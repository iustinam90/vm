import re
import db
import ast
import os
import subprocess
import authorizer
import creator
import starter
import socket
import sys
import time
#too.. to parse it twice

debug=1
id_range_limit=500
base_domain_location="/etc/libvirt/qemu/"
separator_len=150 #for printing entries in db

class VMController:
    def __init__(self,conf):
        self.conf=conf
        self.db=db.VMDatabase(self.conf)
        self.db_initialized=0
        self.authorizer=authorizer.Authorizer()
        
    def setRUID(self,real_uid):
        self.real_uid=real_uid
        
    def verify(self,what_to_check,items):
        if(not self.db_initialized):
            self._initDB()
        if(self.authorizer.isOk(what_to_check,items,self.db)):
            return True
        return False
    
    def _initDB(self):
        if(self.db_initialized):
            return
        try:
            #self.db=db.VMDatabase()
            self.db.init(self.conf['default_db'])
            self.db_initialized=1
        except db.DatabaseException as e:  
            print e.err
            exit(1) 
    ######################################## Initialize ##########################################
    
    # first init creates the tables
    def init(self,args):
        #check real_uid is admin. NOT good. we don't have the db yet. silly
#        if(not self.verify('isadmin',{'who':self.real_uid})):
#            return "Not allowed"
        #create db in dbpath
        try: 
            self.db.firstInit(args['dbpath'])
        except db.DatabaseException as e:
            return e.err
        return
    
    ######################################## User Group Ops ######################################
    
    def addUserGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        # UserGroup (id integer, name text, ip_range text)
        row=(args['user_group_id'],args['name']) 
        if(db.debug): print "row ",row
        try: 
            self.db.insert("UserGroup",row) 
        except db.DatabaseException as e:
            return e.err
        
    def delUserGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try: 
            for ugname in args['user_group_s']['names']:
                args['user_group_s']['ids'].append(self.db.getOneRowWithCriteria("UserGroup",'*','and',{'name':ugname})['id'])
            for ugid in args['user_group_s']['ids']:
                self.db.deleteRowsWithCriteria("UserGroup",'and',{'id':ugid}) 
                self.db.deleteRowsWithCriteria("Permission",'and',{'user_g_id':ugid}) 
                # update User table 
                rows=self.db.getRowsWithCriteriaLike('User','*', 'and', {"gid_list":ugid})
                for row in rows:
                    gid_list=ast.literal_eval(row['gid_list'])
                    gid_list=tuple(y for y in gid_list if y!=ugid) #remove deleted ug from list
                    self.db.update("User", {'gid_list':str(gid_list)}, 'and', {'id':row['id']})
        except db.DatabaseException as e:
            return e.err
        
    def modifyUserGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        #self._initDB()
        try: 
            ugid=self.db.getOneRowWithCriteria('UserGroup','*','or',{'id':args['user_group_s'],'name':args['user_group_s']})['id']
            self.db.update('UserGroup',{'name':args['name']},'and',{'id':ugid}) 
        except db.DatabaseException as e:
            return e.err
    
    def listUserGroups(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try: 
            rows=self.db.getRowsWithCriteria('UserGroup','*', '', {})
            # UserGroup (id integer, name text, //ip_range text)
            print '-'*separator_len
            print "%-6s %s"%('id','name')
            print '-'*separator_len
            for row in rows:
                print "%-6s %s"%(row['id'],row['name'])
        except db.DatabaseException as e:
            return e.err
        return
    
    ######################################## User Group Ops ######################################
    
    def addVMGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        # UserGroup (id integer, name text, ip_range text)
        row=(args['vm_group_id'],args['name'],args['ip_range']) 
        if(db.debug): print "row ",row
        try: 
            self.db.insert("VMGroup",row) 
        except db.DatabaseException as e:
            return e.err
        
    def delVMGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try: 
            for ugname in args['vm_group_s']['names']:
                args['vm_group_s']['ids'].append(self.db.getOneRowWithCriteria("VMGroup",'*','and',{'name':ugname})['id'])
            for ugid in args['vm_group_s']['ids']:
                self.db.deleteRowsWithCriteria("VMGroup",'and',{'id':ugid})
                self.db.deleteRowsWithCriteria("Permission",'and',{'vm_g_id':ugid}) 
                self.db.update("VM", {'vmgid':1}, 'and', {'vmgid':ugid}) #reset vmg to default
        except db.DatabaseException as e:
            return e.err
        
    def modifyVMGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        #self._initDB()
        try: 
            vmgid=self.db.getOneRowWithCriteria('VMGroup','*','or',{'id':args['vm_group_s'],'name':args['vm_group_s']})['id']
            if(args['name']):
                self.db.update('VMGroup',{'name':args['name']},'and',{'id':vmgid}) 
            if(args['ip_range']):
                self.db.update('VMGroup',{'ip_range':args['ip_range']},'and',{'id':vmgid}) 
        except db.DatabaseException as e:
            return e.err
    
    def listVMGroups(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try: 
            rows=self.db.getRowsWithCriteria('VMGroup','*', '', {})
            # UserGroup (id integer, name text, //ip_range text)
            print '-'*separator_len
            print "%-6s %-30s %s"%('id','name','ip_range')
            print '-'*separator_len
            for row in rows:
                print "%-6s %-30s %s"%(row['id'],row['name'],row['ip_range'])
        except db.DatabaseException as e:
            return e.err
        return
        
    ######################################## User Ops ############################################ 

    # admin only
    def addUser(self,args):#, uid, name, ip_range, mac_range, max_running_vm, max_storage, storage_folder, is_admin):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed" 
    
        #User (id, name, ip_range, gid_list,max_running_vm, max_storage,storage_folder,is_admin)
        # user_group_s is a mixture of group names and ids.. convert to ids only , eg ",31,admin, 3" >>(31, 0, 3)
        self._initDB() 
        gids=[1] # default insert in group 'all_users'
        if(args['user_group_s']):
            try: 
                for gn in args['user_group_s']['names']:
                    row=self.db.getOneRowWithCriteria('UserGroup','*', 'and', {'name':gn})
                    gids.append(row['id'])
                for gid in args['user_group_s']['ids']: 
                    row=self.db.getOneRowWithCriteria('UserGroup','*', 'and', {'id':gid}) #only check if exists
                    gids.append(gid)
            except db.DatabaseException as e:
                return e.err 

        if(debug): print "okgroups ",tuple(gids)
        #gids_tuple=tuple(int(v) for v in re.findall("[a-zA-Z_0-9]+",gids_text))
        #todo verify gids are in bd
        row=(args['user_id'],args['name'],args['ip_range'],str(tuple(gids)),args['maxrun'],args['maxstor'],args['storage_dir'])
        if(debug): print "row ",row
        try: 
            self.db.insert("User",row) 
        except db.DatabaseException as e:
            return e.err
        return 
    
    # admin only
    def listUsers(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        
        self._initDB()
        try: 
            rows=self.db.getRowsWithCriteria('User','*', '', {})
            #User (id, name, ip_range, gid_list,max_running_vm, max_storage,storage_folder)
            print '-'*separator_len
            print "%-5s %-22s %-18s %-15s %-16s %-13s %-100s"%('uid','name','ip_range','gid_list','max_running_vm','max_storage','storage_folder')
            print '-'*separator_len
            for row in rows:
#                print "%-5s %-22s %-18s %-10s %-16s %-13s %-100s"%(row['id'],row['name'],row['ip_range'],row['gid_list'],
#                                                                  row['max_running_vm'],row['max_storage'],row['storage_folder'],)
                print "%-5s %-22s %-18s %-15s %-16s %-13s %-100s"%tuple(row)
        except db.DatabaseException as e:
            return e.err
        return
    
    def delUser(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try: 
            for uname in args['user']['names']:
                args['user']['ids'].append(self.db.getOneRowWithCriteria("User",'*','and',{'name':uname})['id'])
            for uid in args['user']['ids']:
                self.db.deleteRowsWithCriteria("User",'and',{'id':uid}) 
                self.db.deleteRowsWithCriteria("Permission",'and',{'user_g_id':uid}) 
        except db.DatabaseException as e:
            return e.err

    # --umod --user _id/name [--name _ --ug +|-_,_ --maxrun _ --maxstor _ --stordir _ ]
    def modifyUser(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        
        modifications={}
        modifications['gid_list']=[]
        
        # previous gid list
        try:
            modifications['gid_list']=list(ast.literal_eval(self.db.getOneRowWithCriteria('User','*', 'or', {"id":args['user'],"name":args['user']})['gid_list']))
        except db.DatabaseException as e:
            return e.err 
        
        # add and remove specified user groups
        if(args['user_group_s']):
            allnames=args['user_group_s']['add']['names']+args['user_group_s']['del']['names']
            allids=args['user_group_s']['add']['ids']+args['user_group_s']['del']['ids']
            try: 
                for gn in allnames:
                    row=self.db.getOneRowWithCriteria('UserGroup','*', 'and', {'name':gn})
                    if(gn in args['user_group_s']['add']['names']):
                        if(not row['id'] in modifications['gid_list']):
                            modifications['gid_list'].append(row['id'])
                    if(gn in args['user_group_s']['del']['names']):
                        if(row['id'] in modifications['gid_list']):
                            modifications['gid_list'].remove(row['id'])
                for gid in allids:
                    row=self.db.getOneRowWithCriteria('UserGroup','*', 'and', {'id':gid}) #check if exists #would throw exc
                    if(gid in args['user_group_s']['add']['ids']):
                        if(not gid in modifications['gid_list']):
                            modifications['gid_list'].append(gid)
                    if(gid in args['user_group_s']['del']['ids']):
                        if(gid in modifications['gid_list']):
                            modifications['gid_list'].remove(gid)
            except db.DatabaseException as e:
                return e.err 
            
        modifications['gid_list']=str(tuple(modifications['gid_list']))
            
        if(args['name']):
            modifications['name']=args['name']
        if(args['maxrun']):
            modifications['max_running_vm']=args['maxrun']
        if(args['maxstor']):
            modifications['max_storage']=args['maxstor']
        if(args['storage_dir']):
            modifications['storage_folder']=args['storage_dir']
                
        try: 
            self.db.update("User", modifications, 'or', {"id":args['user'],"name":args['user']})
        except db.DatabaseException as e:
            return e.err
    ######################################## Permissions Ops ###################################### 

    
    def setPermissions(self,args):
        # user/ug  vm/vmg 
        # check real_uid is owner or admin
        self._initDB()
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try:                 
            #self.db.setPermissions(2,124,{'modify':0,'derive':0})
            if(args['user']):
                user_id=self.db.getOneRowWithCriteria('User','*','or',{'id':args['user'],'name':args['user']})['id']
            if(args['vm']):
                vm_id=self.db.getOneRowWithCriteria('VM','*','or',{'id':args['vm'],'name':args['vm']})['id']
            if(args['user_group_s']):
                user_id=self.db.getOneRowWithCriteria('UserGroup','*','or',{'id':args['user_group_s'],'name':args['user_group_s']})['id']
            if(args['vm_group_s']):
                vm_id=self.db.getOneRowWithCriteria('VMGroup','*','or',{'id':args['vm_group_s'],'name':args['vm_group_s']})['id']
            if(db.debug): print args['permset']
            self.db.setPermissions(user_id, vm_id, args['permset'])                                                  
        except db.DatabaseException as e:  
            return e.err 

    # --permlist [--user _id/name -ug _id/name --vm _uuid/name  -vmg _id/name]
    # user user_group_s vm vm_group
    # users can only see the perms that their uid/gids have
    def listPerms(self,args):
        self._initDB()
        try: 
            if(self.verify('isadmin',{'who':self.real_uid})):
                rows=self.db.getRowsWithCriteria('Permission','*', '', {})
            else:
                rows=self.db.getRowsWithCriteria('Permission','*', 'and', {'user_g_id':self.real_uid})
            # Permission (user_g_id integer, vm_g_id integer, run integer, modify integer, derive integer, force_isolated integer)
            print '-'*separator_len
            print "%-5s %-4s %-4s %-6s %-6s %-14s"%('uid','vmid','run','modify','derive','force_isolated')
            print '-'*separator_len
            for row in rows:
                print "%-5s %-4s %-4s %-6s %-6s %-14s"%tuple(row)
        except db.DatabaseException as e:
            return e.err
        return
        
    def deletePerms(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try: 
            if(args['user']):
                user_id=self.db.getOneRowWithCriteria('User','*','or',{'id':args['user'],'name':args['user']})['id']
            if(args['vm']):
                vm_id=self.db.getOneRowWithCriteria('VM','*','or',{'id':args['vm'],'name':args['vm']})['id']
            if(args['user_group_s']):
                user_id=self.db.getOneRowWithCriteria('UserGroup','*','or',{'id':args['user_group_s'],'name':args['user_group_s']})['id']
            if(args['vm_group_s']):
                vm_id=self.db.getOneRowWithCriteria('VMGroup','*','or',{'id':args['vm_group_s'],'name':args['vm_group_s']})['id']
            
            self.db.deleteRowsWithCriteria("Permission",'and',{'user_g_id':user_id,'vm_g_id':vm_id}) 
        except db.DatabaseException as e:
            return e.err
        
    ######################################## VMs Ops ############################################## 
    
#    def setOwner(self, vm, user):
#        # getOneByNameOrId("User",user),scot uid, idem pt vm scot uuid
#        # get("VM",uuid,"owner_uid") #scot owner vechi
#        # setPermissions(uid,uuid,0,0,0,0)  # ii sterg permisiuni la cel vechi
#        # update("VM",uuid,"owner_uid",uid) #in tabela VM , la linia lui uuid schimb owner_id in uid
#        # setPermissions(uid,uuid,1,1,1,0)  #
#        pass
#
    # update storage sizes for all discs that belong to a user's vms
    def _updateStorage(self):
        pass
        
    # mac ip vnc unused 
    def addVM(self,args):#,real_uid,name,mac,ip,storage,derivable=False,base_uuid=0,desc=""):
        
        self._initDB() 

        ################### check if vm name already exists        
        try: 
            rows=self.db.getRowsWithCriteria('VM','*','and',{'name':args['name']})
            if(len(rows)>0):
                raise db.DatabaseException("VM name taken")
        except db.DatabaseException as e:  
            return e.err
        ################### check storage limit
        if(not args['storage']):
            args['storage']=[]
        new_storage=sum(args['storage'])  #args['storage'] is like [ '100','5000']
        self._updateStorage()
        # get max_storage, storage_folder from User; calculate all_storage from all his vms
        #User (id, name, ip_range, gid_list,max_running_vm, max_storage,storage_folder)
        try: 
            row=self.db.getOneRowWithCriteria('User','*', 'and', {'id':self.real_uid})
            max_storage=row['max_storage']
            storage_folder=row['storage_folder']
            gid_list=ast.literal_eval(row['gid_list'])
            # calculate all storage
            all_storage=0
            rows=self.db.getRowsWithCriteria('VM','*', 'and', {'owner_id':self.real_uid})
            for row in rows:
                stor_dict=ast.literal_eval(row['storage'])
                disc_sizes=sum(stor_dict[key]['size'] for key in stor_dict.keys())   #list of sizes
                all_storage+=disc_sizes
        except db.DatabaseException as e:  
            return e.err 
        
        if(new_storage+all_storage>max_storage):
            return "Cannot create new vm: your maximum storage is {0}".format(max_storage)
        
        ################### check derive permission
        # Permission (user_g_id integer, vm_g_id integer, run integer, modify integer, derive integer, force_isolated integer)
        base_id=0
        if(args['base']):
            try: 
                # get some  IDs
                rows=self.db.getRowsWithCriteria('VM','*','or',{'id':args['base'],'name':args['base']})
                if(len(rows)<1):
                    raise db.DatabaseException("base VM not found")
                base_id=int(rows[0]['id'])
                base_storage=ast.literal_eval(rows[0]['storage'])
                vmgid=ast.literal_eval(rows[0]['vmgid'])
            except db.DatabaseException as e:  
                return e.err    
            if(not self.verify('derive',{'who':(self.real_uid,)+gid_list,'what':(base_id,vmgid)})):
                return "You don't have permission to derive this vm"
        
        vmc=creator.VMCreator(self.conf)
        # create discs in user home., if derivable create it in base_disc_location, base_domain_location, if from base clone discs
        discs_basename=str(self.real_uid)+"_"+args['name']

        if(args['derivable'] and not args['use_discs']):
            if(debug): print "call create template"
            storage=vmc.createDiscs("", discs_basename, self.conf['base_disc_location'],args['storage'],'create',self.real_uid)
        elif(args['base']):
            if(debug): print "call clone"
            storage=vmc.createDiscs(base_storage, discs_basename, storage_folder,{},'clone',self.real_uid)
        elif(args['derivable'] and args['use_discs']):
            if(debug): print "call keep template(copy in dir if not there)"
            storage=vmc.createDiscs(args['use_discs'], discs_basename, self.conf['base_disc_location'],{},'keep_base',self.real_uid) #copy to templates dir
        elif(not args['derivable'] and args['use_discs']):
            if(debug): print "call keep"
            storage=vmc.createDiscs(args['use_discs'], discs_basename, storage_folder,{},'keep',self.real_uid) #
        else:
            if(debug): print "call create"
            storage=vmc.createDiscs("", discs_basename, storage_folder,args['storage'],'create',self.real_uid)
        
        # insert in db
        if(not args['base']): # if it has --base, then inhert the group, else insert in the default vmgroup
            vmgid=1 # default add to group all_vms
            if(args['vm_group_s']):
                if(args['vm_group_s']['ids']):
                    vmgid=args['vm_group_s']['ids']
                elif(args['vm_group_s']['names']):
                    try: 
                        vmgid=self.db.getOneRowWithCriteria('VMGroup','*', 'and', {'name':args['vm_group_s']['names'][0]})['id']
                    except db.DatabaseException as e:
                        return e.err      

        # VM (id, name, owner_id, vmgid, storage,derivable, base_uuid,mac,ip,vnc,desc,started)
        try:
            new_id=self.db.genNextId('VM','>')
            row=(new_id,args['name'],self.real_uid,str(vmgid),str(storage),args['derivable'],base_id,"","","",args['desc'],0)
            if(db.debug): print row
            self.db.insert('VM', row) # throws exc if name/id dupl
            self.db.setPermissions(self.real_uid,new_id,{'run':1,'modify':1,'derive':args['derivable'],'force_isolated':0})
        except db.DatabaseException as e:  
            return e.err 
        
        

    def startVM(self,args):pass
    
    # --vmrun --vm _id/name [--mem _ --smp _ --install --cdrom _ --isolate] 
    def runVM(self,args):#
        # install nu mere fara cdrom 
        self._initDB()
        try: 
            row=self.db.getOneRowWithCriteria('VM','*', 'or', {'id':args['vm'],'name':args['vm']})
            vm_id=int(row['id'])
            vmgid=int(row['vmgid'])
            discs=ast.literal_eval(row['storage'])
            
            row=self.db.getOneRowWithCriteria('User','*', 'and', {'id':self.real_uid})
            gid_list=ast.literal_eval(row['gid_list'])
            #authorize
            if(not self.verify('run',{'who':(self.real_uid,)+gid_list,'what':(vm_id,vmgid)})):
                return "You don't have permission to run this vm"
            if(not args['isolate']):
                if(self.verify('force_isolated',{'who':(self.real_uid,)+gid_list,'what':(vm_id,vmgid)})):
                    return "You don't have permission to run this vm unisolated"
            #vrfy vm is already running
            rows=self.db.getRowsWithCriteria('Mapping','*','and',{'vm_g_id':vm_id})
            if(len(rows)>=1):
                raise db.DatabaseException("Your vm is already running")
        except db.DatabaseException as e:  
            return e.err 

        #vms=starter.VMStarter()
        vmc=creator.VMCreator(self.conf)
        vmc.db=self.db
        
        disc_paths=[discs[e]['path'] for e in discs.keys()]
        for disc in disc_paths:
            if(not os.path.exists(disc)):
                return "err: Disc file does not exist: {0}".format(disc)
        ip=vmc.genFreeIP(vmgid)
        mac=vmc.genMACfromIP(ip)
        
#        vms.getHostParams(self.real_uid, vm_id, discs, args['mem'], args['smp'], args['install'], args['cdrom'], args['isolate'])
        
        # direct call
#        params={'exechost':"",'vncport':"",'tapname':""}
#        vms.getHostParams(params)
#        vms.startVM(disc_paths, args['smp'], args['mem'], ip, mac, params['exechost'],params['vncport'],params['tapname'], args['install'], args['cdrom'], args['isolate'])
        
        #create process
        if(db.debug): print disc_paths
        if(not os.path.isdir(self.conf['vmoutdir'])):  #todo configurable,move in init
            os.mkdir(self.conf['vmoutdir'])
            os.chown(self.conf['vmoutdir'], int(self.real_uid), -1)
        vmoutfile=os.path.join(self.conf['vmoutdir'],str(vm_id)) 

        #used for runing as a process , with --vmid
        #cmd="python starter.py --discs {0} --smp {1} --mem {2} --ip {3} --mac {4} --vmid {5} ".format(','.join(disc_paths),args['smp'],args['mem'],ip,mac,vmoutfile)
        
        
        cmd="sudo {0} --discs {1} --smp {2} --mem {3} --ip {4} --mac {5}".format(self.conf['starter_path'],','.join(disc_paths),args['smp'],args['mem'],ip,mac)
        cmd_watcher="python {0} --uid {1} --vmid {2} --ip {3} --mac {4} --file {5} ".format(self.conf['watcher_path'],self.real_uid,vm_id,ip,mac,vmoutfile)
        
        if(args['isolate']):
            cmd=cmd+" --isolate "
            cmd_watcher=cmd_watcher+" --isolate "
        if(args['install']):
            cmd=cmd+" --install --cdrom {0} ".format(args['cdrom'])
            
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.conf['server_ip'], 0)) #ask for a free port  
        port=s.getsockname()[1] #get the port
        cmd+=" --srvhost {0} --srvport {1} ".format(self.conf['server_ip'],port)
        if(debug): print cmd
        
        cmd_watcher+=" &"
        
        #cmd_job="echo '{0}' |qsub -S /usr/bin/python -o {1} ".format(cmd,vmoutfile)
        job_file=vmoutfile+".sh"
        job_kvm="#!/bin/bash \n {0} \n".format(cmd)
        job_cmd="qsub -N kvm{0} -o {1} -cwd -l h=quad-wn14 {2}".format(vm_id,vmoutfile,job_file)
        m=open(job_file,"w")
        m.write(job_kvm)
        m.close()
        if(debug): print "job_file",job_file,job_kvm,"\n",job_cmd,"\n",cmd_watcher
        #as a process
        #if(subprocess.call(cmd,shell=True)): print "err: calling starter"; exit(1)
        #as a job with command in file
        
        vmc.addDHCPMapping(self.real_uid,vm_id,ip,mac,args['isolate'],"","","")

        child_pid = os.fork() 
        if child_pid == 0:  
            sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) #unbuffer stdout     
            s.listen(1)
            conn, addr = s.accept()
            if(debug): print 'Connected by', addr
            while 1:
                data = conn.recv(1024)
                if not data: 
                    if(debug): print "No more data, delete mapping" 
                    vmc.removeDHCPMapping(ip,mac)
                    os.unlink(vmoutfile)
                    break
                msg=eval(data) #could be {'exechost':"",'vncport':"",'tapname':""} or {'died':1}
                if('exechost' in msg):
                    print "Your vm is accessible via host {0} , display {1}".format(msg['exechost'],int(msg['vncport'])%100)
                    #update mapping
                    vmc.updateDHCPMapping(self.real_uid,vm_id,msg['exechost'],int(msg['vncport']))
                if('died' in msg):
                    if(debug): print "Process died, delete mapping"
                    vmc.removeDHCPMapping(ip,mac)
                    os.unlink(vmoutfile)
            conn.close()
        elif child_pid==-1:
            print "error fork"
        else:
            time.sleep(2) #wait for parent to create a socket
            os.setuid(int(self.real_uid))
            if(subprocess.call(job_cmd,shell=True)): print "err: calling starter job"; exit(1)
            
        
            
#        if(subprocess.call(cmd_watcher,shell=True)): print "err: calling watcher"; exit(1)
        
    
        
    
    def delVM(self,args):
        self._initDB()
        try: 
            for vmname in args['vm']['names']:
                args['vm']['ids'].append(self.db.getOneRowWithCriteria('VM','*','and',{'name':vmname})['id'])
            for vmid in args['vm']['ids']:
                if(not (self.verify('isowner',{'who':self.real_uid,'what':vmid}) or self.verify('isadmin',{'who':self.real_uid}))):
                    return "Not allowed"
                else:
                    self.db.deleteRowsWithCriteria("VM",'and',{'id':vmid})  
                    self.db.deleteRowsWithCriteria("Permission",'and',{'vm_g_id':vmid})  
        except db.DatabaseException as e:
            return e.err

    def listVM(self,args):
        self._initDB()
        try:
            if(self.verify('isadmin',{'who':self.real_uid})):
                rows=self.db.getRowsWithCriteria('VM','*', '', {})
            else:
                # todo user can see vms that he has perm on too..i think
                rows=self.db.getRowsWithCriteria('VM','*', 'and', {'owner_id':self.real_uid})
            
            #VM (id, name, owner_id, vmg, storage,derivable, base_id,mac,ip,vnc,desc,started)
            print '-'*separator_len
            print "%-5s %-22s %-10s %-10s %-11s %-9s %-30s %s"%('vmid','name','owner_id','vm_group',
                                                                      'derivable','base_id','desc','storage')
            print '-'*separator_len
            for row in rows:
                stor=ast.literal_eval(row['storage'])
                print "%-5s %-22s %-10s %-10s %-11s %-9s %-30s %s"%(row['id'],row['name'],row['owner_id'],row['vmgid'],
                                                                                        row['derivable'],row['base_id'],row['desc'],
                                                                                        [[stor[e]['path'],stor[e]['size']] for e in stor.keys()])
        except db.DatabaseException as e:
            return e.err
        return
    
    # --vmmod --vm _id/name [--name _ --owner _ --derivable --noderivable]
    def modifyVM(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        modifications={}

        if(args['name']):
            modifications['name']=args['name']
        if(args['owner']):
            try:
                modifications['owner_id']=self.db.getOneRowWithCriteria('User','*','or',{'id':args['owner'],'name':args['owner']})['id']
            except db.DatabaseException as e:
                return e.err   
        if(args['derivable']):
            modifications['derivable']=1
        if(args['noderivable']):
            modifications['derivable']=0
                
        try: 
            row=self.db.getOneRowWithCriteria('VM','*','or',{'id':args['vm'],'name':args['vm']})
            vmid=row['id']
            old_owner=row['owner_id']
            
            self.db.update("VM", modifications, 'and', {"id":vmid})
            
            derivable=row['derivable']
            if(modifications.get('derivable')): #if user wants to modify
                derivable=modifications['derivable'] #use below
                self.db.setPermissions(old_owner,vmid,{'derive':derivable})
            if(modifications.get('owner_id')):
                # delete old owner permission
                self.db.deleteRowsWithCriteria("Permission",'and',{'user_g_id':old_owner,'vm_g_id':vmid}) 
                # add new owner permission
                self.db.setPermissions(modifications['owner_id'], vmid,{'run':1,'modify':1,'derive':derivable,'force_isolated':0} )
                #run/modify/forceisolate permissions are not kept
        except db.DatabaseException as e:
            return e.err

    ######################################## Mapping Ops ############################################## 

    def listMapping(self,args):
        self._initDB()
        try:
            if(self.verify('isadmin',{'who':self.real_uid})):
                rows=self.db.getRowsWithCriteria('Mapping','*', '', {})
            else:
                rows=self.db.getRowsWithCriteria('Mapping','*', 'and', {'user_g_id':self.real_uid}) 
            #Mapping (user_g_id integer, vm_g_id integer, ip text, mac text, isolated integer,exechost text, vncport integer,tap text, date text)
            print '-'*separator_len
            print "%-6s %-5s %-16s %-18s %-9s %-23s %-5s %-5s %-21s"%('uid','vmid','ip','mac','isolated','exechost','vnc','tap','date')
            print '-'*separator_len
            for row in rows:
                print "%-6s %-5s %-16s %-18s %-9s %-23s %-5s %-5s %-21s"%tuple(row)
        except db.DatabaseException as e:
            return e.err
        return
    
    def delMapping(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try: 
            user_id=self.db.getOneRowWithCriteria('User','*','or',{'id':args['user'],'name':args['user']})['id']
            vm_id=self.db.getOneRowWithCriteria('VM','*','or',{'id':args['vm'],'name':args['vm']})['id']
            self.db.deleteRowsWithCriteria("Mapping",'and',{'user_g_id':user_id,'vm_g_id':vm_id}) 
        except db.DatabaseException as e:
            return e.err


    def execute(self,real_uid,action,args):
#        "user_group_add user_group_del user_group_mod list_user_groups"+\
#                "vm_group_add vm_group_del vm_group_mod list_vm_groups"+\
#                "user_add user_del user_mod user_list "+\
#                "vm_add vm_del vm_mod vm_run vm_list "+\
#                "permset permlist maplist"
        e=""
        if(action=='init'):
            e=self.init(args)
        elif(action=='user_group_add'):
            e=self.addUserGroup(args) 
        elif(action=='user_group_del'):
            e=self.delUserGroup(args),
        elif(action=='user_group_mod'):
            e=self.modifyUserGroup(args)
        elif(action=='list_user_groups'):
            e=self.listUserGroups(args)
            
        elif(action=='vm_group_add'):
            e=self.addVMGroup(args) 
        elif(action=='vm_group_del'):
            e=self.delVMGroup(args),
        elif(action=='vm_group_mod'):
            e=self.modifyVMGroup(args)
        elif(action=='list_vm_groups'):
            e=self.listVMGroups(args)
            
        elif(action=='user_add'):
            e=self.addUser(args)
        elif(action=='user_list'):
            e=self.listUsers(args)
        elif(action=='user_del'):
            e=self.delUser(args)
        elif(action=='user_mod'):
            e=self.modifyUser(args)
            
        elif(action=='vm_add'):
            e=self.addVM(args)
        elif(action=='vm_run'):
            e=self.runVM(args)
        elif(action=='vm_del'):
            e=self.delVM(args)
        elif(action=='vm_list'):
            e=self.listVM(args)
        elif(action=='vm_mod'):
            e=self.modifyVM(args)
         
        elif(action=='permset'):
            e=self.setPermissions(args)   
        elif(action=='permlist'):
            e=self.listPerms(args)
        elif(action=='permdel'):
            e=self.deletePerms(args)
                
        elif(action=='maplist'):
            e=self.listMapping(args)
        elif(action=='mapdel'):
            e=self.delMapping(args)
        
        return e
################################################################################# test area
    
def main():
    pass
    

if __name__ == "__main__": main()
