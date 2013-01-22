import commands
#import pypureomapi
import datetime
import os
import subprocess
import sys
import db

dhcp_keyname = "omapi_key"
dhcp_secret = "KaekLmmyUj2RLvC8c1lj15AJ3gOIScUo/PjabCirckCw1lxSAj0hyIEASRaptg3gk33XHUrglPzQK1len7LhMQ=="
dhcp_server = "127.0.0.1"
dhcp_port = 9991

class VMCreator:
    def __init__(self): self.db=None


    #unused
    # returns dict with requested params
    def genVMparams(self,params):
        pset={}
#        for p in params:
#            if(p=='ip'):
#                pset['ip']=self.genIP()
#            elif(p=='mac'):
#                pset['mac']=self.genMACfromIP()
#            elif(p=='vnc'):
#                pset['vnc']=self.genVNCport()  # generate unused vnc port
        return pset
        
    
    
    def genUUID(self):
        return commands.getstatusoutput("uuidgen")[1]
        
    # storage is list of sizes [100,..] , base_storage is {'basepath1':size,..} or ['path1',..] 
    # returns dict {'path':size,..}
    def createDiscs(self,base_storage,discs_basename,location,storage,action):
        if(db.debug): print "..creating disc ",discs_basename," location ",location,' base storage ',base_storage
        new_storage={}
        path=os.path.join(location,discs_basename)
        
        if(action=='clone'): 
            i=0
            sorted_base_storage_keys=base_storage.keys()
            sorted_base_storage_keys.sort()
            for base_path in sorted_base_storage_keys:
                mpath=path+"_{0}.qcow2".format(i)
                cmd="qemu-img create -f qcow2 -b {0} {1} >/dev/null 2>&1".format(base_path,mpath)
                if(db.debug): print cmd
                i+=1
                new_storage[mpath]=base_storage[base_path]
                if(subprocess.call(cmd,shell=True)): print "err: creating disc (qemu-img with base)"; exit(1)
                if(not os.path.isfile(mpath)): print "err: cloned file is not there..funny"; exit(1)
        elif(action=='create'):
            # create new discs based on storage sizes
            i=0
            for size in storage:
                mpath=path+"_{0}.qcow2".format(i)
                cmd="qemu-img create -f qcow2 {0} {1}M >/dev/null 2>&1".format(mpath,size)
                if(db.debug): print cmd
                i+=1
                new_storage[mpath]=size
                if(subprocess.call(cmd,shell=True)): print "err: creating disc (qemu-img create)"; exit(1)
                if(not os.path.isfile(mpath)): print "err: created file is not there..funny"; exit(1)
        elif(action=='copy'):
            # this is when we have preexisting discs and we want to make them derivable( copy in templates location)
            # qemu-img info vs1.qcow2 |grep virtual |cut -d'(' -f2 |cut -d' ' -f1
            i=0
            for base_path in base_storage:
                mpath=path+"_{0}.qcow2".format(i)
                cmd="cp {0} {1} >/dev/null 2>&1 &".format(base_path,mpath)
                if(db.debug): print cmd
                i+=1
                if(subprocess.call(cmd,shell=True)): print "err"; exit(1)
                if(db.debug): print "checking size"
                if(not os.path.isfile(mpath)): print "err: created file is not there..funny"; exit(1)
                new_storage[mpath]=int(commands.getstatusoutput('qemu-img info {0} |grep virtual |cut -d"(" -f2 |cut -d" " -f1'.format(base_path))[1][:-6])
        elif(action=='rename'):
            # keep paths,but rename files
            i=0
            for base_path in base_storage:
                mpath=path+"_{0}.qcow2".format(i)
                cmd="mv {0} {1} >/dev/null 2>&1 ".format(base_path,mpath)
                if(db.debug): print cmd
                i+=1
                if(not os.path.isfile(mpath)): print "err: created file is not there..funny"; exit(1)
                new_storage[mpath]=int(commands.getstatusoutput('qemu-img info {0} |grep virtual |cut -d"(" -f2 |cut -d" " -f1'.format(base_path))[1][:-6])
                if(subprocess.call(cmd,shell=True)): print "err"; exit(1)
        
        return new_storage
    
    def ipstr_to_number(self,s):
        "Convert dotted IPv4 address to integer."
        return int(reduce(lambda a,b: a<<8 | b, map(int, s.split("."))))
 
    def number_to_ipstr(self,ip):
        "Convert 32-bit integer to dotted IPv4 address."
        return ".".join(map(lambda n: str(int(ip)>>n & 0xFF), [24,16,8,0]))
    
    def genFreeIP(self,vmgid):
        if(not self.db):
            print "creator: Please give the db"
            exit(1)
        # subnet for uid/gids , usedIPs from mappings #  or ask dhcp, maybe look in leases. #todo
        try:
            row=self.db.getOneRowWithCriteria('VMGroup','*','and',{'id':vmgid})
            ip_range=row['ip_range']  #"192.168.100.15-192.168.100.254"
            min_ip,max_ip=ip_range.split('-')
            min_ip=self.ipstr_to_number(min_ip)
            max_ip=self.ipstr_to_number(max_ip)
            # find used IPs (mappings) from this range #todo; for now, use 192.168.100
            rows=self.db.getRowsWithCriteria('Mapping','ip', '', {})
            if(db.debug): print rows
            #todo ..this is just for /24 and 192.168.100.0; use some conversion for the host bits, a number(for using the range)
            # this may be slow..if too many mappings exist
            
            nlist=range(min_ip,max_ip)
            for row in rows:
                for ip in row: #only one
                    #used_host_no=commands.getstatusoutput("cut -d'.' -f4 <<<{0}".format(ip))[1]  #host digits
                    ipno=self.ipstr_to_number(ip)
                    if ipno in nlist: 
                        nlist.remove(ipno)
            if(db.debug): print self.number_to_ipstr(min(nlist))
            return self.number_to_ipstr(min(nlist))
        except db.DatabaseException as e:  
            print e.err 
            exit(1)
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
    
    
    def addDHCPMapping(self,real_uid,vm_id,ip,mac,isolate,exechost,vncport,tapname):
        if(not self.db):
            print "creator: Please give the db"
            exit(1)
        #instruct dchp
        try:
            oma = pypureomapi.Omapi(dhcp_server, dhcp_port, dhcp_keyname, dhcp_secret, debug=False)
            oma.add_host(ip,mac) #gives an err if entry is already there
        except pypureomapi.OmapiError as err:
            print "OMAPI error: {0}".format(err)
        #insert in db
        # Mapping (user_g_id integer, vm_g_id integer, ip text, mac text, isolated integer,exechost text, vncport integer, date text)
        date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            row=(real_uid,vm_id,ip,mac,isolate,exechost,vncport,tapname,date)
            self.db.insert('Mapping', row)
        except db.DatabaseException as e:  
            print e.err
    
    def removeDHCPMapping(self,ip,mac):
        if(not self.db):
            print "creator: Please give the db"
            exit(1)
        try:
            self.db.deleteRowsWithCriteria('Mapping', 'and',{'ip':ip,'mac':mac})
        except db.DatabaseException as e:  
            print e.err
    
    