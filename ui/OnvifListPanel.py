from tkinter import *


import logging
log = logging.getLogger("onvif.listPanel")

class OnvifListPanel(PanedWindow):
    
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
        self.selectedItem = None
        self.selection = selection

    def addItem(self, item):
        log.debug("Adding item : " + str(item))
        label = Label(self,text=str(item))
        label.item = item
        label.orig_color = label.cget("background")
        label.bind("<Button-1>", self._selectItem)

        self.add(label)
        label.pack(expand=0,fill=BOTH)

    def _selectItem(self, evt):
        caller = evt.widget

        caller.configure(bg='blue')
        if self.selectedItem is not None:
            self.selectedItem.configure(bg=self.selectedItem.orig_color)
        self.selectedItem = caller

        if self.selection is not None:
            self.selection(caller.item)