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
Simple message parser
'''
import re

# === Definition of the message types ===

#used to provlde a username (as argument)
T_USER="USER"
#used to provide a password (as argument)
T_PASS="PASS"
#used to provide an IP address and port in which the client is reachable
T_BIND="BIND"
#used by a user to notify its intention to leave the chat and undo the binding
T_LEAVE="LEAVE"
#command to query the directory service. An optional argument cna be
#used to query the directory service for a specific user. Providing
#no arguments will generate a list of all users
T_QUERY="QUERY"
#sent by the server to ack the reception and successful completion
#of a command that does not expect any result (USER or PASS)
T_ACK="ACK"
#sent by the server to let the client know that something went wrong
T_ERR="ERR"
#sent by the server in response to a command that expects some result
#in return. The result is in the payload of the message.
T_RESULT="RESULT"
#keep alive messages, to verify the correct operation of a client.
#any client must respond to a PING message with a PONG
T_PING="PING"
T_PONG="PONG"
#message to be exchanged among clients. The message passes as 
#argument the username of the sender, and contains the message
#as payload
T_MESSAGE="MESSAGE"

def parse(buf):
    """
    Tries to extract one message from a string buffer.
    It returns the remaining unparsed buffer, and the 
    extracted message
    """
    m=Message()
    consumed=m.parse(buf)
    toparse=buf[consumed:]
    
    return (toparse,m) if consumed>0 else (toparse,None) 
    

def parse_all(buf):
    """
    Tries to "consume" a string buffer and convert it to 
    Message objects. Returns the remaining part of the 
    buffer that was not yet converted to an object (e.g.
    truncated messages) and a list of fully parsed messages.
    """
    parsed=[]
    toparse=buf
    
    while len(toparse)>0:
        toparse,m=parse(toparse)
        
        if m==None and len(toparse)>0:
            #we are probably dealing with a truncated message.
            #not all the payload was received yet, and so it
            #can't be consumed. We can't do anything else.
            break
        elif m!=None:
            #the message was parsed correctly
            parsed.append(m)
        
    return toparse,parsed


class Message:
    
    def __init__(self,message_type=None,message_args=[],message_payload=""):
        """
        Parses a basic protocol message. The protocol syntax is 
        a simplification of the HTTP one. Each message starts with a 
        header line, which contains the message type (an uppercase string),
        the payload length (0 implies no payload), and a list of space-separated
        parameters. Only alphanumeric characters are accepted. The header line
        always ends with a "\n" character.
        The header line can be followed by a payload whose length was specified
        in the header.
        """
        self.type=message_type
        self.args=message_args
        self.payload=message_payload
        
    def parse(self,buf):
        """
        Consume data from a buffer and parse the first message.
        The provided buffer is a string.
        Returns the number of messages consumed from the buffer 
        (if any)
        """
        #number of consumed bytes
        consumed=0
        
        #use this regular expression to parse the header
        #If you are not familiar with regular expressions, have
        #a look to the following page: http://docs.python.org/library/re.html
        match=re.match("(?P<type>\w+) (?P<len>\d+)(?P<args>( \S+)*)\n",buf)
        if match:
            #the header was parsed correctly
            hlen=match.end() #last character matched by the regular expression
            m_type=match.groupdict()["type"]
            m_len=int(match.groupdict()["len"])
            m_args=[i for i in match.groupdict()["args"].strip().split(" ") if len(i)>0]
            
            
            if len(buf)>=hlen+m_len:
                #all the payload is there.
                payload=buf[hlen:hlen+m_len]
                consumed=hlen+m_len
                
                #we can populate the message
                self.type=m_type
                self.args=m_args
                self.payload=payload
        
        return consumed
            
        
    def __str__(self):
        """
        Create the message
        """
        if len(self.args):
            return "%s %d %s\n"%(self.type,len(self.payload)," ".join(map(str,self.args)))+self.payload
        else:
            return "%s %d\n"%(self.type,len(self.payload))+self.payload
    
    def __repr__(self):
        """
        Representation of the message in the interpreter
        """
        return "Message(%s,%s,%s)"%(repr(self.type),repr(self.args),repr(self.payload))
    

if __name__=="__main__":
    #let's test whether it works!
    
    #create a message, and then parse it
    m=Message(T_RESULT,[],"This is a result")
    #convert it to string
    buf=str(m)
    #add a second message
    m=Message(T_USER,["corrado"])
    buf+=str(m)
    
    buf,parsed=parse(buf)
    
    print repr(buf),parsed