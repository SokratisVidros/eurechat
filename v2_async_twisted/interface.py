#
# interface.py
# 
# @author       : Vidros Sokratis <vidros@eurecom.fr>
# @date         : 21-1-2012 
# @copyright    : Copyright (c) 2012 Vidros Sokratis
# @license      : http://creativecommons.org/licenses/by-nd-nc/1.0/
# @version      : 1.0
# @description  : Eurechat GUI based on Curses
#

import curses, time, traceback, sys
import curses.wrapper, curses.textpad, curses.ascii
	

class CursesStdIO:
    """fake fd to be registered as a reader with the twisted reactor.
    Curses classes needing input should extend this"""
    def fileno(self):
        """ We want to select on FD 0 """
        return 0

    def doRead(self):
        """called when input is ready"""

    def logPrefix(self): return 'CursesClient'


class AsyncTextbox(curses.textpad.Textbox):
    """
    A Textbox which doesn't block the reactor.
    """

    def __init__(self, win, insert_mode=False):
        Textbox.__init__(self, win, insert_mode)
        self.completion_deferred = Deferred()

    def increment(self, char, validate=None):
        if validate:
            char = validate(char)
            if not char:
                return
        if not self.do_command(char):
            reactor.callLater(0, self.completion_deferred.callback,
                self.gather())
        self.win.refresh()


class EurechatInterface (CursesStdIO):
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

    def start(self):
        """ Start the GUI """
        
        scr = curses.initscr()
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
        
        return self.__screen
    
    def doRead(self):
        self.getInput()
    
    def connectionLost(self, reason):
        self.close()
 
    def getInput(self):
        """ Wait to get the input from the Textpad """

        self.entry.clear()
        self.entry.refresh()
        self.textbox = AsyncTextbox(self.entry)
        d = self.textbox.completion_deferred
        @d.addCallback
        def cb(s):
            self.textbox = None
            return s
        return d

        #self.textpadWin.erase()
        #return self.textpad.edit(self.__validator).strip()

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
        
    def close(self):
        """ clean up """
        curses.nocbreak()
        self.__screen.keypad(0)
        curses.echo()
        curses.endwin()