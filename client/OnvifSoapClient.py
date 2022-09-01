
from zeep import AsyncClient, Settings
from requests import Session
from requests.auth import HTTPBasicAuth
from zeep.transports import Transport
import json 

class OnvifSoapClient():
    WSDL_DEVICE="wsdl/devicemgmt.wsdl"

    
    def __init__(self, username, password, server):
        session = Session()
        session.auth = HTTPBasicAuth(username, password)

        settings = Settings(strict=False, xml_huge_tree=True)
        self.client = AsyncClient(self.WSDL_DEVICE, settings=settings, transport=Transport(session=session))
        self.device = self.client.create_service('{http://www.onvif.org/ver10/device/wsdl}DeviceBinding', "http://" + str(server) + ":8081/onvif/device_service")

        #Cache entries
        self.hostname = None

    def __str__(self):
        hostname = self.getHostname()
        string = "Hostname : " + hostname["Name"] + "\nType : " + self._getDeviceType()
        return string

    def getHostname(self):
        if(self.hostname == None):
            self.hostname = self.device.GetHostname()
        return self.hostname

    def getDevice(self):
        return self.device

    def _getDeviceType(self):
        return "Camera"

    
