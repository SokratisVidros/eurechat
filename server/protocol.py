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
Wrapper to simplify protocol interaction
'''
import logging,socket
import parsing as p

class ProtocolWrapper:
    """
    Wrap a socket object and simplify
    the socket interaction. All the methods can 
    raise a socket.timeout, that needs to be handled 
    by the caller.
    """
    
    def __init__(self,socket,addrinfo):
        self.__sock=socket
        self.__address=addrinfo
        
        #the receiving buffer
        self.__buffer=""
        #the logger for the object
        self.__logger=logging.getLogger("endpoint.%s:%d"%self.__address)
        #set a timeout for the socket. Don't block for more than 30s
        self.__sock.settimeout(30)
        
        self.__logger.debug("new connection")
        
        
        
    def recv(self, echo = False):
        """
        Tries to receive one complete message from the buffer.
        Returns None if client disconnected or if an error occurred.
        """
        msg=None
        
        #continue to receive until at least one message is produced
        while msg==None:
            try:
                pay=self.__sock.recv(1024)
                self.__buffer+=pay
                
                #client may have disconnected
                if not pay:     break
            except socket.error,e:
                self.__logger.error("receive error: %s"%str(e))
                break
            
            self.__buffer,msg=p.parse(self.__buffer)
        
        return msg
    
    def send(self,message_type,message_args=[],message_payload=""):
        """
        Returns true if the send was successful
        """
        m=p.Message(message_type,message_args,message_payload)
        
        try:
            #shortcut to ensure we have sent all the payload.
            #it calls send multiple times until all the data has been sent
            self.__sock.sendall(str(m))
            return True
        except socket.error,e:
            self.__logger.error("send error: %s"%str(e))
            return False
    
    def close(self,failure=None):
        """
        Shutdown the socket. If a failure string is provided, 
        send back an ERR message to the client
        """
        if failure!=None:
            self.__logger.debug("failure: %s"%failure)
            #send an error message, or at least try to...
            self.send(p.T_ERR,[],failure)
        
        self.__logger.debug("closing connection")
        self.__sock.close()
