from optparse import OptionParser
import time
import sys
import os
import commands
import ConfigParser
import creator
import db

debug=1
conf_file="/opt/ncit-cloud/vm.ini"
# loop: get vnc, host and tap, insert mapping
# loop: looks in process outp file for the message "died" and deletes mapping
# deletes mapping (ip,mac) 

class VMWatcher:
    def __init__(self):pass
        
#    def initDB(self):
#        try:
#            self.db=db.VMDatabase(self.conf['default_db'])
#            self.db.init(self.conf['default_db'])
#        except db.DatabaseException as e:  
#            print e.err
#            exit(1) 
#          
#    def getConf(self):
#        config = ConfigParser.ConfigParser()
#        config.read(conf_file)
#        conf=config._sections['conf']
#        needed_opts="default_db default_ip_range default_admin_uid default_admin_home dhcp_keyname dhcp_secret dhcp_server dhcp_port id_range_limit base_domain_location base_disc_location vmoutdir separator_len"
#        for opt in needed_opts.split(' '):
#            if(not opt in conf.keys()): print "Missing option: ",opt; exit(1)
#        self.conf=conf
          
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
            #if(debug): sys.stdout.write("w")
            #check if file was modified recently 
            if(not os.path.exists(file)):
                vm_running=0
            elif(time.time()-os.path.getmtime(file)>5):
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
    vmw.getConf()
    vmw.initDB()
    vmc=creator.VMCreator(vmw.conf)
    vmc.db=vmw.db #give the initialized db ref to creator.
    params={'exechost':"",'vncport':"",'tapname':""}
    vmw.watchHostParams(args['file'],params) #wait for host params (tap,vnc,hostname) 
    if(debug): print "watcher",params
    vmc.addDHCPMapping(args['uid'],args['vmid'],args['ip'],args['mac'],args['isolate'],params['exechost'],params['vncport'],params['tapname'])
    vmw.watchVMdies(args['file']) #todo file
    vmc.removeDHCPMapping(args['ip'],args['mac'])
    