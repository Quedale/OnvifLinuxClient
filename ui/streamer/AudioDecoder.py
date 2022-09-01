import threading
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstAudio', '1.0')
from gi.repository import Gst, GstAudio

import logging
log = logging.getLogger("onvif.streamer")

Gst.init(None)

class AudioDecoder(Gst.Bin):
    def __init__(self, pipeline,volumeGage=None, volume=50):
        log.info('Init audio encoder')

        self.volumeGage = volumeGage
        self.mic_sensitivity = 20

        super(AudioDecoder, self).__init__()
        bus = pipeline.get_bus()
        bus.set_sync_handler(self.on_message)
        
        # Create elements
        q1 = Gst.ElementFactory.make('queue', None)
        decode = Gst.ElementFactory.make('decodebin', None)
        self.volume = Gst.ElementFactory.make('volume',None)
        level = Gst.ElementFactory.make('level',None)
        self.convert = Gst.ElementFactory.make('audioconvert', None)
        q2 = Gst.ElementFactory.make('queue', None)

        self.setVolume(volume)
        #ocaps = Gst.Caps.from_string("audio/x-raw, channels=1, rate=8000")
        #ofilter = Gst.ElementFactory.make("capsfilter", "filter")
        #ofilter.set_property("caps", ocaps)

        level.set_property('post-messages',True)
        level.set_property('message',True)

        # Add elements to Bin
        self.add(q1)
        self.add(level)
        self.add(decode)
        #self.add(ofilter)
        self.add(self.convert)
        self.add(self.volume)
        self.add(q2)

        # Link elements
        q1.link(decode)

        # skip decode convert link - add it only on new pad added
        self.convert.link(level)
        #ofilter.link(volume)
        level.link(self.volume)
        self.volume.link(q2)

        #self.volume.set_volume(GstAudio.StreamVolumeFormat.LINEAR ,0.05)
        decode.connect('pad-added', self.on_new_decoded_pad)

        log.debug('Using rtsp sink audio stream')
        # Add Ghost Pads
        self.add_pad(
            Gst.GhostPad.new('sink', q1.get_static_pad('sink'))
        )

        self.add_pad(
            Gst.GhostPad.new('src', q2.get_static_pad('src'))
        )

    def setVolume(self,volume):
        self.volume.set_volume(GstAudio.StreamVolumeFormat.LINEAR ,volume/100)
        
    def on_message(self,bus, message):
        #if message.type == Gst.MESSAGE_ELEMENT:
        struct = message.get_structure()
        if struct is not None and struct.get_name() == 'level':
            peak = struct.get_value('peak')[0]+self.mic_sensitivity
            
            if peak < 0:
                peak = 0

            if self.volumeGage is not None:
                percentage = (peak / self.mic_sensitivity) * 100
                self.volumeGage.value(percentage)
        # else:
        #     print("on_message : " + str(message))
        #     print('strict : ' + struct.to_string())
        return True


    def on_new_decoded_pad(self, element, pad):
        pad.get_parent().link(self.convert)
        log.debug('Audio connected')
