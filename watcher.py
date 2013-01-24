from optparse import OptionParser
import time
import sys
import os
import commands
import creator
import db

debug=1
# loop: get vnc, host and tap, insert mapping
# loop: looks in process outp file for the message "died" and deletes mapping
# deletes mapping (ip,mac) 

class VMWatcher:
    def __init__(self):
        self.vmc=creator.VMCreator()
        self.db=db.VMDatabase()
        
    def initDB(self):
        try:
            self.db.init(db.defaultDb)
        except db.DatabaseException as e:  
            print e.err
            exit(1) 
            
    def watchHostParams(self,file,params):
        mustbe3=0
        while(mustbe3!=3):
            # todo check if file was created ; wait for a while 
            time.sleep(1)
            err1,exechost=commands.getstatusoutput("grep exechost {0} |grep -v grep ".format(file))
            err2,vncport=commands.getstatusoutput("grep vncport {0} |grep -v grep ".format(file))
            err3,tapname=commands.getstatusoutput("grep tapname {0} |grep -v grep ".format(file))
            if(exechost and not err1):
                print exechost
                params['exechost']=exechost.split('=')[1]
                mustbe3+=1
            if(tapname and not err1):
                print tapname
                params['tapname']=tapname.split('=')[1]
                mustbe3+=1
            if(vncport and not err1):
                print vncport
                params['vncport']=vncport.split('=')[1]
                mustbe3+=1
            
    def watchVMdies(self,file):
        vm_running=1
        while(vm_running):
            time.sleep(1)
            if(debug): sys.stdout.write("w")
            #check if file was modified recently 
            if(time.time()-os.path.getmtime(file)>5):
                print "died: ",file
                os.unlink(file)
                vm_running=0

                
################################################################################# test area

def get_opts():
    parser=OptionParser()
    parser.add_option("--file",dest="file",help="",default="") 
    parser.add_option("--vmid",dest="vmid",help="") 
    parser.add_option("--uid",dest="uid",help="")  # ['path1','path2',..]
    parser.add_option("--ip",dest="ip",help="")
    parser.add_option("--mac",dest="mac",help="")
    parser.add_option("--isolate",dest="isolate",action='store_true',help="Isolates vm from the others",default=False)
    (opts,args)=parser.parse_args()
    return opts

if __name__ == "__main__":
    args=vars(get_opts())
    
    vmw=VMWatcher()
    vmw.initDB()
    vmw.vmc.db=vmw.db #give the initialized db ref to creator.
    params={'exechost':"",'vncport':"",'tapname':""}
    vmw.watchHostParams(args['file'],params) #wait for host params (tap,vnc,hostname) #todo file
    if(debug): print "watcher",params
#    vmw.vmc.addDHCPMapping(args['uid'],args['vmid'],args['ip'],args['mac'],args['isolate'],params['exechost'],params['vncport'],params['tapname'])
    vmw.watchVMdies(args['file']) #todo file
#    vmw.vmc.removeDHCPMapping(args['ip'],args['mac'])
    