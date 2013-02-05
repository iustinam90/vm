#!/usr/bin/python -u
import commands
import ast
import datetime
import subprocess
import os
import time
import sys
from optparse import OptionParser
import socket


ifup="/etc/qemu-scripts/ifup-vlan9.sh"

class VMStarter:
    def __init__(self):pass
        
    # --vmrun --vm _id/name [--mem _ --smp _ --install --cdrom _ --isolate] 
    def getHostParams(self,params):        
        params['exechost']=self.getExechost()
        params['vncport']=self.genVNCport()
        params['tapname']='tapxx'
    
    def startVM(self,disc_paths,smp,mem,ip,mac,exechost,vncport,tapname,install,cdrom,isolate):
        # create command
        optional_install=""
        if(cdrom): optional_install=" -boot d -cdrom {0} ".format(cdrom)
        hdds=""
        if(len(disc_paths)>=1): hdds+=" -hda {0} ".format(disc_paths[0])
        if(len(disc_paths)>=2): hdds+=" -hdb {0} ".format(disc_paths[1])
        if(len(disc_paths)>=3): hdds+=" -hdc {0} ".format(disc_paths[2])
        if(len(disc_paths)>=4): hdds+=" -hdd {0} ".format(disc_paths[3])
        

        cmd="/usr/libexec/qemu-kvm {0} -vnc :{1} -m {2} -smp {3} -net nic,macaddr={4} -net tap,script={5} {6}  &".format(hdds,vncport%100,mem,smp,mac,ifup,optional_install)
#        cmd="/usr/libexec/qemu-kvm {0} -vnc :{1} -m {2} -smp {3}".format(hdds,vncport%100,'1G',1)
        print cmd
        
        if(subprocess.call(cmd,shell=True)): print "error calling kvm";exit(1)
        while(1):
            print "waiting ",os.getpid()
            time.sleep(5)
            sts,outp=commands.getstatusoutput("ps aux |grep /usr/libexec/qemu-kvm |grep {0} |grep -v grep ".format(disc_paths[0])) #there are 2 processes (this one that waits, and the kvm)
            print "ps: ",sts,outp
            if(not outp): 
                self.sendMessageToServer(repr({'dead':1}))
                self.sock.close()
                exit(1)
                
        
#        child_pid = os.fork() #if not fork will lose output..dunno why yet
#        if child_pid == 0:      
#            if(subprocess.call(cmd,shell=True)): print "error calling kvm";exit(1)
#        else:
#            print "Your vm is accessible via host {0} vnc port {1}, display {2}".format(exechost,vncport,vncport%100)
#            vm_running=1
#            while(vm_running):
#                time.sleep(2)
#                # todo prin smth in out to let the controller know if vm is still running
#                sys.stdout.write("k")
#                if(not commands.getstatusoutput("ps aux |grep {0} |grep -v grep ".format(disc_paths[0]))[1]):
#                    print "vm process died"
#                    vm_running=0
    
    def connectToServer(self,ip,port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock=s
        print "connecting to {0} {1}".format(ip,port)
        self.sock.connect((ip, port))
        print "connected to {0} {1}".format(ip,port)

    def sendMessageToServer(self,msg):
        print "sending ",msg
        self.sock.sendall(msg) #sends the entire message (in pieces if necessary)
        print "sent"
    
    def getExechost(self):
        return commands.getstatusoutput("hostname")[1]
    
    def genVNCport(self):
        ls=range(5901,5999) #todo ce porturi poate avea vnc
        #netstat -an |grep :59 |tr -s ' ' |cut -d' ' -f4 | cut -d: -f2  >>> [5901,5902,...]
        p=subprocess.Popen("netstat -an |grep :59 |tr -s ' ' |cut -d' ' -f4 | cut -d: -f2",shell=True,stdout=subprocess.PIPE)
        for used_port in p.stdout.readlines():
            if int(used_port) in ls:
                ls.remove(int(used_port))
        return min(ls)
    
################################################################################# test area

def get_opts():
    parser=OptionParser()
    parser.add_option("--vmid",dest="vmid",help="",default="") #todo do not use, now use for output filename
    parser.add_option("--discs",dest="discs",help="")  # ['path1','path2',..]
    parser.add_option("--ip",dest="ip",help="")
    parser.add_option("--mac",dest="mac",help="")
    parser.add_option("--smp",dest="smp",help="# processors, default 1",default=1)
    parser.add_option("--mem",dest="mem",help="memory in megabytes (eg '512' or '512M','1G'), default 512",default="1G")
    parser.add_option("--isolate",dest="isolate",action='store_true',help="Isolates vm from the others",default=False)
    parser.add_option("--install",dest="install",action='store_true',help="if specified, the vm will boot from the cdrom (which must be specified also)",default=False)
    parser.add_option("--cdrom",dest="cdrom",help="specify .iso installation file")
    parser.add_option("--srvhost",dest="srvhost")
    parser.add_option("--srvport",dest="srvport")
    (opts,args)=parser.parse_args()
    return opts
    
if __name__=="__main__":
    vms=VMStarter()
    args=vars(get_opts())
    
    if(args['vmid']):
        sys.stdout = open(args['vmid'], 'w')
    
    params={'exechost':"",'vncport':"",'tapname':""}
    vms.connectToServer(args['srvhost'], int(args['srvport']))
    vms.getHostParams(params)
    vms.sendMessageToServer(repr(params))
    
#    print "exechost=",params['exechost']
#    print "vncport=",params['vncport']
#    print "tapname=",params['tapname']
    discs=args['discs'].split(",")
    vms.startVM(discs, args['smp'], args['mem'], args['ip'], args['mac'], params['exechost'],params['vncport'],params['tapname'],
                 args['install'], args['cdrom'], args['isolate']) #to send out filename to kid process (only used if started without qsub)
    
