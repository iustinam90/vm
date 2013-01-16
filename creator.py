import commands
import os
import subprocess



class VMCreator:
    def __init__(self):pass
    
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
        print "..creating disc ",discs_basename," location ",location,' base storage ',base_storage
        new_storage={}
        path=os.path.join(location,discs_basename)
        
        if(action=='clone'): 
            i=0
            sorted_base_storage_keys=base_storage.keys()
            sorted_base_storage_keys.sort()
            for base_path in sorted_base_storage_keys:
                mpath=path+"_{0}.qcow2".format(i)
                cmd="qemu-img create -f qcow2 -b {0} {1} >/dev/null 2>&1".format(base_path,mpath)
                print cmd
                i+=1
                new_storage[mpath]=base_storage[base_path]
                if(subprocess.call(cmd,shell=True)): print "err"; exit(1)
                if(not os.path.isfile(mpath)): print "err: cloned file is not there..funny"; exit(1)
        elif(action=='create'):
            # create new discs based on storage sizes
            i=0
            for size in storage:
                mpath=path+"_{0}.qcow2".format(i)
                cmd="qemu-img create -f qcow2 {0} {1}M >/dev/null 2>&1".format(mpath,size)
                print cmd
                i+=1
                new_storage[mpath]=size
                if(subprocess.call(cmd,shell=True)): print "err"; exit(1)
                if(not os.path.isfile(mpath)): print "err: created file is not there..funny"; exit(1)
        elif(action=='copy'):
            # this is when we have preexisting discs and we want to make them derivable( copy in templates location)
            # qemu-img info vs1.qcow2 |grep virtual |cut -d'(' -f2 |cut -d' ' -f1
            i=0
            for base_path in base_storage:
                mpath=path+"_{0}.qcow2".format(i)
                cmd="cp {0} {1} >/dev/null 2>&1 &".format(base_path,mpath)
                print cmd
                i+=1
                if(subprocess.call(cmd,shell=True)): print "err"; exit(1)
                print "checking size"
                if(not os.path.isfile(mpath)): print "err: created file is not there..funny"; exit(1)
                new_storage[mpath]=int(commands.getstatusoutput('qemu-img info {0} |grep virtual |cut -d"(" -f2 |cut -d" " -f1'.format(base_path))[1][:-6])
        elif(action=='rename'):
            # keep paths,but rename files
            i=0
            for base_path in base_storage:
                mpath=path+"_{0}.qcow2".format(i)
                cmd="mv {0} {1} >/dev/null 2>&1 ".format(base_path,mpath)
                print cmd
                i+=1
                if(not os.path.isfile(mpath)): print "err: created file is not there..funny"; exit(1)
                new_storage[mpath]=int(commands.getstatusoutput('qemu-img info {0} |grep virtual |cut -d"(" -f2 |cut -d" " -f1'.format(base_path))[1][:-6])
                if(subprocess.call(cmd,shell=True)): print "err"; exit(1)
        
        return new_storage
    
    
    
    
    