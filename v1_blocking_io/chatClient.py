#
# chatClient.py
# 
# @author       : Vidros Sokratis <vidros@eurecom.fr>
# @date         : 9-1-2012 
# @copyright    : Copyright (c) 2012 Vidros Sokratis
# @license      : http://creativecommons.org/licenses/by-nd-nc/1.0/
# @version      : 1.0
# @description  : Chat single threaded client class
#


import re
import sys
import parsing as p

from time import sleep
from connectionManager import ConnectionManager



class ChatClient:
    """ Chat client handles all outcoming requests like (authentication, user searching and of course chatting. The general idea of the client is to
    open a connection for sending messages and receive all the incoming messages
    at the server port that is known through the directory server."""

    def __init__(self, host, port, username, password, agent):
        self.__host = host
        self.__port = port
        self.__username = username
        self.__password = password
        self.__agent = agent
        self.__cm = None
        self.__userList = {}

    def __connect(self):
        self.__cm = ConnectionManager(self.__host, self.__port)
        self.__cm.connect()
        
    def __disconnect(self):
        self.__cm.disconnect()

    def __trigger(self, toBeExecuted, args = []):
        """ Trigger function uses the power of functinal programing to execute the functions 
            that are passed as parameters. In details, its a wrapper for every command that
            requires re-authentication with the directory server. """

        self.__connect()
        [ f(args) for f in toBeExecuted ]
        self.__disconnect()

    def authenticate(self):
        self.__trigger([self.__login, self.__bind])

    def search(self, username):
        self.__trigger([self.__login, self.__searchUser], [username])

    def listAll(self):
        self.__trigger([self.__login, self.__searchUser])

    def leave(self):
        self.__trigger([self.__login, self.__unregister])

    def chat(self, username, message, getSecret = False):
        """ Start chatting with a specific user """

        try:
            if len(self.__userList) == 0:
                raise Exception, 'Use the list command to see the online users'

            if (username in self.__userList):
   
                # Setup a new socket connection with the other user and send data.
                # The user can reply at the binded port from the directory server
                uIp, uP = self.__userList[username]
                c = ConnectionManager(uIp, uP)
                c.connect()
                c.send(p.T_MESSAGE, [self.__username], message)
                c.disconnect()

            else:
                raise Exception, 'User %s can\'t be reached.' % username

        except Exception,e:
            self.__handleError('Chat', e)

    def getSecret(self, username, message):
        """ Start chatting with the bot server. GLADOS replies back to the client socket
            so we have to keep the connection open and wait to receive replies from bot. """

        try:
            if len(self.__userList) == 0:
                raise Exception, 'Use the list command to see the online users'

            if (username in self.__userList):
   
                uIp, uP = self.__userList[username]
                c = ConnectionManager(uIp, uP)
                c.connect()
                c.send(p.T_MESSAGE, [self.__username], message)
                
                # We wait for four replies from GLADOS to receive the final token
                # The application is going to block until GLADOS replies.
                # Quick and dirty solution as GLaDOS speaks "differently" from
                # the way this client is implemented. So, the message is printed
                # in raw format just to get the final token. 
                for i in range(0,3):
                    r = c.receive()
                    self.__agent.printMessage(str(r),'Bot user')
                    if(r.type == p.T_PING):
                        c.send(p.T_PONG, [self.__username])
                c.disconnect()
            else:
                raise Exception, 'User %s can\'t be reached.' % username

        except Exception,e:
            self.__handleError('Chat', e)

    def ping(self, username):
        """ Ping user """

        try:       
            if len(self.__userList) == 0:
                raise Exception, 'Use the list command to see the online users'

            if (username in self.__userList):
   
                uIp, uP = self.__userList[username]
                c = ConnectionManager(uIp, uP)

                c.connect()
                c.send(p.T_PING, [self.__username])

                pong = c.receive()
                self.__agent.printMessage(pong.type, pong.args.pop())

                c.disconnect()
            else:
                raise Exception, 'User %s can\'t be pinged.' % username

        except Exception,e:
            self.__handleError('Ping', e)

    def getUsername(self):
        return self.__username

    def __unregister(self, args = []):
        """ Unregisterer from directory server and close all connections """

        try:
            self.__cm.send(p.T_LEAVE,[])
            reply = self.__cm.receive()
            if (reply.type != p.T_ACK):
                raise Exception, "Unregistering from server was not successfull. Disconnecting anyway!"
        
        except Exception,e:
            self.__handleError('Leave', e)

    def __login(self, args = []):
        """ Authenticate with the remote server and register afterwards. """

        try:
             
            # Send username and wait for an ACK
            self.__cm.send(p.T_USER, [self.__username])
            reply = self.__cm.receive()
            
            if (reply.type != p.T_ACK):
                raise Exception, "Unable to login!"

            # Send password and wait for an ACK
            self.__cm.send(p.T_PASS, [self.__password])
            reply = self.__cm.receive()
            
            if (reply.type != p.T_ACK):
                raise Exception, "Invalid credentials!"

        except Exception,e:
            self.__handleError('Authenticate', e)
    
    def __bind(self, args = []):
        """ Start local server and bind to the port updating the server accordingly """
 
        try: 

            # Start the local chat server and be ready to receive incoming requests
            localServerPort = self.__agent.startLocalServer()

            # Sleep a little bit to allow the new thread to open the listening port
            sleep(0.3)
            
            serverIp, serverPort = self.__cm.getConnectionInfo()

            self.__cm.send(p.T_BIND, [serverIp, localServerPort])
            reply = self.__cm.receive()
            
            if (reply.type == p.T_ERR):
                raise Exception, "Port binding was not succussful!"

        except Exception,e:
            self.__handleError('Bind', e)

    def __searchUser(self, args = []):
        """ Search for username is the server's database """

        try:
            if len(args) == 0:
                self.__cm.send(p.T_QUERY, '')
            else:
                self.__cm.send(p.T_QUERY, args)

            reply = self.__cm.receive()

            if (reply is not None and reply.type == p.T_RESULT):
                [ self.__parseUserRecord(r) for r in reply.payload.split() ] 
                self.__agent.printList(self.__userList)
            else:
                raise Exception, "An error occured while fetching user data! The user list is outdated."
            
        except Exception, e:
            self.__handleError('List', e) 

    def __parseUserRecord(self, record):
        """ Parse user records and store the extracted information in a tuple in a dictionary """

        match = re.search('([a-zA-Z0-9]+),([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}),([0-9]+)', record)
        username = match.group(1)
        userIp = match.group(2)
        userPort = int(match.group(3))
        self.__userList[username] = (userIp, userPort)

    def __handleError(self, triggeredAt, msg):
        self.__agent.printMessage(str(msg), triggeredAt + " Error")
