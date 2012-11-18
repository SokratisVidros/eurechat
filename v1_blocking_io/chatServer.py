#
# chatServer.py
# 
# @author       : Vidros Sokratis <vidros@eurecom.fr>
# @date         : 9-1-2012 
# @copyright    : Copyright (c) 2012 Vidros Sokratis
# @license      : http://creativecommons.org/licenses/by-nd-nc/1.0/
# @version      : 1.0
# @description  : Chat server class in a new thread
#

import sys
import parsing as p
import threading
import socket

from parsing import Message
from connectionManager import ConnectionManager



class ChatServer(threading.Thread):
    """ Chat Server class initializes a daemon for each incoming request. """

    def __init__(self, host, username, agent):
        threading.Thread.__init__(self)
        self.daemon = True
        self.__agent = agent
        self.__username = username
        self.__sock = ConnectionManager.createListeningSocket(host)

    def getServerPort(self):
        return self.__sock.getsockname()[1]
 
    def run(self):

        try:

            # Listen to maximum 5 queued connections. We use the queue here to avoid 
            # invoking a new thread for each incoming message
            self.__sock.listen(5)
            while True:
               self.conn, self.addr = self.__sock.accept()
               while True:
                   data = self.conn.recv(1024)
                   if not data:
                        break

                   message = self.parseMsg(data)

                   if len(message) > 0:
                       if message[0].type == p.T_PING:
                           pong = Message("PONG", [self.__username])
                           self.conn.send(str(pong))
                       elif message[0].type == p.T_MESSAGE:
                           self.__agent.printMessage(message[0].payload,message[0].args.pop())
        
        except Exception ,e:
            self.__handleError(str(e))

        finally:
            self.conn.close()

    def parseMsg(self, msg):
        return filter(None, list(p.parse(msg)))

    def __handleError(self, msg):
        self.__agent.printMessage(str(msg), "Server Error")
