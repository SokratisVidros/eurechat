#
# chatServer.py
# 
# @author       : Vidros Sokratis <vidros@eurecom.fr>
# @date         : 20-1-2012 
# @copyright    : Copyright (c) 2012 Vidros Sokratis
# @license      : http://creativecommons.org/licenses/by-nd-nc/1.0/
# @version      : 1.0
# @description  : Eurechat peer protocol implementation and listening server based on twisted python
#

from twisted.internet import protocol, reactor

import parsing as p



class PeerProtocol(protocol.Protocol):
    """ Implementing Eurechat peer protocol between users. """
    
    def connectionMade(self):
        self.buffer = ""
        
        # If the peer protocol is trigger by the client factory we add the
        # instance in the active peer connection list
        if not isinstance(self.factory, ChatServerFactory):
            self.factory.clientConnectionMade(self)
        
    def connectionLost(self, reason):
        
        # If the peer protocol is trigger by the client factory we remove the
        # instance of the active peer connection list
        if not isinstance(self.factory, ChatServerFactory):
            self.factory.clientConnectionClosed(self)
            
    def dataReceived(self, data):
        try:
            self.buffer += data
            self.buffer, msgs = p.parse_all(self.buffer)
    
            for msg in msgs:
                reactor.callLater(0, self.msgReceived, msg)
        
        except:
            # @TODO
            # Error handling
            pass
            
    def msgSend(self, msgType, msgArgs =[], msgPayload = ""):
        m = p.Message(msgType, msgArgs, msgPayload)
        self.transport.write(str(m))
        
    def msgReceived(self, msg):
        """ Function that handles incomind messages and Ping pongs """
        
        if msg.type == p.T_PING:
            self.msgSend(p.T_PONG, [self.factory.username])
        elif msg.type == p.T_MESSAGE:
            print "%s:> %s"%(str(msg.args), msg.payload)
            


class ChatServerFactory(protocol.ServerFactory):
    """ Chat Server Factory class, listens to incoming requests
        by implementing the peer protocol."""
        
    protocol = PeerProtocol

    def __init__(self, username):
        self.username = username