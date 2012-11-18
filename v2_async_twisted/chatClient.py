#
# chatClient.py
# 
# @author       : Vidros Sokratis <vidros@eurecom.fr>
# @date         : 20-1-2012 
# @copyright    : Copyright (c) 2012 Vidros Sokratis
# @license      : http://creativecommons.org/licenses/by-nd-nc/1.0/
# @version      : 1.0
# @description  : Eurechat directory protocol implementation and client based on twisted python
# 

import re
import parsing as p

from twisted.internet import reactor,protocol
from twisted.internet.protocol import ClientFactory

from chatServer import PeerProtocol


S_LOGINSENT     = "LOGIN_SENT"
S_PASSSENT      = "PASS_SENT"
S_AUTHENTICATED = "AUTHENTICATED"
S_ERROR         = "ERROR"



class DirectoryProtocol(protocol.Protocol):
    """ Implementing Eurechat server protocol between user and directory server. """
    
    def connectionMade(self):
        self.factory.connection=self
        self.def_list=[]
        self.buffer = ""
        self.msgSend(p.T_USER, [self.factory.username])
        self.state = S_LOGINSENT
        
    def connectionLost(self, reason):
        pass
        #self.factory.handleError("Connection lost, %s" % reason)
        
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
        try:
            if msg.type == p.T_PING:
                self.msgSend(p.T_PONG)
            elif self.state == S_LOGINSENT:
                if msg.type == p.T_ACK:
                    self.msgSend(p.T_PASS, [self.factory.password])
                    self.state = S_PASSSENT
                else:
                    self.state = S_ERROR
            elif self.state == S_PASSSENT:
                if msg.type == p.T_ACK:
                    self.msgSend(p.T_BIND, [self.factory.host, self.factory.listeningPort])
                    self.state = S_AUTHENTICATED
                else:
                    self.state = S_ERROR
            elif self.state == S_AUTHENTICATED:
                if msg.type == p.T_ACK:
                    
                    # @ TODO
                    # Implement Leave State
                    pass
                elif msg.type == p.T_RESULT:
                    [ self.__parseUserRecord(r) for r in msg.payload.split() ] 
                    
                    # @ TODO
                    # Redirect printing to the agent for better output
                    print "Online users:"
                    for x in self.factory.userList:
                        print "list:> %s, %s" % (x, self.factory.userList[x])
                else:
                    self.state = S_ERROR
        except Exception, e:
            self.factory.handleError(e)

    def __parseUserRecord(self, record):
        """ Parse user records and store the extracted information as a tuple in a dictionary """

        match = re.search('([a-zA-Z0-9]+),([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}),([0-9]+)', record)
        username = match.group(1)
        userIp = match.group(2)
        userPort = int(match.group(3))
        self.factory.userList[username] = (userIp, userPort)



class ChatClientFactory(ClientFactory):
    """ Chat Client Factory class, handles the interaction between the user 
        and the directory server plus the chating among users."""
    
    def __init__(self, username, password, host, listeningPort):
        self.connection=None
        self.username = username
        self.password = password
        self.host = host
        self.listeningPort = listeningPort
        self.dirProto = None
        self.userList = {}              # Keep all the user's data (IP, PORT) in a dictonary
        self.peerPool = []              # Keep a list of all the active peer connections and reuse them
    
    def buildProtocol(self, address):
        """ Overriden method to distinguish between the two protocols. """
        
        if address.port == 8888:
            self.protocol = DirectoryProtocol
            self.dirProto = ClientFactory.buildProtocol(self, address)
            return self.dirProto
        else:
            self.protocol = PeerProtocol
            return ClientFactory.buildProtocol(self, address)
    
    def clientConnectionLost(self, connector, reason):
        #self.handleError("Lost connection, reason: %s" % reason.getErrorMessage())
        
        #Reconnect automatically on the directory server. Keep connection alive
        connector.connect()
        
    def clientConnectionFailed(self, connector, reason):
        self.handleError("Connection failed, reason: %s" % reason.getErrorMessage())
        #reactor.stop()
    
    def clientConnectionMade(self, client):
        """ Method that adds a new peer connection to the connection list upon success """
        
        self.peerPool.append(client)
        
    def clientConnectionClosed(self, client):
        """ Method that removes a dead peer connection from the connection list """
        
        self.peerPool.remove(client)
    
    def listAll(self):
        """ Send a 'list all users' query to the directory server """
        self.dirProto.msgSend(p.T_QUERY)
    
    def search(self, user):
        """ Search for a specific user """
        
        self.dirProto.msgSend(p.T_QUERY, [user])
        
    def leave(self):
        self.dirProto.msgSend(p.T_LEAVE,[])
        
    def chat(self, username, message = "Dummy"):
        """ Start chatting with a specific user """

        try:
            if len(self.userList) == 0:
                raise Exception, 'Use the list command to get the online users'

            if (username in self.userList):
                uIp, uPort = self.userList[username]
                uConn = self.__searchOpenPeers((uIp, uPort))
                if len(self.peerPool) == 0 or uConn is None:
                    reactor.connectTCP( uIp, uPort, self)
                    
                    # Quick and dirty solution to wait 1 sec until the connection is setup
                    # The right one is to use deferreds!
                    reactor.callLater(1,self.chat, username, message)
                else:
                    uConn.msgSend(p.T_MESSAGE, [self.username], message)

            else:
                raise Exception, 'User %s can\'t be reached.' % username

        except Exception,e:
            self.handleError(e)
            
    def ping(self, username):
        """ Ping a specific user """

        try:
            if len(self.userList) == 0:
                raise Exception, 'Use the list command to get the online users'

            if (username in self.userList):
                uIp, uPort = self.userList[username]
                uConn = self.__searchOpenPeers((uIp, uPort))
                
                if len(self.peerPool) == 0 or uConn is None:
                    reactor.connectTCP( uIp, uPort, self)
                    
                    # Same quick and dirty solution here
                    reactor.callLater(1,self.ping, username)
                else:
                    uConn.msgSend(p.T_PING, [self.username])
            else:
                raise Exception, 'User %s can\'t be reached.' % username

        except Exception,e:
            self.handleError(e)
    
    def __searchOpenPeers(self, (host, port)):
        """ Search if there is an active connection for the specific user (IP, PORT). """
        
        for client in self.peerPool:
            cHost = client.transport.getPeer().host
            cPort = client.transport.getPeer().port

            if cHost is host and cPort == port:
                return client
        return None
    
    def handleError(self, errorMsg):
        # @TODO send data back to agent throung transport, with defered
        print "Error:> " + str(errorMsg)