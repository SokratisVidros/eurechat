'''
 _   _      _          _____ 
| \ | |    | |        |_   _|
|  \| | ___| |___      _| |  
| . ` |/ _ \ __\ \ /\ / / |  
| |\  |  __/ |_ \ V  V /| |_ 
|_| \_|\___|\__| \_/\_/_____|

Introduction to computer networking and Internet
Corrado Leita - corrado_leita@symantec.com
================================================
Eurechat directory service
'''
import threading
import logging
import socket
import os

import parsing as p
from protocol import ProtocolWrapper


class DirectoryChecker(threading.Thread):
    """
    This thread is used to verify the proper behavior
    of all the clients registered to the directory
    """
    LOOP_WAIT = 10
    
    def __init__(self,directory):
        """
        The constructor takes as input the directory object
        """
        threading.Thread.__init__(self)
        self.daemon=True
        
        self.__directory=directory
        self.__logger=logging.getLogger("checker")
        
    def run(self):
        """
        Continuously verify for the correct operation of the registered
        clients
        """
        import time
        
        while True:
            #sleep for a while at every loop
            time.sleep(DirectoryChecker.LOOP_WAIT)
            
            #generate the list of registered users
            users=[i[0] for i in self.__directory.directory_query()]
            self.__logger.debug("%d users are active"%len(users))
            
            for username in users:
                #retrieve the bind information for each user
                res=self.__directory.directory_query(username)
                username,address,port=res[0] if len(res)==1 else (username,None,None)
                
                if address!=None and port!=None:
                    try:
                        self.__logger.debug("connecting to %s:%d"%(address,port))
                        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                        sock.connect((address,port))

                        #use the protocol wrapper to simplify socket handling
                        proto=ProtocolWrapper(sock,(address,port))
                        #send a ping, and wait for a pong
                        self.__logger.debug("sending ping")
                        proto.send(p.T_PING)

                        msg=proto.recv()
                        
                        
                        if msg!=None and msg.type==p.T_PONG:
                            self.__logger.info("USER %s OK"%username)
                            proto.close()
                        else:
                            raise Exception, "no PONG received"
                        
                    except Exception,e:
                        #client is misbehaving, deregister it
                        self.__logger.error("USER %s ERROR (%s)"%(username,str(e)))
                        self.__directory.directory_deregister(username)
                        
                    
        
class Directory:
    """
    Directory information. All the methods 
    defined in this object are required to be thread
    safe, since the object will be shared among all
    threads in concurrency
    """
    
    def __init__(self):
        """
        Define here all the synchronization objects
        """
        #directory is a dictionary mapping usernames to
        #their address and ports
        self.__directory=dict()
        self.__directory_lock=threading.Lock()
        #our logger
        self.__logger=logging.getLogger("directory")
    
    def directory_login(self,username,password):
        """
        Implement access control here. Return true
        if the username has logged in successfully, 
        false otherwise
        """
        return True
    
    def directory_register(self,username,address,port):
        """
        Register a specific client in the directory service
        """
        self.__logger.info("REGISTER %s %s %d"%(username,address,port))
        self.__directory_lock.acquire()
        self.__directory[username]=(address,port)
        self.__directory_lock.release()
        
    def directory_deregister(self,username):
        """
        Deregister a specific user from the directory service
        """
        self.__logger.info("DEREGISTER %s"%username)
        self.__directory_lock.acquire()
        if username in self.__directory:
            self.__directory.pop(username)
        self.__directory_lock.release()
    
    def directory_query(self,username=None):
        """
        Always returns a list of tuples (username,address,port).
        If username is not None, it will return a list containing
        only one tuple associated to the specific username.
        """
        res=[]
        self.__directory_lock.acquire()
        if username!=None and username in self.__directory:
            res.append((username,self.__directory[username][0],self.__directory[username][1]))
        elif username==None:
            res+=[(key,value[0],value[1]) for key,value in self.__directory.items()]
        self.__directory_lock.release()
        
        return res
        
        

class DirectoryClient(threading.Thread):
    """
    Separate thread in charge of the communication
    with each client.
    """
    def __init__(self,directory,clisock,addrinfo):
        """
        The thread takes as input three arguments:
        1) the instance of the directory object that accepted the connection
        2) the connected socket associated with the client
        3) the address info tuple
        """
        threading.Thread.__init__(self)
        
        self.username=None
        self.password=None
        self.bind_address=None
        self.bind_port=None
        
        self.__directory=directory
        self.__protocol=ProtocolWrapper(clisock,addrinfo)
        
        #we are not interested in joining these threads
        self.daemon=True
        #the logger
        self.__logger=logging.getLogger("client")
        
        
        
    def __port_test(self):
        """
        Simple check to ensure the reachability of a client before
        registering it to the directory service.
        """
        try:
            s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            s.connect((self.bind_address,self.bind_port))
            s.close()
            self.__logger.debug("port test successful %s"%self.username)
            return True
        except socket.error:
            self.__logger.error("port test failed %s"%self.username)
            return False
        
    def run(self):
        """
        The thread executes here.
        """
        #user authentication
        try:
            #get the username
            msg=self.__protocol.recv(True)
            if msg==None or msg.type!=p.T_USER or len(msg.args)!=1: return self.__protocol.close("a 'USER <username>' command was expected!")
            self.username=msg.args[0]
            if not self.__protocol.send(p.T_ACK,[],"hi %s, authentication required"%self.username): return self.__protocol.close()

            #get the password
            msg=self.__protocol.recv(True)
            if msg==None or msg.type!=p.T_PASS or len(msg.args)!=1: return self.__protocol.close("a 'PASS <password>' command was expected!")
            self.password=msg.args[0]
            
            if self.__directory.directory_login(self.username, self.password):
                if not self.__protocol.send(p.T_ACK,[],"successfully authenticated"): return self.__protocol.close()
            else:
                return self.__protocol.close("authentication failed")
            
            #if we are here, we are successfully authenticated
            #from now on, the client can send any sequence of queries, bind or leave commands
            while True:
                msg=self.__protocol.recv()
                if msg==None:   return self.__protocol.close() #connection was closed by client
                
                if msg.type==p.T_BIND and len(msg.args)==2:
                    self.bind_address=msg.args[0]
                    self.bind_port=int(msg.args[1])
                    
                    if self.__port_test():
                        self.__directory.directory_register(self.username, self.bind_address, self.bind_port)
                        if not self.__protocol.send(p.T_ACK,[],"bound successfully to %s:%d"%(self.bind_address,self.bind_port)): return self.__protocol.close()
                    else:
                        return self.__protocol.close("invalid bind notification")
                        
                elif msg.type==p.T_QUERY and len(msg.args)<=1:
                    username=msg.args[0] if len(msg.args)==1 else None
                    result=self.__directory.directory_query(username)
                    payload="\n".join(["%s,%s,%d"%i for i in result])
                    
                    if not self.__protocol.send(p.T_RESULT,[],payload): self.__protocol.close()
                elif msg.type==p.T_LEAVE and len(msg.args)==0:
                    self.__directory.directory_deregister(self.username)
                    if not self.__protocol.send(p.T_ACK,[],"deregistered from directory"): return self.__protocol.close()
                else:
                    return self.__protocol.close("I did not understand the message %s"%msg.type)
                    
        except socket.timeout:
            self.__protocol.close("shutting down idle connection (timeout)")
        except:
            self.__protocol.close("unexpected error")
            self.__logger.exception("something unexpected went wrong!")

class Server:
    """
    Main directory server class. Keeps track of connected clients
    and 
    """
    
    def __init__(self,address="127.0.0.1",port=8888):
        """
        Upon construction, let's bind the socket that
        will be used for the interaction with the clients
        """
        self.__sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.__sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,True)
        self.__sock.bind((address,port))
        self.__sock.listen(15)
        
        #the directory service, shared among all threads
        self.__directory=Directory()
        #the directory checker, that ensures everything is behaving well
        self.__checker=DirectoryChecker(self.__directory)
        
        #logger
        self.__logger=logging.getLogger("server")
        self.__logger.info("waiting for connections on %s:%d"%(address,port))
        
    
    def main_loop(self):
        """
        This is the loop in which the main thread will
        continuously accept new connections and assign them 
        to new threads
        """
        self.__checker.start()
        while True:
            try:
                clisock,addr=self.__sock.accept()
            except KeyboardInterrupt,e:
                return 
            except:
                clisock=addr=None
            
            if clisock!=None:
                d=DirectoryClient(self.__directory,clisock,addr)
                d.start()



if __name__=="__main__":
    os.system('clear')

    from optparse import OptionParser
    from cliutils import daemonize,setup_logging
    
    op=OptionParser()
    op.add_option("-v","--verbose",dest="verbose",action="store_true",help="Enable debug output")
    op.add_option("-D","--daemon",dest="daemon",action="store_true",help="Daemonize process")
    op.add_option("-l","--logfile",dest="logfile",type="str",help="Store logs to a file instead of standard output")
    
    (values,args)=op.parse_args()
    
    if values.daemon==True:
        print "Starting daemon process!"
        #daemonize()
    
    setup_logging(verbose=values.verbose, logfile=values.logfile)
    
    s=Server()
    s.main_loop()
    
