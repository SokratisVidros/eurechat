#
# agent.py
# 
# @author       : Vidros Sokratis <vidros@eurecom.fr>
# @date         : 11-1-2012 
# @copyright    : Copyright (c) 2012 Vidros Sokratis
# @license      : http://creativecommons.org/licenses/by-nd-nc/1.0/
# @version      : 1.0
# @description  : Eurechat main agent class + gui interface using curses
#

import socket
import sys
import re
import os
import curses, curses.textpad, curses.ascii

from chatClient import ChatClient
from chatServer import ChatServer



class Agent:
    """ Chat Agent is the core class of our chat application. It invokes 
        one client and one local server to send and accept messages, plus 
        the GUI class using the curses package. """

    def __init__(self, username, password, localAddress, remoteServerPort):
        """ Create a local server and a local client for the chat and start GUI """

        # Create a local client and a local server as we are peer to peer
        self.__client = ChatClient(localAddress, remoteServerPort, username, password, self)
        self.__server = ChatServer(localAddress, username, self)

        # Start GUI
        self.__gui = EurechatInterface(username, localAddress, remoteServerPort)
        curses.wrapper(self.__gui.start)

        # Authenticate the user and bind to port for chatting
        self.__client.authenticate()

    
    def prompt(self, showIntro = False):
        """ Start the simple prompt that acccepts user input.
            A few words about secret command, because of the behaviour of GLADOS,
            that speaks back to the port we opened to send him a message, we use 
            this special function to interact with her to get the secret token. 
            All the messages from other users are received at the binded port on 
            the directory server. """

        while True: 
            try:
                self.__gui.printHeader()

                # Wait for user input
                input = self.__gui.getInput()
                self.printMessage(input)

                if re.search("^bye$", input):
                    self.quit()
                    break
                elif (input.find('chat') == 0):
                    match = re.search('^chat ([a-zA-Z0-9]+) (.*)$', input)
                    username = match.group(1)
                    message = match.group(2)
                    self.__result = self.__client.chat(username, message)
                elif (input.find('list') == 0):
                    match = re.search('^list ([a-zA-Z0-9]+)$', input)
                    if (match):
                        self.__result = self.__client.search(match.group(1))
                    else:
                        self.__result = self.__client.listAll()
                elif (input.find('ping') == 0):
                    match = re.search('^ping ([a-zA-Z0-9]+)$', input)
                    if (match):
                        self.__result = self.__client.ping(match.group(1))
                elif (input.find('secret') == 0):
                    match = re.search('^secret ([a-zA-Z0-9]+) (.*)$', input)
                    username = match.group(1)
                    message = match.group(2)
                    self.__client.getSecret(username, message)
                elif re.search("^help$", input):
                    self.printMessage("Available commands:", "help")
                    self.printMessage("chat user message    : Chat with another user.", "help")
                    self.printMessage("secret user message  : Get final secret from bot_user", "help")
                    self.printMessage("list                 : List all online users.", "help")
                    self.printMessage("ping user            : Ping user.", "help")
                    self.printMessage("bye                  : I think its obvious ;)", "help")
                else:
                    raise Exception

            except Exception,e:
                self.printMessage("Invalid command, type help to list all the available commands." + str(e) + input, "error")

            except KeyboardInterrupt:
                self.quit() 
                return
            

    def startLocalServer(self):
        self.__server.start()
        return self.__server.getServerPort()     

    def printMessage(self, msg, args = ""):
        self.__gui.display(str(msg), str(args))

    def printList(self, msg):   
        self.__gui.displayAtSide(msg)

    def quit(self):
        curses.endwin() 
        self.__client.leave()
        sys.exit(0)



class EurechatInterface:
    """ Eurechat Interface using curses parkage. The screen is splitted into 3 sub-windows
        like shown above:
         ____________________________________
        |                           |        |
        |                           |        |
        |                           |        |
        |        Ouput Window       |Side Win|
        |                           |        |
        |                           |        |
        |___________________________|________|
        |          Input Textbox             |
        |____________________________________|

    """

    def __init__(self, username, host, port):
        self.__screen = None
        self.__buffer = []
        self.__textboxRow = 0
        self.__sideWinCol = 0
        self.__sideColSize = 20
        self.__info = "%s@%s:%s" % (username, host, port)
        self.outputWin = None
        self.textpadWin = None
        self.textpad = None
        self.rows, self.columns = 0, 0

    def start(self, scr):
        """ Start the GUI """

        self.__screen = scr
        self.rows, self.columns = self.__screen.getmaxyx()
        self.__textboxRow = self.rows - 2
        self.__sideWinCol = self.columns - self.__sideColSize

        # Create the 3 panels
        self.outputWin = self.__screen.subwin(self.__textboxRow - 3, self.__sideWinCol - 1, 3, 1)
        self.sideWin = self.__screen.subwin(self.__textboxRow - 4, self.__sideColSize - 1, 3, self.__sideWinCol)
        self.textpadWin = self.__screen.subwin(1, self.columns - 2, self.__textboxRow, 1)
        self.textpad = curses.textpad.Textbox(self.textpadWin)        

        self.sideWin.border(0)

        self.display("Type help to see all the available commands")
        self.__screen.refresh()
 
    def getInput(self):
        """ Wait to get the input from the Textpad """

        self.textpadWin.erase()
        return self.textpad.edit(self.__validator).strip()

    def __refreshLine(self):
        self.__screen.hline(self.__textboxRow - 1, 1, curses.ACS_HLINE, self.columns -1)

    def __rowCount(self, entry):
        return int(len(entry[0] + entry[1]) / self.columns) + 1

    def display(self, response, args = ""):
        """ Display new text on ouput window. The implementation is slow one cause the function 
            updates the screen for everynew text. We can do it in bulk in a future version.
        """

        self.__buffer.append((args, response))
        self.outputWin.erase()
        pos = 0
        toBePrinted = []
        length = 0

        for i in xrange(len(self.__buffer) - 1, -1, -1):
            c = self.__rowCount(self.__buffer[i])
            if length + c > self.outputWin.getmaxyx()[0] - 2:
                break
            length = length + c
            toBePrinted.insert(0, self.__buffer[i])

        for args, response in toBePrinted :
            if args is not "":
                args = args + ":> "
                self.outputWin.addstr(pos, 0, args, curses.A_BOLD)
                self.outputWin.addstr(pos, len(args), response)
            else:
                self.outputWin.addstr(pos, 0, response)
            pos = pos + int(len(response + args) / self.columns) + 1
        
        self.__refreshLine()
        self.outputWin.refresh()

    def displayAtSide(self, response):
        """ Display new text on side Screen """

        self.sideWin.erase()
        pos = 1
        length = 0

        self.sideWin.border(0)

        for r in response:
            c = self.__rowCount(r)
            if ((length + c) > (self.columns - self.__sideWinCol) or pos > self.__textboxRow - 4):
                break
            self.sideWin.addstr(pos, 1, r)
            pos = pos + 1

        self.__refreshLine()
        self.sideWin.refresh()

    def printHeader(self):
        """ Print header info at the top of the screen """

        self.__screen.addstr(0, 0, " " * self.columns, curses.A_REVERSE)
        self.__screen.addstr(0, 0, "Welcome to Eurechat   " + self.__info, curses.A_REVERSE)
        self.__screen.addstr(2, self.__sideWinCol, "Online users:" + " " * 7, curses.A_REVERSE)
        self.__screen.refresh()

    def __validator(self, c):
        if c == curses.ascii.NL:
            return curses.ascii.BEL
        else:
            return c


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
    
    a = Agent(settings['username'], settings['password'], settings['local_ip'], settings['remote_server_port'])
    a.prompt()


if __name__ == "__main__":
    main()
