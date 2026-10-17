"""Resource-bounded native parser process; called with server-owned paths only."""
import os
import sys
if os.name!='nt':
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,16*1024*1024))
os.execv(sys.argv[1],sys.argv[1:])
