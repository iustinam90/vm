import commands
import pypureomapi
import datetime
import os
import subprocess
import sys
import db

debug=0
#dhcp_keyname = "omapi_key"
#dhcp_secret = "KaekLmmyUj2RLvC8c1lj15AJ3gOIScUo/PjabCirckCw1lxSAj0hyIEASRaptg3gk33XHUrglPzQK1len7LhMQ=="
#dhcp_server = "127.0.0.1"
#dhcp_port = 9991
#chown_gid=9007

class VMCreator:
    def __init__(self,conf): 
        self.db=None
        self.conf=conf


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
    def createDiscs(self,base_storage,discs_basename,location,storage,action,real_uid):
        if(db.debug): print "..creating disc ",discs_basename," location ",location,' base storage ',base_storage
        new_storage={}
        path=os.path.join(location,discs_basename)
        
        if(action=='clone'): 
            for i in base_storage.keys():
                new_storage[i]={}
                new_storage[i]['path']=path+"_{0}.qcow2".format(i)
                cmd="qemu-img create -f qcow2 -b {0} {1}".format(base_storage[i]['path'],new_storage[i]['path'])
                if(debug): print cmd
#                new_storage[mpath]=base_storage[base_path]
                new_storage[i]['size']=base_storage[i]['size']
                out=commands.getstatusoutput(cmd)
                if(out[0]): print "err: creating disc (qemu-img with base): ",out[1]; exit(1)
                #if(subprocess.call(cmd,shell=True)): print "err: creating disc (qemu-img with base)"; exit(1)
                if(not os.path.isfile(new_storage[i]['path'])): print "err: cloned file is not there..funny"; exit(1)
                os.chown(new_storage[i]['path'], int(real_uid), -1)
        elif(action=='create'):
            # create new discs based on storage sizes
            i=0
            for size in storage:
                mpath=path+"_{0}.qcow2".format(i)
                cmd="qemu-img create -f qcow2 {0} {1}M ".format(mpath,size) #>/dev/null 2>&1
                if(debug): print cmd
                new_storage[i]={}
                new_storage[i]['path']=mpath
                new_storage[i]['size']=size
                if(subprocess.call(cmd,shell=True)): print "err: creating disc (qemu-img create)"; exit(1)
                if(not os.path.isfile(mpath)): print "err: created file is not there..funny"; exit(1)
                os.chown(new_storage[i]['path'], int(real_uid), -1)
                i+=1
        elif(action=='keep_base'):
            # this is when we have preexisting discs and we want to make them derivable
            # copy discs in templates location if not already there, RENAME to our convention
            # qemu-img info vs1.qcow2 |grep virtual |cut -d'(' -f2 |cut -d' ' -f1
            i=0
            for base_path in base_storage:
                mpath=path+"_{0}.qcow2".format(i)
                if(os.path.exists(mpath) and os.path.samefile(base_path,mpath)):
                    if(debug): print "same file: ",base_path,mpath
                else:
                    cmd="cp {0} {1} ".format(base_path,mpath)
                    if(debug): print cmd
                    if(subprocess.call(cmd,shell=True)): print "err"; exit(1)     
                if(db.debug): print "checking size"
                if(not os.path.isfile(mpath)): print "err: created file is not there..funny"; exit(1)
                
#                mpath=base_path #todo remove
                new_storage[i]={}
                new_storage[i]['path']=mpath
                new_storage[i]['size']=int(commands.getstatusoutput('qemu-img info {0} |grep virtual |cut -d"(" -f2 |cut -d" " -f1'.format(mpath))[1][:-6])
                os.chown(new_storage[i]['path'], int(real_uid), -1)
                i+=1
        elif(action=='keep'):
            #  renames, keeps paths
            i=0
            for base_path in base_storage:
                #path= os.path.abspath("_".join(base_path.split('_')[:-1]))
#                mpath=os.path.abspath(base_path+"_{0}.qcow2".format(i))
#                if(debug): print "renaming ",base_path,mpath
#                if(os.path.exists(mpath) and os.path.samefile(base_path,mpath)):
#                    if(debug): print "same file: ",base_path,mpath
#                else:
#                    cmd="mv {0} {1} ".format(base_path,mpath)
#                    if(debug): print cmd
#                    if(subprocess.call(cmd,shell=True)): print "err: movin file"; exit(1)
                if(not os.path.isfile(base_path)): print "err: the file is not there..funny"; exit(1)
                new_storage[i]={}
                new_storage[i]['path']=os.path.abspath(base_path)
                new_storage[i]['size']=int(commands.getstatusoutput('qemu-img info {0} |grep virtual |cut -d"(" -f2 |cut -d" " -f1'.format(base_path))[1][:-6])
                os.chown(new_storage[i]['path'], int(real_uid), -1)
                i+=1
                
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
        # subnet for uid/gids , usedIPs from mappings #  or ask dhcp, maybe look in leases. 
        try:
            row=self.db.getOneRowWithCriteria('VMGroup','*','and',{'id':vmgid})
            ip_range=row['ip_range']  #"192.168.100.15-192.168.100.254"
            min_ip,max_ip=ip_range.split('-')
            min_ip=self.ipstr_to_number(min_ip)
            max_ip=self.ipstr_to_number(max_ip)
            # find used IPs (mappings) from this range 
            rows=self.db.getRowsWithCriteria('Mapping','ip', '', {})
            if(db.debug): print rows
            
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
            oma = pypureomapi.Omapi(self.conf['dhcp_server'],int(self.conf['dhcp_port']), self.conf['dhcp_keyname'], self.conf['dhcp_secret'], debug=False)
            oma.add_host(ip,mac) #gives an err if entry is already there
        except pypureomapi.OmapiError as err:
            if(not "add failed" in str(err)):
                print "OMAPI error: {0}".format(err)
        #insert in db
        # Mapping (user_g_id integer, vm_g_id integer, ip text, mac text, isolated integer,exechost text, vncport integer, date text)
        date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            row=(real_uid,vm_id,ip,mac,isolate,exechost,vncport,tapname,date)
            self.db.insert('Mapping', row)
        except db.DatabaseException as e:  
            print e.err
            
    def updateDHCPMapping(self,ruid,vm_id,exechost,vnc):
        if(not self.db):
            print "creator: Please give the db"
            exit(1)
        try:
            self.db.update2('Mapping', ruid, vm_id,{'exechost':exechost,'vncport':vnc})
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
    
    