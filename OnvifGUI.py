import logging
import logging.config
import yaml

import tkinter as tk
import client.OnvifServiceDiscovery as ServD
from client.OnvifSoapClient  import OnvifSoapClient
from ui.OnvifDevicePanel  import OnvifDevicePanel
from ui.OnvifListPanel import OnvifListPanel

with open('logging.yml', 'rt') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)

log = logging.getLogger("onvif.mainWindow")

class MainWindow():
    def __init__(self) -> None:
        self.window = tk.Tk()

        #Root Wrapper
        self.rootContainer = tk.PanedWindow(height=800,width=1200)
        self.rootContainer.pack(fill=tk.BOTH, expand=1)
        
        #Browser Wrapper
        self.browserContainer = tk.PanedWindow(self.rootContainer)

        #Search Button
        self.scanBtn = tk.Button(
            self.browserContainer,
            text="Scan...",
            width=25,
            height=4,
            command=self._discoverDevices
        )
        self.onvifPanel = OnvifDevicePanel(self.rootContainer)

        self.listbox = OnvifListPanel(self.browserContainer, width=200, bg='white', selection=self.onvifPanel.showDevice)

        self.browserContainer.add(self.scanBtn)
        self.scanBtn.pack()
        self.browserContainer.add(self.listbox)
        self.listbox.pack(fill=tk.BOTH,expand=1)
        self.rootContainer.add(self.browserContainer)

        self.rootContainer.add(self.onvifPanel)

        self.client = None
    

    def show(self):
        self.window.mainloop()
    
    def _discoverDevices(self):
        sd = ServD(self._foundDevice)

    def _foundDevice(self,ip):
        onvif_client = OnvifSoapClient("admin","admin", ip)
        self.listbox.addItem(onvif_client)


if __name__ == "__main__":
    log.info("Entering main...")
    log.debug("Entering main...")
    mw = MainWindow()
    mw.show()