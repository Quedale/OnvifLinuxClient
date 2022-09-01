from tkinter import *
from ui.streamer.VideoStreamerGst import VideoStreamerGst
from ui.OnvifVolumeGage import OnvifVolumeGage

class OnvifDevicePanel(PanedWindow):
    def __init__(self, master=None, cnf=None, background=None, bd=None, bg=None, border=None, borderwidth=None, cursor=None, handlepad=None, 
                handlesize=None, height=None, name=None, opaqueresize=None, orient=None, 
                proxybackground=None, proxyborderwidth=None, proxyrelief=None, 
                relief=None, sashcursor=None, sashpad=None, sashrelief=None, sashwidth=None, 
                showhandle=None, width=None, selection=None) -> None:
        super().__init__(master=master, cnf=cnf, background=background, bd=bd, bg=bg, border=border, borderwidth=borderwidth, cursor=cursor, handlepad=handlepad, 
                handlesize=handlesize, height=height, name=name, opaqueresize=opaqueresize, orient=orient, 
                proxybackground=proxybackground, proxyborderwidth=proxyborderwidth, proxyrelief=proxyrelief, 
                relief=relief, sashcursor=sashcursor, sashpad=sashpad, sashrelief=sashrelief, sashwidth=sashwidth, 
                showhandle=showhandle, width=width)

        self.volume = 1
        self.client = None
        self.resize = None
        
        self.volumeGage = OnvifVolumeGage(self, bd=1, relief="solid", width=width,height=15)
        self.add(self.volumeGage)
        
        self.mediaContainer = PanedWindow(self,orient=HORIZONTAL)

        self.devicePanel = Label(self.mediaContainer, text="Top Panel", bg='black')
        self.mediaContainer.add(self.devicePanel)
        self.devicePanel.bind("<Configure>", self._resize)

        self.volumeControl = Scale(self.mediaContainer, from_=100, to=0, orient="vertical", command=self._volumeControl, width=20)
        self.mediaContainer.add(self.volumeControl)
        self.add(self.mediaContainer)
        self.volumeControl.set(1)

        self.volumeControl.pack(fill=NONE,expand=0,side=BOTTOM)
        self.devicePanel.pack(expand=1,fill=BOTH)
        self.volumeGage.pack(expand=0,fill=X)

        self.mediaContainer.pack(expand=1,fill=BOTH)
        

    def _volumeControl(self,value):
        self.volume = int(value)
        if self.client is not None:
                self.client.stream.setVolume(self.volume)

    def showDevice(self, client):
        if self.client is not None:
                self.client.stream.stopStream()

        self.client = client
        self.client.stream = VideoStreamerGst(url="rtsp://127.0.0.1:8554/h264", canvas=self.devicePanel, volumeGage=self.volumeGage, volume=self.volume)
        
        #TODO Stop VideoStreamer gracefully
        self.client.stream.startStream()

    def _resize(self,event):
        if self.client is not None:
                self.client.stream.setWidth(event.width)

