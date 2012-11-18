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
Various useful command line tools
'''
import sys,os,logging

def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    """
    Call this to daemonize your process. Daemonizing a process allows you
    to detatch the process from the command line (remember orphan processes
    and reparenting...?). 
    """
    
    # Perform first fork.
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0) # Exit first parent.
    except OSError, e:
        sys.stderr.write("fork #1 failed: (%d) %sn" % (e.errno, e.strerror))
        sys.exit(1)
    # Decouple from parent environment.
    os.chdir("/")
    os.umask(0)
    os.setsid( )
    # Perform second fork.
    try:
        pid = os.fork( )
        if pid > 0:
            sys.exit(0) # Exit second parent.
    except OSError, e:
        sys.stderr.write("fork #2 failed: (%d) %sn" % (e.errno, e.strerror))
        sys.exit(1)
    # The process is now daemonized, redirect standard file descriptors.
    for f in sys.stdout, sys.stderr: f.flush( )
    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    os.dup2(si.fileno( ), sys.stdin.fileno( ))
    os.dup2(so.fileno( ), sys.stdout.fileno( ))
    os.dup2(se.fileno( ), sys.stderr.fileno( ))

    
def setup_logging(verbose=True,logfile=None):
    """
    Function that sets up the logging module to either output
    to the standard output (StreamHandler) or to output to a file
    (FileHandler). Setting the verbose flag to False sets the 
    debugging level to INFO.
    """
    l=logging.getLogger()
    
    l.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    formatter=logging.Formatter("[%(asctime)s] %(levelname)-6s  %(name)-35s %(message)s ")
    
    if logfile!=None:
        handler=logging.FileHandler(logfile)
    else:
        handler=logging.StreamHandler()
    
    handler.setFormatter(formatter)
    l.addHandler(handler)

