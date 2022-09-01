import gi
import threading
import numpy as np
from PIL import ImageTk, Image

gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst,GstVideo
import gstreamer.utils as utils

import logging
log = logging.getLogger("onvif.videoDecoder")

Gst.init(None)
class VideoDecoder(Gst.Bin):
    def __init__(self):
        log.debug('Init video encoder')
        super(VideoDecoder, self).__init__()

        ocaps = Gst.Caps.from_string("video/x-raw, format=(string)RGBA, pixel-aspect-ratio=(fraction)1/1")

        # Create elements
        q1 = Gst.ElementFactory.make('queue', None)
        depay = Gst.ElementFactory.make('rtph264depay', None)
        parser = Gst.ElementFactory.make('h264parse', None)
        ##
        #dec = Gst.ElementFactory.make('openh264dec',None)
        dec = Gst.ElementFactory.make('avdec_h264',None)
        colorspace = Gst.ElementFactory.make("videoconvert", None)
        vfilter = Gst.ElementFactory.make("capsfilter", "filter")
        q2 = Gst.ElementFactory.make('queue', None)

        vfilter.set_property("caps", ocaps)

        # Add elements to Bin
        self.add(q1)
        self.add(depay)
        self.add(parser)
        ##
        self.add(dec)
        self.add(colorspace)
        self.add(vfilter)
        self.add(q2)

        # Link elements
        q1.link(depay)
        depay.link(parser)
        #parser.link(q2)
        parser.link(dec)
        dec.link(colorspace)
        colorspace.link(vfilter)
        vfilter.link(q2)
        #dec.link(q2)

        # Add Ghost Pads
        self.add_pad(
            Gst.GhostPad.new('sink', q1.get_static_pad('sink'))
        )
        self.add_pad(
            Gst.GhostPad.new('src', q2.get_static_pad('src'))
        )

class StreamDisplayThread(threading.Thread):
    def __init__(self, streamer) -> None:
        threading.Thread.__init__(self)
        self.streamer = streamer
        self.running = False
        self.img = None

    #TODO Set size on resize
    def displayImage(self):
        imgtk = ImageTk.PhotoImage(image=self.img)
        self.streamer.canvas.imgtk = imgtk
        self.streamer.canvas.configure(image=imgtk)

    def run(self):
        self.running = True
        while(self.running):
            
            if self.streamer.vsink is None:
                #No video output define
                return
                
            sample = self.streamer.vsink.emit('pull-sample')

            caps_format = sample.get_caps().get_structure(0)  # Gst.Structure

            # GstVideo.VideoFormat
            frmt_str = caps_format.get_value('format') 
            video_format = GstVideo.VideoFormat.from_string(frmt_str)
            
            w, h = caps_format.get_value('width'), caps_format.get_value('height')

            c = utils.get_num_channels(video_format)

            buffer = sample.get_buffer()
            array = np.ndarray(shape=(h, w, c), \
                buffer=buffer.extract_dup(0, buffer.get_size()), \
                dtype=utils.get_np_dtype(video_format))

            #array = np.squeeze(array)  
            self.img = Image.fromarray(array)

            #First run, determine aspect ratio of incoming feed
            if self.streamer.ratio is None:
                self.streamer.ratio = self.streamer.calculate_aspect(width=w,height=h)

            #First run, determine the size of the canvas
            if self.streamer.size is None:
                width = self.streamer.canvas.winfo_width()
                height = int(self.streamer.getHeight(arw=self.streamer.ratio[0],arh=self.streamer.ratio[1],width=width))
                self.streamer.size = (width,height)
            else:
                width = self.streamer.size[0]
                height = self.streamer.size[1]

            #Make sure widget isn't bigger than the picture
            if height > h or width > w:
                height = h
                width = w
                self.streamer.size = (width,height)

            self.img.thumbnail(self.streamer.size, Image.ANTIALIAS)
            self.streamer.canvas.after(1, self.displayImage)

    def stop(self):
        self.running = True