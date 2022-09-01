import threading
import time
import gi
gi.require_version('Gst', '1.0')

from gi.repository import Gst

import logging
log = logging.getLogger("onvif.audioDecoder")

Gst.init(None)

class AudioEncoder(Gst.Bin):
    def __init__(self):
        log.info('Init audio encoder')
        super(AudioEncoder, self).__init__()


        ocaps = Gst.Caps.from_string("audio/x-mulaw, channels=1, rate=8000")

        # Create elements
        q1 = Gst.ElementFactory.make('queue', None)
        src = Gst.ElementFactory.make('audiotestsrc', None)
        self.convert = Gst.ElementFactory.make('audioconvert', None)
        resampler = Gst.ElementFactory.make('audioresample',None)
        enc = Gst.ElementFactory.make('mulawenc',None)
        pay = Gst.ElementFactory.make('rtppcmupay',None)
        q2 = Gst.ElementFactory.make('queue', None)
        
        micfilter = Gst.ElementFactory.make("capsfilter", "filter")
        micfilter.set_property("caps", ocaps)

        # Add elements to Bin
        self.add(q1)
        self.add(src)
        self.add(self.convert)
        self.add(resampler)
        self.add(enc)
        self.add(micfilter)
        self.add(pay)
        self.add(q2)

        # Link elements
        q1.link(src)
        src.link(self.convert)
        self.convert.link(resampler)
        resampler.link(enc)
        enc.link(micfilter)
        micfilter.link(pay)
        pay.link(q2)
        
        log.debug('Using rtsp source audio stream')
        # Add Ghost Pads
        self.add_pad(
            Gst.GhostPad.new('sink', q1.get_static_pad('sink'))
        )
        self.add_pad(
            Gst.GhostPad.new('src', q2.get_static_pad('src'))
        )