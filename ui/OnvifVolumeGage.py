
from tkinter import *
from tkinter import ttk
import math


class OnvifVolumeGage(Canvas):
    def __init__(self, parent, width=None,height=None, bd=None, bg=None, relief=None) -> None:
        super().__init__(parent,bd=bd,relief=relief,width=width,height=height)
        self.currentValue = 0
        self.rendered = False
        self.setSize(width,height)
        self.bind("<Configure>", self._resize)

    def setSize(self,width=None,height=None):
        if width is None or height is None or width == 0 or height == 0:
            self.width = 0
            self.height = 0
            self.rendered = False
            self.delete(ALL)
            return

        self.width = width
        self.height = height
        self.bar_width = width / 4
        self.scale_factor = width / 100
        self.value(self.currentValue)

    def _createFullGreen(self):
        self.create_rectangle(
                0, 
                0, 
                self.bar_width, 
                self.height, 
                fill="green")

    def _createFullYellow(self):
        self.create_rectangle(
                self.bar_width, 
                0, 
                self.bar_width*2, 
                self.height, 
                fill="yellow")

    def _createFullOrange(self):
        self.create_rectangle(
                self.bar_width*2, 
                0, 
                self.bar_width*3, 
                self.height, 
                fill="orange")

    def _createPartialColor(self,color,start):
        self.create_rectangle(
                start, 
                0, 
                self.currentValue * self.scale_factor, 
                self.height, 
                fill=color)

    def _resize(self,event):
        self.setSize(event.width,event.height)

    def value(self,scalevar):
        if self.currentValue == scalevar and self.rendered:
            return

        scalevar= math.ceil(scalevar)
        scalevar = int(scalevar)

        self.rendered = False
        self.currentValue = scalevar
        self.delete(ALL)

        if self.width == 0 or self.height == 0:
            return

        if scalevar <= 25:
            self._createPartialColor('green',0)
        elif scalevar <= 50 and scalevar > 25:
            self._createFullGreen()
            self._createPartialColor('yellow',self.bar_width)
        elif scalevar <= 75 and scalevar > 50:
            self._createFullGreen()
            self._createFullYellow()
            self._createPartialColor('orange',self.bar_width*2)
        else:
            self._createFullGreen()
            self._createFullYellow()
            self._createFullOrange()
            self._createPartialColor('red',self.bar_width*3)
        self.rendered = True