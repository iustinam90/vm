import pypureomapi
import commands
import datetime
import subprocess
import os
import time
import db

br_name="vbr0"

dhcp_keyname = "omapi_key"
dhcp_secret = "KaekLmmyUj2RLvC8c1lj15AJ3gOIScUo/PjabCirckCw1lxSAj0hyIEASRaptg3gk33XHUrglPzQK1len7LhMQ=="
dhcp_server = "127.0.0.1"
dhcp_port = 9991



class VMStarter:
    def __init__(self):pass
        
    # --vmrun --vm _id/name [--mem _ --smp _ --install --cdrom _ --isolate] 
    # hd is a list of paths (hda->hdd)
    
    def getParamsForKVM(self,real_uid,vm_id,discs,mem,smp,install,cdrom,isolate):
        # db
        self._initDB()
        disc_paths=discs.keys() 
        disc_paths.sort()       #put them in order : _0.qcow2,_1.qcow2 etc
        ip=self.genFreeIP(real_uid)
        mac=self.genMACfromIP(ip)
        exechost=self.getExechost()
        vncport=self.genVNCport()
        tapname=self.genTap()
        
        self.addDHCPMapping(real_uid,vm_id,ip,mac,isolate,exechost,vncport,tapname)
        self.connectToNetwork(tapname)
        if(isolate): 
            self.isolateVM(ip,mac,tapname) # mac spoof, inter vm traffic
        self.startVM(disc_paths,smp,mem,ip,mac,exechost,vncport,tapname,install,cdrom)
    
    def startVM(self,disc_paths,smp,mem,ip,mac,exechost,vncport,tapname,install,cdrom):
        # create command
        optional_install=""
        if(cdrom): optional_install=" -boot d -cdrom {0} ".format(cdrom)
        hdds=""
        if(len(disc_paths)>=1): hdds+=" -hda {0} ".format(disc_paths[0])
        if(len(disc_paths)>=2): hdds+=" -hdb {0} ".format(disc_paths[1])
        if(len(disc_paths)>=3): hdds+=" -hdc {0} ".format(disc_paths[2])
        if(len(disc_paths)>=4): hdds+=" -hdd {0} ".format(disc_paths[3])
        
        #/usr/libexec/qemu-kvm [ -boot d -cdrom ..iso ] -hda vm1.qcow2 -vnc :10 -m 1G -smp 1 -net nic,macaddr=DE:AD:BE:EF:CF:87 -net tap,ifname=tap0,script=no,downscript=no &
        cmd="/usr/libexec/qemu-kvm {0} -vnc :{1} -m {2} -smp {3} -net nic,macaddr={4} -net tap,ifname={5},script=no,downscript=no \
        {6}  &".format(hdds,vncport%100,mem,smp,mac,tapname,optional_install)
        print cmd
        if(subprocess.call(cmd,shell=True)): print "err";exit(1)
        # todo check if vm is actually running
        print "Your vm is accessible via host {0} vnc port {1}, display {2}".format(exechost,vncport,vncport%100)
        
        #fork to watch this process 
        child_pid = os.fork()
        if child_pid == 0:
            print "Child Process: PID# %s" % os.getpid()
            vm_running=1
            while(vm_running):
                time.sleep(1)
                if(not commands.getstatusoutput("ps aux |grep {0} |grep -v grep ".format(disc_paths[0]))[1]):
                    print "vm process died"
                    vm_running=0
                    self.removeDHCPMapping(ip,mac)
                    self.removeTap(tapname)
                    self.alterEbtables("D",ip,mac,tapname)
                
        else:
            print "Parent terminating: PID# %s" % os.getpid()
    
    def _initDB(self):
        try:
            self.db=db.VMDatabase()
            self.db.init(db.defaultDb)
        except db.DatabaseException as e:  
            print e.err 
    
    def getDiscPaths(self,vm_id):
        discs=[]

        return discs
    
    def genFreeIP(self,real_uid):
        # subnet for uid/gids , usedIPs from mappings #  or ask dhcp, maybe look in leases. #todo
        try:
            #todo change , ; for now, use the range 192.168.100.0/24
            #rows=self.db.getRowsWithCriteria('UserGroup','*','and',{'id':1})
            #ip_range=rows[0]['ip_range']  #10.42.0.0/16
            # find used IPs (mappings) from this range #todo; for now, use 192.168.100
            rows=self.db.getRowsWithCriteria('Mapping','ip', '', {})
            print rows
            #todo ..this is just for /24 and 192.168.100.0; use some conversion for the host bits, a number(for using the range)
            # this may be slow..if too many mappings exist
            first_host_digits=15 
            list=range(first_host_digits,255)
            for row in rows:
                for ip in row: #only one
                    used_host_no=commands.getstatusoutput("cut -d'.' -f4 <<<{0}".format(ip))[1]  #host digits
                    if int(used_host_no) in list: 
                        list.remove(int(used_host_no))
            return "192.168.100."+str(min(list))
        except db.DatabaseException as e:  
            print e.err 
        pass
    
    def genMACfromIP(self,ip):
        # okidoki..now..what, convert last 16 bits to hex :D        
        ip_part3=ip.split('.')[2]
        ip_part4=ip.split('.')[3]
        mac_part5=hex(int(ip_part3)).split('x')[1]  
        mac_part6=hex(int(ip_part4)).split('x')[1]  
        if(len(mac_part5)==1): mac_part5="0"+mac_part5
        if(len(mac_part6)==1): mac_part6="0"+mac_part6
        mac="de:af:de:af:{0}:{1}".format(mac_part5,mac_part6)
        return mac
    
    def getExechost(self):
        return commands.getstatusoutput("hostname")[1]
    
    #unused exechost
    def addDHCPMapping(self,real_uid,vm_id,ip,mac,isolate,exechost,vncport,tapname):
        #instruct dchp
        try:
            oma = pypureomapi.Omapi(dhcp_server, dhcp_port, dhcp_keyname, dhcp_secret, debug=False)
            oma.add_host(ip,mac)
        except pypureomapi.OmapiError as err:
            print "OMAPI error: {0}".format(err)
        #insert in db
        # Mapping (user_g_id integer, vm_g_id integer, ip text, mac text, isolated integer,exechost text, vncport integer, date text)
        date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:S")
        try:
            row=(real_uid,vm_id,ip,mac,isolate,exechost,vncport,tapname,date)
            print row
            self.db.insert('Mapping', row)
        except db.DatabaseException as e:  
            print e.err
    
    def removeDHCPMapping(self,ip,mac):
        try:
            self.db.deleteRowsWithCriteria('Mapping', 'and',{'ip':ip,'mac':mac})
        except db.DatabaseException as e:  
            print e.err
    
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
    