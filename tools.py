import re
import db
import ast
import authorizer
import creator
import starter
#too.. to parse it twice

id_range_limit=500

def_db_path="vm.db"
#base_disc_location="/var/lib/libvirt/images/"
base_domain_location="/etc/libvirt/qemu/"
base_disc_location="/tmp"
separator_len=150 #for printing entries in db

class VMTools:
    def __init__(self,real_uid):
        self.real_uid=real_uid
        self.db=db.VMDatabase()
        self.db_initialized=0
        self.authorizer=authorizer.Authorizer()
        
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
            self.db.init(db.defaultDb)
            self.db_initialized=1
        except db.DatabaseException as e:  
            print e.err 
    ######################################## Initialize ##########################################
    
    def init(self,args):
        #check real_uid is admin. NOT good. we don't have the db yet. silly
#        if(not self.verify('isadmin',{'who':self.real_uid})):
#            return "Not allowed"
        #create db in dbpath
        try: 
            self.db.firstInit(db=args['dbpath'])
        except db.DatabaseException as e:
            return e.err
        return
    
    ######################################## User Group Ops ######################################
    
    def addUserGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        # UserGroup (id integer, name text, ip_range text)
        row=(args['user_group_id'],args['name'],'') #todo
        print "row ",row
        try: 
            self.db.insert("UserGroup",row) 
        except db.DatabaseException as e:
            return e.err
        
    def delUserGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try: 
            for ugname in args['user_group_s']['names']:
                self.db.deleteRowsWithCriteria("UserGroup",'and',{'name':ugname}) 
            for ugid in args['user_group_s']['ids']:
                self.db.deleteRowsWithCriteria("UserGroup",'and',{'id':ugid}) 
        except db.DatabaseException as e:
            return e.err
        
    def modifyUserGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        #self._initDB()
        try: 
            ugid=self.db.getOneRowWithCriteria('UserGroup','*','or',{'id':args['user_group_s'],'name':args['user_group_s']})['id']
            self.db.update('UserGroup',ugid,{'name':args['name']}) 
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
        row=(args['vm_group_id'],args['name']) #todo add iprange
        print "row ",row
        try: 
            self.db.insert("VMGroup",row) 
        except db.DatabaseException as e:
            return e.err
        
    def delVMGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try: 
            for ugname in args['vm_group_s']['names']:
                self.db.deleteRowsWithCriteria("VMGroup",'and',{'name':ugname}) 
            for ugid in args['vm_group_s']['ids']:
                self.db.deleteRowsWithCriteria("VMGroup",'and',{'id':ugid}) 
        except db.DatabaseException as e:
            return e.err
        
    def modifyVMGroup(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        #self._initDB()
        try: 
            vmgid=self.db.getOneRowWithCriteria('VMGroup','*','or',{'id':args['vm_group_s'],'name':args['vm_group_s']})['id']
            self.db.update('VMGroup',vmgid,{'name':args['name']}) 
        except db.DatabaseException as e:
            return e.err
    
    def listVMGroups(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        try: 
            rows=self.db.getRowsWithCriteria('VMGroup','*', '', {})
            # UserGroup (id integer, name text, //ip_range text)
            print '-'*separator_len
            print "%-6s %s"%('id','name')
            print '-'*separator_len
            for row in rows:
                print "%-6s %s"%(row['id'],row['name'])
        except db.DatabaseException as e:
            return e.err
        return
        
    ######################################## User Ops ############################################ 

    # admin only
    def addUser(self,args):#, uid, name, ip_range, mac_range, max_running_vm, max_storage, storage_folder, is_admin):
        msj=""
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed" 
    
        #User (id, name, ip_range, gid_list,max_running_vm, max_storage,storage_folder,is_admin)
        # user_group_s is a mixture of group names and ids.. convert to ids only , eg ",31,admin, 3" >>(31, 0, 3)
        #todo move this in validate
        
        self._initDB() 
        
        okgroups=[1] # default insert in group 'all_users'
        groupnames=[]
        if(args['user_group_s']):
            groups=args['user_group_s'].split(',')  
            rex1=re.compile(r"[a-zA-Z_0-9]+")
            rex2=re.compile(r"[0-9]+")
            for s in groups:
                if(rex2.match(s)):
                    okgroups.append(s)
                elif(rex1.match(s)):
                    groupnames.append(s)
            try: 
                for gn in groupnames:
                    rows=self.db.getRowsWithCriteria('UserGroup','*', 'and', {'name':gn})
                    if(len(rows)>1):
                        raise db.DatabaseException("Inconsistent table Group: name in multiple rows")
                    if(len(rows)==0):
                        msj+="Ignoring group {0} : name not found".format(gn)
                    okgroups.append(rows[0]['id'])
            except db.DatabaseException as e:
                return e.err 

        print "okgroups ",tuple(okgroups)
        #gids_tuple=tuple(int(v) for v in re.findall("[a-zA-Z_0-9]+",gids_text))
        #todo verify gids are in bd
        row=(args['user_id'],args['name'],args['ip_range'],str(tuple(okgroups)),args['maxrun'],args['maxstor'],args['storage_dir'])
        print "row ",row
        try: 
            self.db.insert("User",row) 
        except db.DatabaseException as e:
            return e.err
        return msj
    
    # admin only
    def listUsers(self,args):
        if(not self.verify('isadmin',{'who':self.real_uid})):
            return "Not allowed"
        
        self._initDB()
        try: 
            rows=self.db.getRowsWithCriteria('User','*', '', {})
            #User (id, name, ip_range, gid_list,max_running_vm, max_storage,storage_folder)
            print '-'*separator_len
            print "%-5s %-22s %-18s %-10s %-16s %-13s %-100s"%('uid','name','ip_range','gid_list','max_running_vm','max_storage','storage_folder')
            print '-'*separator_len
            for row in rows:
#                print "%-5s %-22s %-18s %-10s %-16s %-13s %-100s"%(row['id'],row['name'],row['ip_range'],row['gid_list'],
#                                                                  row['max_running_vm'],row['max_storage'],row['storage_folder'],)
                print "%-5s %-22s %-18s %-10s %-16s %-13s %-100s"%tuple(row)
        except db.DatabaseException as e:
            return e.err
        return
    
#    def deleteUser(self,user):
#        # getOneByNameOrId("User",user), scot uid
#        # delete("User",uid)
#        pass
#    
#    def setUserDetail(self,user,detail,value):
#        # getOneByNameOrId("User",user), scot uid
#        # update("User",uid,dict(detail=value))...cum fac asta..#todo detail nu ar trebui sa fie string, poate puna lista de tuple
#        pass
    ######################################## Permissions Ops ###################################### 

    
    def setPermissions(self,args):
        # user/ug  vm/vmg 
        # check real_uid is owner or admin
        self._initDB()
        try: 
            #todo vm_group_s user_group_s
            #self.db.setPermissions(2,124,{'modify':0,'derive':0})
            if(args['user']):
                user_id=self.db.getOneRowWithCriteria('User','*','or',{'id':args['user'],'name':args['user']})['id']
            if(args['vm']):
                vm_id=self.db.getOneRowWithCriteria('VM','*','or',{'id':args['vm'],'name':args['vm']})['id']
            print args['permset']
            self.db.setPermissions(user_id, vm_id, args['permset'])                                                  
        except db.DatabaseException as e:  
            return e.err 
        pass
#    
#    def getVMsWithPermission(self, user_id, perm):  
#        # user wants to find out which vms he has permission on; perm is "run"/"modify"/"derive"/"force_isolated"
#        #  
#        # 
#        pass   
    
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
                disc_sizes=sum(ast.literal_eval(row['storage']).values())   #list of sizes
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
                vm_gid_list=ast.literal_eval(rows[0]['gid_list'])
            except db.DatabaseException as e:  
                return e.err    
            if(not self.verify('derive',{'who':(self.real_uid,)+gid_list,'what':(base_id,)+vm_gid_list})):
                return "You don't have permission to derive this vm"
        
        vmc=creator.VMCreator()
        # create discs in user home., if derivable create it in base_disc_location, base_domain_location, if from base clone discs
        discs_basename=str(self.real_uid)+"_"+args['name']

        if(args['derivable'] and not args['use_discs']):
            storage=vmc.createDiscs("", discs_basename, base_disc_location,args['storage'],'create')
        elif(args['base']):
            storage=vmc.createDiscs(base_storage, discs_basename, storage_folder,{},'clone')
        elif(args['derivable'] and args['use_discs']):
            storage=vmc.createDiscs(args['use_discs'], discs_basename, base_disc_location,{},'copy')
        elif(not args['derivable'] and args['use_discs']):
            storage=vmc.createDiscs(args['use_discs'], discs_basename, storage_folder,{},'rename')
        else:
            storage=vmc.createDiscs("", discs_basename, storage_folder,args['storage'],'create')
        
        #uuid=vmc.genUUID()
        # create domain /clone domain and change uuid name stordir..#todo

        # insert in db
        # todo
        gid_list=[1] # default add to group all_vms
        if(args['vm_group_s']):
            pass #todo append in list
        
        # VM (id, name, owner_id, gid_list, storage,derivable, base_uuid,mac,ip,vnc,desc,started)
        try:
            new_id=self.db.genNextId('VM','>')
            row=(new_id,args['name'],self.real_uid,str(tuple(gid_list)),str(storage),args['derivable'],base_id,"","","",args['desc'],0)
            print row
            self.db.insert('VM', row) # throws exc if name/id dupl
            self.db.setPermissions(self.real_uid,new_id,{'run':1,'modify':1,'derive':1,'force_isolated':0})
        except db.DatabaseException as e:  
            return e.err 
        
        

    def startVM(self,args):pass
    
    def runVM(self,args):#
        # --vmrun --vm _id/name [--mem _ --smp _ --install --cdrom _ --isolate] 
        # install nu mere fara cdrom 
        # err daca vm are deja base.

        # scot vm_id
        # pt uid si gids: getPermissions(uid, vm_id) , vrfy  run=1 , force_isolated suprascrie isolated,
        self._initDB()
        try: 
            rows=self.db.getRowsWithCriteria('VM','*', 'or', {'id':args['vm'],'name':args['vm']})
            if(len(rows)>1):
                raise db.DatabaseException("Too many VMs with this id/name")
            if(len(rows)==0):
                raise db.DatabaseException("VM ({0}) was not found in db".format(args['vm']))
            vm_id=rows[0]['id']
            discs=ast.literal_eval(rows[0]['storage'])
        except db.DatabaseException as e:  
            return e.err 
        # update("VM",vm_id,"started",1)
        vms=starter.VMStarter()
        vms.getParamsForKVM(self.real_uid, vm_id, discs, args['mem'], args['smp'], args['install'], args['cdrom'], args['isolate'])
        

    def listVM(self,args):
        self._initDB()
        try:
            if(self.verify('isadmin',{'who':self.real_uid})):
                rows=self.db.getRowsWithCriteria('VM','*', '', {})
            else:
                # todo user can see vms that he has perm on too..i think
                rows=self.db.getRowsWithCriteria('VM','*', 'and', {'owner_id':self.real_uid})
            
            #VM (id, name, owner_id, gid_list, storage,derivable, base_id,mac,ip,vnc,desc,started)
            print '-'*separator_len
            print "%-5s %-22s %-10s %-10s %-11s %-9s %-30s %s"%('vmid','name','owner_id','vm_groups',
                                                                      'derivable','base_id','desc','storage')
            print '-'*separator_len
            for row in rows:
                print "%-5s %-22s %-10s %-10s %-11s %-9s %-30s %s"%(row['id'],row['name'],row['owner_id'],row['gid_list'],
                                                                                        row['derivable'],row['base_id'],row['desc'],row['storage'],)
        except db.DatabaseException as e:
            return e.err
        return
    
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
        elif(action=='vm_add'):
            e=self.addVM(args)
        elif(action=='vm_run'):
            e=self.runVM(args)
        elif(action=='vm_list'):
            e=self.listVM(args)
        elif(action=='permlist'):
            e=self.listPerms(args)
        elif(action=='maplist'):
            e=self.listMapping(args)
        elif(action=='permset'):
            e=self.setPermissions(args)
        return e
################################################################################# test area
    
def main():
    pass
    

if __name__ == "__main__": main()
