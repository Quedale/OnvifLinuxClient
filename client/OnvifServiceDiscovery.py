import sys
import logging
from socket import *

log = logging.getLogger("onvif.discovery")

class OnvifServiceDiscovery:

    def __call__(self,callback):
        self.server_address = ('255.255.255.255', 3702)
        self.msg = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:wsd="http://schemas.xmlsoap.org/ws/2005/04/discovery">
                        <soap:Header>
                            <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
                            <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Resolve</wsa:Action>
                            <wsa:MessageID>urn:uuid:29206488-217f-4a1d-83c7-da156409aec8</wsa:MessageID>
                        </soap:Header>
                        <soap:Body>
                            <wsd:Resolve>
                                <wsa:EndpointReference>
                                    <wsa:Address>urn:uuid:1c852a4d-b800-1f08-abcd-6cc21717ea2a</wsa:Address>
                                </wsa:EndpointReference>
                            </wsd:Resolve>
                        </soap:Body>
                    </soap:Envelope>"""
        log.debug("Scanning...")
        
        # Create a UDP socket
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        sock.settimeout(5)
        try:
            # Send data
            sent = sock.sendto(self.msg.encode(), self.server_address)

            # Receive response
            log.debug('Waiting to receive udp response...')
            data, servers = sock.recvfrom(4096)
            dec_data = data.decode('UTF-8')
            #TODO Extract features from prob
            #print(dec_data)
            
            for server in servers:
                if self.validate_ip(str(server)):
                    log.info('Discovered Server ip: ' + str(server))
                    #TODO Try catch
                    callback(server)
                else:
                    log.warn("Invalid IP address received : " + str(server))
            
        finally:	
            sock.close()

    def validate_ip(self,s):
        a = s.split('.')
        if len(a) != 4:
            return False
        for x in a:
            if not x.isdigit():
                return False
            i = int(x)
            if i < 0 or i > 255:
                return False
        return True

sys.modules[__name__] = OnvifServiceDiscovery()