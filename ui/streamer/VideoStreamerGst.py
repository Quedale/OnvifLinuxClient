import time
import alsaaudio
from ui.streamer.AudioDecoder import AudioDecoder
from ui.streamer.VideoDecoder import VideoDecoder
from ui.streamer.AudioEncoder import AudioEncoder
from ui.streamer.VideoDecoder import StreamDisplayThread
import numpy as np
import gc
import gi
import weakref
import gstreamer.utils as utils
import traceback

gi.require_version('Gst', '1.0')
gi.require_version('GstAudio', '1.0')
from gi.repository import Gst, GLib, GstAudio
#import gstreamer.utils as utils

import logging
log = logging.getLogger("onvif.streamer")

Gst.init(None)

class AudioSamplePlayer:
    def __init__(self) -> None:
        #TODO Create device from sample caps
        #audio/x-raw, format=(string)S16LE, layout=(string)interleaved, rate=(int)8000, channels=(int)1
        self.device = alsaaudio.PCM(type=alsaaudio.PCM_PLAYBACK, 
                mode=alsaaudio.PCM_NONBLOCK, 
                #rate=8000, 
                #channels=1, 
                #format=alsaaudio.PCM_FORMAT_S16_LE, 
                #device='default'
                )

        self.device.setchannels(1)
        self.device.setrate(8000)
        self.device.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        #self.device.polldescriptors()
    
    def new_sample(self, pad):
        try:
            sample = pad.emit('pull-sample')
            buffer=sample.get_buffer()
            self.device.write(buffer.extract_dup(0, buffer.get_size()))

        except Exception as e:
            log.error(e)
            #TODO Return appropriate failure code
        
        return Gst.FlowReturn.OK

class AudioSampleForwarder:
    def __init__(self,rtspsrc,channel) -> None:
        self.channel = channel
        self.rtspsrc = rtspsrc

            
    def copy_buffer(self,buffer):
        buffer=buffer.extract_dup(0, buffer.get_size())
        return Gst.Buffer.new_wrapped(buffer)

    def copy_buffer2(self,buffer):
        gbuffer = Gst.Buffer()
        return gbuffer

    def copy_caps(self,caps):
        return Gst.caps_from_string(caps.to_string())


    def gst_sample_make_writable(self, sample):
        if sample.get_buffer().mini_object.is_writable():
            return sample
        else:
            return Gst.Sample.new(
                sample.get_buffer().copy_region(
                    Gst.BufferCopyFlags.FLAGS | Gst.BufferCopyFlags.TIMESTAMPS |
                    Gst.BufferCopyFlags.META | Gst.BufferCopyFlags.MEMORY, 0,
                    sample.get_buffer().get_size()),
                sample.get_caps(),
                sample.get_segment().copy(),
                sample.get_info())

    def new_sample(self, pad):
        try:
            sample = pad.emit('pull-sample')
            nsample = self.gst_sample_make_writable(sample)
            log.debug("fake pushing : " + str(nsample.get_buffer().get_size()))
            log.debug("segment position : " + str(sample.get_segment().position))
            log.debug("segment duration : " + str(sample.get_segment().duration))
            log.debug("segment rate : " + str(sample.get_segment().rate))
            ret = self.rtspsrc.emit ("push-backchannel-buffer", self.channel, nsample)
            time.sleep(2)
            return ret
            #return Gst.FlowReturn.OK
        except Exception as e:
            log.error("Some exception")
            log.error(e)
            return Gst.FlowReturn.ERROR

class VideoStreamerGst():
    def __init__(self, canvas=None, url=None, volumeGage=None, volume=50):
        log.debug('Init streaming')
        self.url = url
        self.canvas = canvas
        self.size = None
        self.ratio = None
        self.displayThread = None
        self.micThread = None
        self.exit = False
        self.pipeline = Gst.Pipeline()
        self.bus = self.pipeline.get_bus()
        #self.bus.connect('message', self.on_message)
        
        self.bus.add_signal_watch()
        #self.bus.add_watch(GLib.PRIORITY_DEFAULT, self.on_message)
        #self.bus.set_sync_handler(self.on_message)

        # Connecting common messages
        self.bus.connect('message::error', self.on_error)
        self.sig_eos = None

        # Create elements
        self.src = Gst.ElementFactory.make('rtspsrc', None)
        self.video = VideoDecoder()
        self.vtee = Gst.ElementFactory.make('tee', None)
        self.vqueue = Gst.ElementFactory.make('queue', None)
        self.vsink = Gst.ElementFactory.make('appsink', None)

        # Add elements to pipeline
        self.pipeline.add(self.src)
        self.pipeline.add(self.video)
        self.pipeline.add(self.vtee)
        self.pipeline.add(self.vqueue)
        self.pipeline.add(self.vsink)

        # Set properties
        log.debug("RTSPSRC location : " + str(self.url))
        self.src.set_property('location', self.url)
        self.src.set_property('latency', 0)
        self.src.set_property('onvif-mode', True)
        self.src.set_property('backchannel', 'onvif')
        self.src.set_property('debug', True)

        # Connect signal handlers
        self.src.connect('pad-added', self.on_pad_added)
        self.src.connect('select-stream', self.select_stream)
        
        # Link elements
        self.video.link(self.vtee)
        self.vtee.link(self.vqueue)
        self.vqueue.link(self.vsink)

        # Connecting Audio Output
        self.audio = AudioDecoder(self.pipeline,volumeGage,volume)
        self.atee = Gst.ElementFactory.make('tee', None)
        self.aqueue = Gst.ElementFactory.make('queue', None)
        self.speakers = Gst.ElementFactory.make('appsink',None)

        self.receiver = AudioSamplePlayer()
        self.speakers.connect('new-sample', self.receiver.new_sample)
        self.speakers.set_property('emit-signals', True)

        self.pipeline.add(self.audio)
        self.pipeline.add(self.atee)
        self.pipeline.add(self.aqueue)
        self.pipeline.add(self.speakers)

        self.audio.link(self.atee)
        self.atee.link(self.aqueue)
        self.aqueue.link(self.speakers)

    def setVolume(self,volume):
        self.audio.setVolume(volume)

    def _setup_backshovler(self,rtspsrc,caps,channel):
        log.debug("Setting up Backsholver")
        #Setup Back pipeline
        self.backline = Gst.Pipeline()
        self.backbus = self.backline.get_bus()
        self.backbus.add_signal_watch()
        self.backbus.connect('message::error', self.on_error)
        
        #Create Elements
        #src = Gst.ElementFactory.make('alsasrc', None)
        src = Gst.ElementFactory.make('audiotestsrc', None)
        src.set_property("is-live", True)
        src.set_property("wave", "red-noise")

        convert = Gst.ElementFactory.make('audioconvert', None)
        resampler = Gst.ElementFactory.make('audioresample',None)
        enc = Gst.ElementFactory.make('mulawenc',None)
        pay = Gst.ElementFactory.make('rtppcmupay',None)
        #q2 = Gst.ElementFactory.make('queue', None)
        self.msink = Gst.ElementFactory.make('appsink', None)
        
        
        #ocaps = Gst.Caps.from_string("audio/x-mulaw, channels=1, rate=8000")
        #encCaps = Gst.ElementFactory.make("capsfilter", "filter")
        #encCaps.set_property("caps", ocaps)

        #Set provided caps on AppSink
        #log.debug("Caps : " + str(ocaps.serialize(Gst.SerializeFlags.NONE)))
        if caps is not None:
            log.debug("RTP Caps : " + str(caps.serialize(Gst.SerializeFlags.NONE)))
            self.msink.set_property("caps", caps)
        
        #Flag to enable signal events
        self.msink.set_property('emit-signals', True)

        #Register callback for new-sample
        receiver = AudioSampleForwarder(rtspsrc,channel)
        self.msink.connect('new-sample', receiver.new_sample)

        #Add Elements to pipeline
        self.backline.add(src)
        self.backline.add(convert)
        self.backline.add(resampler)
        self.backline.add(enc)
        self.backline.add(encCaps)
        self.backline.add(pay)
        self.backline.add(self.msink)
        #self.backline.add(q2)

        #Link elements to each other
        src.link(convert)
        convert.link(resampler)
        resampler.link(enc)
        enc.link(encCaps)
        encCaps.link(pay)
        pay.link(self.msink)
        #self.msink.link(q2)

        #Try to setup backchannel feed
        for i in range(1, 6):
            log.debug('Backchannel try %d' % i)
            start_time = time.time()
            backstate = self.backline.set_state(Gst.State.PLAYING)
            backstate=self.backline.get_state(2 * i * Gst.SECOND)[1]
            if backstate == Gst.State.PLAYING:
                log.debug("Successfully started backchannel feed.")
                return True
            else:
                end_time = time.time()
                log.warn('Couldn\'t receive stream, retrying... ' + str(backstate))
                self.backline.set_state(Gst.State.NULL)
                if end_time - start_time < 2 * i:
                    log.warn('Sleeping %f sec...' % ((start_time - end_time) + 2 * i))
                    #TODO skip sleep if last index
                    time.sleep((start_time - end_time) + 2 * i)
                    return False

    def select_stream(self,rtspsrc, num, caps):
        log.debug("Stream selection : " + caps.to_string())
        capstr = caps.to_string()

        if 'media=(string)audio' in capstr:
            if 'a-sendonly=(string)' in capstr:
                # struct = caps.get_structure(0).copy()
                # struct.set_name('application/x-rtp')
                # ccaps = Gst.caps_from_string(struct.to_string())
                ccaps = Gst.caps_from_string("application/x-rtp, media=(string)audio, payload=(int)0, clock-rate=(int)8000, encoding-name=(string)PCMU")
                log.debug("Select stream for caps : " + capstr)
                log.debug("Updated Caps for Output : " + ccaps.to_string())
                return self._setup_backshovler(rtspsrc,ccaps,num)
            #elif 'a-recvonly=(string)' in capstr:
                #ccaps = Gst.caps_from_string("application/x-rtp, media=(string)audio, payload=(int)0, clock-rate=(int)8000, encoding-name=(string)PCMU")
                #log.debug("Updated Caps for Output : " + ccaps.to_string())
            #else:
                #log.warn("What is this...")

        return True
        
    def startStream(self):
        log.info("Starting streams...")
        self.start()

    def setWidth(self,width):
        if self.ratio is None:
            height = int(self.getHeight(16,9,width))
        else:
            height = int(self.getHeight(arw=self.ratio[0],arh=self.ratio[1],width=width))
        self.size = (width,height)

    def getHeight(self, arw, arh, width):
        v1 = width / arw
        v2 = v1 * arh
        return v2

    def calculate_aspect(self,width: int, height: int) -> str:
        def gcd(a, b):
            """The GCD (greatest common divisor) is the highest number that evenly divides both width and height."""
            return a if b == 0 else gcd(b, a % b)

        r = gcd(width, height)
        x = int(width / r)
        y = int(height / r)

        return (x,y)

    def on_error(self, bus, msg):
        log.error('Received error:' + ' '.join(map(str,msg.parse_error())))
        self.stop()

    def start(self):
        #while self.exit != True:
            self.run()      

    def _stop_stream_threads(self):
        if self.displayThread is not None:
            self.displayThread.stop()
            self.displayThread = None
        if self.micThread is not None:
            self.micThread.stop()
            self.micThread = None

    def run(self):
        log.info('Running streaming')
        if self.sig_eos != None:
            self.bus.disconnect(self.sig_eos)
        self.sig_eos = self.bus.connect('message::eos', self.on_eos)
        self.mainloop = GLib.MainLoop()

        # Try to connect 5 times before reset camera
        for i in range(1, 6):
            log.debug('Try %d' % i)

            start_time = time.time()
            self.pipeline.set_state(Gst.State.PLAYING)
            
            # Check that pipeline is ok
            state=self.pipeline.get_state(2 * i * Gst.SECOND)[1]
            if state == Gst.State.PLAYING:
                log.debug('Start receiving stream')
                try:
                    self._stop_stream_threads()
                    if self.canvas is not None:
                        self.displayThread = StreamDisplayThread(streamer=self)
                        self.displayThread.start()
                except KeyboardInterrupt:
                    log.warn('Received keyboard interrupt. Stopping streaming by EOS')
                    self.stop()
                return
            else:
                end_time = time.time()
                log.warn('Couldn\'t receive stream, retrying... ' + str(state))
                self.pipeline.set_state(Gst.State.NULL)
                if end_time - start_time < 2 * i:
                    log.warn('Sleeping %f sec...' % ((start_time - end_time) + 2 * i))
                    time.sleep((start_time - end_time) + 2 * i)

        log.error('Couldn\'t receive stream, closing device...')
        self.stop()

    def on_eos(self, bus, msg):
        log.info('Received end of stream...')

    def stop(self):

        self._stop_stream_threads()
        self.exit = True
        self.eos()
        log.info('Cleaning gstreamer')
        #TODO check for failed backline
        self.backline.set_state(Gst.State.NULL)
        self.pipeline.set_state(Gst.State.NULL)
        self.bus.remove_signal_watch()
        self.backbus.remove_signal_watch()

    def eos(self):
        if self.pipeline.get_state(2 * Gst.SECOND)[1] == Gst.State.PLAYING:
            log.debug('Sending EOS')
            self.bus.disconnect(self.sig_eos)
            self.sig_eos = self.bus.connect('message::eos', self.stop_eos)
            self.pipeline.send_event(Gst.Event.new_eos())
            try:
                pass
                #self.eosloop = GLib.MainLoop()
                #self.eosloop.run()
            except KeyboardInterrupt:
                log.info('EOS waiting is stopped by keyboard interrupt')
        else:
            log.error('Couldn\'t send EOS due to pipeline state is not playing')
        self._stop_stream_threads()
        self.mainloop.quit()

    def stop_eos(self, bus, msg):
        log.info('EOS is received')
        self.eosloop.quit()
        bus.disconnect(self.sig_eos)
        self._stop_stream_threads()

    def on_pad_added(self, element, pad):
        string = pad.query_caps(None).to_string()
        log.debug('Found stream: %s' % string)

        if string.startswith('application/x-rtp'):
            if 'media=(string)video' in string:
                pad.link(self.video.get_static_pad('sink'))
                log.info('Video connected')
            elif 'media=(string)audio' in string:
                pad.link(self.audio.get_static_pad('sink'))
                log.info('Audio found...')
            else:
                log.warn("------------------- what ---- : ")
        else:
            log.warn("------------------- what2 ---- : ")


if __name__ == "__main__":
    streamer = VideoStreamerGst(url="rtsp://127.0.0.1:8554/h264", canvas=None)
    streamer.start()