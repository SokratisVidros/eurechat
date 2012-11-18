#
# agent.py
#
# @author       : Vidros Sokratis <vidros@eurecom.fr>
# @date         : 21-1-2012
# @copyright    : Copyright (c) 2012 Vidros Sokratis
# @license      : http://creativecommons.org/licenses/by-nd-nc/1.0/
# @version      : 1.0
# @description  : Eurechat main agent class. Unfortunately, 3
# @note         : Unfortunately, i didn't had the luxury of time to add the
#                 curses graphical interface of the first project to the second one 
#                 cause it proved to be quite tricky. Twisted and Curses modules 
#                 need a special handling in order to synchronize.
#                 Also, some corner cases need to be implemented throroughly
#                 (see the @ TODO annotation)
#

import sys
import re
import os

from twisted.internet import reactor,protocol,stdio
from chatClient import ChatClientFactory
from chatServer import ChatServerFactory


        
class Agent(protocol.Protocol):
    """ Chat Agent Class handles the user input and dispatches the commands accordingly. """
    
    prompt = "\n>>> "
    
    def __init__(self, cClient):
        self.__cClient = cClient
    
    def connectionMade(self):
        self.transport.write("Welcome to Eurechat!\n")
        self.transport.write("User %s, connected at %s\n" %(self.__cClient.username, self.__cClient.host)) 
        self.transport.write("\nType help to see all the available commands.\n")
        self.transport.write(self.prompt)
        
    def connectionLost(self, reason):
        self.quit()
    
    def dataReceived(self,data):
        data=data.strip()
        if len(data)>0:
            self.parseCmd(data)
            self.transport.write(self.prompt)
        else:
            self.transport.loseConnection()

    def parseCmd(self, input):
        """ Parse user's input and execute the corresponding command. """
            
        try:
            if re.search("^bye$", input):
                self.quit()
            elif (input.find('chat') == 0):
                match = re.search('^chat ([a-zA-Z0-9]+) (.*)$', input)
                username = match.group(1)
                message = match.group(2)
                self.__result = self.__cClient.chat(username, message)
            elif (input.find('list') == 0):
                match = re.search('^list ([a-zA-Z0-9]+)$', input)
                if (match):
                    self.__result = self.__cClient.search(match.group(1))
                else:
                    self.__result = self.__cClient.listAll()
            elif (input.find('ping') == 0):
                match = re.search('^ping ([a-zA-Z0-9]+)$', input)
                if (match):
                    self.__result = self.__cClient.ping(match.group(1))
            elif (input.find('secret') == 0):
                match = re.search('^secret ([a-zA-Z0-9]+) (.*)$', input)
                username = match.group(1)
                message = match.group(2)
                self.__cClient.getSecret(username, message)
            elif re.search("^help$", input):
                self.printMessage("Available commands:", "help")
                self.printMessage("chat user message    : Chat with another user.", "help")
                self.printMessage("list                 : List all online users.", "help")
                self.printMessage("ping user            : Ping user.", "help")
                self.printMessage("bye                  : I think its obvious ;)", "help")
            else:
                raise Exception, "Invalid command " + input + ", type help to list all the available commands."

        except Exception,e:
            self.printMessage("Invalid command. Type help to list all the available commands", "error")

        except KeyboardInterrupt:
            self.quit()
            return
    
    def printMessage(self, msg, args = ""):
        self.transport.write("%s:> %s\n" % (str(args), str(msg)))

    def printList(self, msg):
        self.transport.write(msg)
        
    def quit(self):
        reactor.stop()



##############################################################################################################
# Launching using main function
##############################################################################################################

def main():

    os.system('clear')

    if (len(sys.argv) < 3):
        sys.stderr.write("Usage: %s username password\n"%sys.argv[0])
        sys.exit(1)

    settings = { 'local_ip'           : '127.0.0.1',
                 'remote_server_port' : 8888 ,
                 'username'           : sys.argv[1],
                 'password'           : sys.argv[2]
               }

    # Start the listening server
    cServer = reactor.listenTCP(0, ChatServerFactory(settings['username']))

    # Start the client
    cClient = ChatClientFactory(settings['username'], settings['password'], settings['local_ip'], cServer.getHost().port)

    # Start the Stdio protocol
    stdio.StandardIO(Agent(cClient))

    reactor.connectTCP( settings['local_ip'], settings['remote_server_port'], cClient)
    
    reactor.run()


if __name__ == "__main__":
    main()
