#!/usr/bin/python
#import pypureomapi
import commands
import ast
import datetime
import subprocess
import os
import time
import sys
from optparse import OptionParser

#import db

br_name="vbr0" # are 192.168.100.1

#dhcp_keyname = "omapi_key"
#dhcp_secret = "KaekLmmyUj2RLvC8c1lj15AJ3gOIScUo/PjabCirckCw1lxSAj0hyIEASRaptg3gk33XHUrglPzQK1len7LhMQ=="
#dhcp_server = "127.0.0.1"
#dhcp_port = 9991



class VMStarter:
    def __init__(self):pass
        
    # --vmrun --vm _id/name [--mem _ --smp _ --install --cdrom _ --isolate] 
    # hd is a list of paths (hda->hdd)
    
    def getHostParams(self,params):
        # db
#        self._initDB()

#        disc_paths=discs.keys() 
#        disc_paths.sort()       #put them in order : _0.qcow2,_1.qcow2 etc
#        ip=self.genFreeIP(real_uid)
#        mac=self.genMACfromIP(ip)
        
        params['exechost']=self.getExechost()
        params['vncport']=11
        params['tapname']='tapxx'
#        params['exechost']=self.getExechost()
#        params['vncport']=self.genVNCport()
#        params['tapname']=self.genTap()
        
#        self.addDHCPMapping(real_uid,vm_id,ip,mac,isolate,exechost,vncport,tapname)
#        self.connectToNetwork(tapname)
#        if(isolate): 
#            self.isolateVM(ip,mac,tapname) # mac spoof, inter vm traffic
#        self.startVM(disc_paths,smp,mem,ip,mac,exechost,vncport,tapname,install,cdrom)
    
    def startVM(self,disc_paths,smp,mem,ip,mac,exechost,vncport,tapname,install,cdrom,isolate):
        self.connectToNetwork(tapname)
#        if(isolate): 
#            self.isolateVM(ip,mac,tapname) # mac spoof, inter vm traffic
        # create command
        optional_install=""
        if(cdrom): optional_install=" -boot d -cdrom {0} ".format(cdrom)
        hdds=""
        if(len(disc_paths)>=1): hdds+=" -hda {0} ".format(disc_paths[0])
        if(len(disc_paths)>=2): hdds+=" -hdb {0} ".format(disc_paths[1])
        if(len(disc_paths)>=3): hdds+=" -hdc {0} ".format(disc_paths[2])
        if(len(disc_paths)>=4): hdds+=" -hdd {0} ".format(disc_paths[3])
        
        #/usr/libexec/qemu-kvm [ -boot d -cdrom ..iso ] -hda vm1.qcow2 -vnc :10 -m 1G -smp 1 -net nic,macaddr=DE:AD:BE:EF:CF:87 -net tap,ifname=tap0,script=no,downscript=no &
#        cmd="/usr/libexec/qemu-kvm {0} -vnc :{1} -m {2} -smp {3} -net nic,macaddr={4} -net tap,ifname={5},script=no,downscript=no \
#        {6}  &".format(hdds,vncport%100,mem,smp,mac,tapname,optional_install)
        cmd="/usr/libexec/qemu-kvm {0} -vnc :{1} -m {2} -smp {3}".format(hdds,11,'1G',1)
        print cmd
        if(subprocess.call(cmd,shell=True)): print "err";exit(1)
        # todo check if vm is actually running
        print "Your vm is accessible via host {0} vnc port {1}, display {2}".format(exechost,vncport,vncport%100)
        
        #fork to watch this process 
        child_pid = os.fork()
        if child_pid == 0:
#            print "redirect ",redirect_file
#            if(redirect_file): 
#                sys.stdout = open(redirect_file, 'w')
            print "Child Process: PID# %s" % os.getpid()
            vm_running=1
            while(vm_running):
                time.sleep(1)
                # todo prin smth in out to let the controller know if vm is still running
                if(not commands.getstatusoutput("ps aux |grep {0} |grep -v grep ".format(disc_paths[0]))[1]):
                    print "vm process died"
                    vm_running=0
#                    self.removeTap(tapname)
#                    self.alterEbtables("D",ip,mac,tapname)
                
        elif child_pid == -1:
            print "err fork"
        else:
            print "Parent terminating: PID# %s" % os.getpid()
    
#    def _initDB(self):
#        try:
#            self.db=db.VMDatabase()
#            self.db.init(db.defaultDb)
#        except db.DatabaseException as e:  
#            print e.err 

    
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
    
    def genTap(self): 
        ls=range(0,100)
        # ifconfig -a |grep tap |cut -d' ' -f1
        p=subprocess.Popen("ifconfig -a |grep tap |cut -d' ' -f1",shell=True,stdout=subprocess.PIPE)
        for used_tap in p.stdout.readlines():
            if int(used_tap[3]) in ls: # last digit tap0 >> 0
                ls.remove(int(used_tap[3]))
        return "tap"+str(min(ls))
    
    def connectToNetwork(self,tapname):
        # create tap, add to br
        if(subprocess.call("tunctl -t {0}".format(tapname),shell=True)): print "err"; exit(1)
        if(subprocess.call("brctl addif {0} {1}".format(br_name,tapname),shell=True)): print "err"; exit(1)
        if(subprocess.call("ip link set {0} up".format(tapname),shell=True)): print "err"; exit(1)
        
    def isolateVM(self,ip,mac,tapname):
        print "..isolating vm"
        self.alterEbtables("A",ip,mac,tapname)
    
    def removeTap(self,tapname):
        if(subprocess.call("tunctl -d {0}".format(tapname),shell=True)): print "err"; exit(1)
     
    def alterEbtables(self,action,ip,mac,tapname):
        # mac spoofing
        if(subprocess.call("ebtables -{0} FORWARD -i {1} -s ! {2} -j DROP".format(action,tapname,mac),shell=True)): print "err"; exit(1)
        # ip spoofing
        if(subprocess.call("ebtables -{0} FORWARD -p IPv4 --ip-src ! {1} -s  {2} -j DROP".format(action,ip,mac),shell=True)): print "err"; exit(1)
        if(subprocess.call("ebtables -{0} FORWARD -p IPv4 --ip-src {1} -s ! {2} -j DROP".format(action,ip,mac),shell=True)): print "err"; exit(1)
        #..hai sa lasam dhcpul.. 
        #if(subprocess.call("ebtables -A INPUT -p IPv4 --ip-src ! {0} -s {1} -j DROP".format(ip,mac),shell=True)): print "err"; exit(1)
        #if(subprocess.call("ebtables -A INPUT -p IPv4 --ip-src {0} -s ! {1} -j DROP".format(ip,mac),shell=True)): print "err"; exit(1)
        # inter-vm IP traffic
        if(subprocess.call("ebtables -{0} FORWARD -i tap+ -o {1} -j DROP".format(action,tapname),shell=True)): print "err"; exit(1)
        # save
        if(subprocess.call("service ebtables save",shell=True)): print "err"; exit(1)
        
        
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
    (opts,args)=parser.parse_args()
    return opts
    
if __name__=="__main__":
    vms=VMStarter()
    args=vars(get_opts())
    
    if(args['vmid']):
        sys.stdout = open(args['vmid'], 'w')
    
    params={'exechost':"",'vncport':"",'tapname':""}
    vms.getHostParams(params)
    print "exechost=",params['exechost']
    print "vncport=",params['vncport']
    print "tapname=",params['tapname']
    
    discs=args['discs'].split(",")
    vms.startVM(discs, args['smp'], args['mem'], args['ip'], args['mac'], params['exechost'],params['vncport'],params['tapname'],
                 args['install'], args['cdrom'], args['isolate']) #to send out filename to kid process (only used if started without qsub)
    
    