#
# ConnectionManager.py
# 
# @author       : Vidros Sokratis <vidros@eurecom.fr>
# @date         : 8-1-2012 
# @copyright    : Copyright (c) 2012 Vidros Sokratis
# @license      : http://creativecommons.org/licenses/by-nd-nc/1.0/
# @version      : 1.0
# @description  : Connection Manager classs
#

import socket
import sys
import parsing as p

from threading import Timer



class ConnectionManager:
    """ Simple Socket Connection Manager with blocking IO. """

    def __init__(self, host, port, sock = None):
        if sock is None:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        else:
            self.__sock = sock
        
        self.__sock.settimeout(10)
        self.__host = host
        self.__port = port
        self.__buffer = ''

    def getConnectionInfo(self):
        return self.__host, self.__port

    def connect(self):
        """ Connect to specific socket """
        
        try:
            self.__sock.connect((self.__host, self.__port))

        except socket.error,e:
            print 'Oops, unable to connect. Try again!',e
            sys.exit(1)

    def sendRaw(self, msg, echo = False):
        """ Sending raw data over socket """

        sent = self.__sock.send(msg)
        if sent > 0 and echo:
            print "Sent: %s"%msg,

    def send(self, msgType, msgArgs = [], msgPayload = ""):
        """ Send a message over socket """

        m = p.Message(msgType, msgArgs, msgPayload)

        try:
            self.__sock.sendall(str(m))
            return True
        except Exception,e:
            print 'Something went wrong while sending your message :(', e

    def receiveRaw(self, echo = False):
        """ Receive raw data """

        try:
            received_data = ''
            while 1:
                chunk = self.__sock.recv(256)
                if not chunk:
                    break
                received_data += chunk

        except socket.error, e:
            # @TODO error handling
            print e

        finally:
            if echo:
                print received_data,
            return received_data

    def receive(self, echo = False):
        """ Receive messages """

        msg=None
        
        while msg == None:
            try:
                pay = self.__sock.recv(1024)
                self.__buffer+=pay
                
                if not pay:
                    break

            except socket.error,e:
                break
            
            self.__buffer, msg = p.parse(self.__buffer)

        return msg

    def disconnect(self):
        self.__sock.close()

    @staticmethod
    def createListeningSocket(host):
        """ Create a listening server socket """

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, 0))
        return sock
