#!/usr/bin/python
from optparse import OptionParser
import commands
import os
import re
import tools

id_range_limit=1000

class VMUserInterface:
    def __init__(self,vmtools,real_uid):
        self.vmtools=vmtools
        self.parser=OptionParser()
        self.opts=None
        self.real_uid=real_uid
        
    def parseOpts(self):
        # First thing to do
        self.parser.add_option("--init",dest="init",action='store_true',help="to initialize the db when first used",default=False)
        self.parser.add_option("--dbpath",dest="dbpath",help="path to database")
        
        # multipurpose opts
        self.parser.add_option("--name",dest="name",help="add user group")
        self.parser.add_option("--user",dest="user",help="")
        self.parser.add_option("--vm",dest="vm",help="")
        self.parser.add_option("--ug",dest="user_group_s",help="add user group")
        self.parser.add_option("--vmg",dest="vm_group_s",help="add user group")
        self.parser.add_option("--uid",dest="user_id",help="add user group")
        self.parser.add_option("--uuid",dest="uuid",help="identifier used with domains in libvirt")
        self.parser.add_option("--ugid",dest="user_group_id",help="add user group")
        self.parser.add_option("--vmgid",dest="vm_group_id",help="add user group")
        self.parser.add_option("--iprange",dest="ip_range",help="add user group",default="")

        # User Groups
        self.parser.add_option("--ugadd",dest="user_group_add",action='store_true',help="add user group",default=False)
        self.parser.add_option("--ugdel",dest="user_group_del",action='store_true',help="delete user group",default=False)
        self.parser.add_option("--ugmod",dest="user_group_mod",action='store_true',help="modify user group",default=False)
        self.parser.add_option("--uglist",dest="list_user_groups",action='store_true',help="list user groups",default=False)
        # VM Groups
        self.parser.add_option("--vmgadd",dest="vm_group_add",action='store_true',help="add user group",default=False)
        self.parser.add_option("--vmgdel",dest="vm_group_del",action='store_true',help="delete user group",default=False)
        self.parser.add_option("--vmgmod",dest="vm_group_mod",action='store_true',help="modify user group",default=False)
        self.parser.add_option("--vmglist",dest="list_vm_groups",action='store_true',help="list vm groups",default=False)
        # Users
        self.parser.add_option("--uadd",dest="user_add",action='store_true',help="add user ",default=False)
        self.parser.add_option("--udel",dest="user_del",action='store_true',help="delete user ",default=False)
        self.parser.add_option("--umod",dest="user_mod",action='store_true',help="modify user ",default=False)
        self.parser.add_option("--maxrun",dest="maxrun",help="",default=2)
        self.parser.add_option("--maxstor",dest="maxstor",help="",default="13G")
        self.parser.add_option("--stordir",dest="storage_dir",help="add user group")
        self.parser.add_option("--ulist",dest="user_list",action='store_true',default=False,help="list users with diff criteria")
        self.parser.add_option("--str",dest="string_to_find",help="")
        # VMs
        self.parser.add_option("--vmadd",dest="vm_add",action='store_true',help="add vm ",default=False)
        self.parser.add_option("--vmdel",dest="vm_del",action='store_true',help="delete vm ",default=False)
        self.parser.add_option("--vmmod",dest="vm_mod",action='store_true',help="modify vm ",default=False)
        self.parser.add_option("--vmrun",dest="vm_run",action='store_true',help="modify vm ",default=False)
        self.parser.add_option("--usediscs",dest="use_discs",help="eg. '/path/file1.qcow1,/path/file2.qcow1 (first is used to boot)")
        self.parser.add_option("--stor",dest="storage",help="eg. '5G,500M (creates 2 discs), '3G' (one disc) or wtv.",default="5G")
        self.parser.add_option("--smp",dest="smp",help="# processors, default 1",default=1)
        self.parser.add_option("--mem",dest="mem",help="memory in megabytes (eg '512' or '512M','1G'), default 512",default="1G")
        self.parser.add_option("--isolate",dest="isolate",action='store_true',help="Isolates vm from the others",default=False)
        self.parser.add_option("--base",dest="base",help="",default="")
        self.parser.add_option("--desc",dest="desc",help="",default="")
        self.parser.add_option("--derivable",dest="derivable",action='store_true',default=False,help="")
        self.parser.add_option("--noderivable",dest="noderivable",action='store_true',default=False,help="")
        self.parser.add_option("--install",dest="install",action='store_true',help="if specified, the vm will boot from the cdrom (which must be specified also)",default=False)
        self.parser.add_option("--cdrom",dest="cdrom",help="specify .iso installation file")
        self.parser.add_option("--owner",dest="owner",help="")
        self.parser.add_option("--vmlist",dest="vm_list",action='store_true',help="find vm ",default=False)
        self.parser.add_option("--perm",dest="perm",help="")
        self.parser.add_option("--running",dest="running",action='store_true',default=False,help="")
        # Permissions
        self.parser.add_option("--permset",dest="permset",help="")
        self.parser.add_option("--permlist",dest="permlist",action='store_true',help="list permissions",default=False)
        # Mappings
        self.parser.add_option("--maplist",dest="maplist",action='store_true',help="list existing mappings in db",default=False)

        (self.opts,args)=self.parser.parse_args()
    
    
    def check_vm_add(self):
        # vrfy base/storage exclusive and  mandatory, name mandatory,  derivable/base ori una ori niciuna
        # validate storage format numberM|G , convert to list and into M
        rex1=re.compile(r"[1-9][0-9]*[MG]")
        #print self.opts['storage']
        sizes=self.opts_dict['storage'].split(',')
        newsizes=[]
        for size in sizes:
            if(rex1.match(size)):
                if(size[-1]=='G'):
                    newsizes.append(int(size[:-1]+"000"))
                else:
                    newsizes.append(int(size[:-1]))
        if(len(newsizes)<1):
            print "Invalid storage"
            return False
        self.opts_dict['storage']=newsizes
        
        # use_discs #todo check if list of valid qcow2 existing paths
        if(self.opts_dict['use_discs']):
            self.opts_dict['use_discs']=self.opts_dict['use_discs'].split(',')
        
        return True
        
    def check_permset(self):
        #todo 
        # self.opts_dict['use_discs'] is like "+m,-d,+r,-i"
        perm_err="invalid permissions: should be a list from +m,+d,+r,+i,-m,-d,-r,-i"
        permdict={}
        for perm in self.opts_dict['permset'].split(","):
            if(len(perm)!=2):
                print perm_err
                return False
            add_del=perm[0]
            if(add_del=="+"):
                add_del=1
            elif(add_del=="-"):
                add_del=0
            else:
                print perm_err
                return False
            if(perm[1]=="m"): permdict['modify']=add_del
            elif(perm[1]=="d"): permdict['derive']=add_del
            elif(perm[1]=="r"): permdict['run']=add_del
            elif(perm[1]=="1"): permdict['force_isolated']=add_del
            else: print perm_err
        self.opts_dict['permset']=permdict
        print permdict
        return True
    
    def check_user_group_add(self):
        rex1=re.compile(r"[a-zA-Z_0-9]+")
        rex2=re.compile(r"[0-9]+")
        if(not self.opts_dict['name'] or not self.opts_dict['user_group_id'] or 
           not rex1.match(self.opts_dict['name']) or not rex2.match(self.opts_dict['user_group_id']) or 
           not int(self.opts_dict['user_group_id'])<id_range_limit):
            print "Invalid action. Usage: --ugadd --name _ --ugid _  (name allowed characters: 0-9a-zA-Z_)"
            return False
        return True
        
    def check_user_group_del(self):
        if(not self.opts_dict['user_group_s']):
            print "Invalid action. Usage: --ugdel --ug _id/name[,..]"
            return False
        rex1=re.compile(r"[a-zA-Z_0-9]+")
        rex2=re.compile(r"[0-9]+")
        ugids=[]
        ugnames=[]
        for ug in self.opts_dict['user_group_s'].split(','):
            if(rex2.match(ug)):
                ugids.append(ug)
            elif(rex1.match(ug)):
                ugnames.append(ug)
        if(len(ugids)==0 and len(ugnames)==0):
            print "Nothing to delete, maybe your (list of) group(s) is invalid"
            return False
        self.opts_dict['user_group_s']={'ugids':ugids,'ugnames':ugnames}
        return True
    
    def check_user_group_mod(self):
        rex1=re.compile(r"[a-zA-Z_0-9]+")
        rex2=re.compile(r"[0-9]+")
        if(not self.opts_dict['user_group_s'] or not self.opts_dict['name'] or
           not (rex1.match(self.opts_dict['user_group_s']) or rex2.match(self.opts_dict['user_group_s'])) or
           not rex1.match(self.opts_dict['name']) ):
            print "Invalid action. Usage: --ugmod --ug _id/name[,..] --name _ (name allowed characters: 0-9a-zA-Z_)"
            return False
        return True
    
    def check_vm_group_add(self):
        rex1=re.compile(r"[a-zA-Z_0-9]+")
        rex2=re.compile(r"[0-9]+")
        if(not self.opts_dict['name'] or not self.opts_dict['vm_group_id'] or 
           not rex1.match(self.opts_dict['name']) or not rex2.match(self.opts_dict['vm_group_id']) or 
           not int(self.opts_dict['vm_group_id'])<id_range_limit):
            print "Invalid action. Usage: --vmgadd --name _ --vmgid _  (name allowed characters: 0-9a-zA-Z_)"
            return False
        return True
        
    def check_vm_group_del(self):
        if(not self.opts_dict['vm_group_s']):
            print "Invalid action. Usage: --vmgdel --vmg _id/name[,..]"
            return False
        rex1=re.compile(r"[a-zA-Z_0-9]+")
        rex2=re.compile(r"[0-9]+")
        vmgids=[]
        vmgnames=[]
        for ug in self.opts_dict['vm_group_s'].split(','):
            if(rex2.match(ug)):
                vmgids.append(ug)
            elif(rex1.match(ug)):
                vmgnames.append(ug)
        if(len(vmgids)==0 and len(vmgnames)==0):
            print "Nothing to delete, maybe your (list of) group(s) is invalid"
            return False
        self.opts_dict['vm_group_s']={'vmgids':vmgids,'vmgnames':vmgnames}
        return True
    
    def check_vm_group_mod(self):
        rex1=re.compile(r"[a-zA-Z_0-9]+")
        rex2=re.compile(r"[0-9]+")
        if(not self.opts_dict['vm_group_s'] or not self.opts_dict['name'] or
           not (rex1.match(self.opts_dict['vm_group_s']) or rex2.match(self.opts_dict['vm_group_s'])) or
           not rex1.match(self.opts_dict['name']) ):
            print "Invalid action. Usage: --vmgmod --vmg _id/name[,..] --name _ (name allowed characters: 0-9a-zA-Z_)"
            return False
        return True
        
    def validateArgs(self,action): 
        if(action=='user_group_add'):
            return self.check_user_group_add()
        if(action=='user_group_del'):
            return self.check_user_group_del()
        if(action=='user_group_mod'):
            return self.check_user_group_mod()
        
        if(action=='vm_group_add'):
            return self.check_vm_group_add()
        if(action=='vm_group_del'):
            return self.check_vm_group_del()
        if(action=='vm_group_mod'):
            return self.check_vm_group_mod()
        
        if(action=='vm_add'):
            return self.check_vm_add()
        if(action=='permset'):
            return self.check_permset()
        return True # False #todo!!
    
    # vrfy command arguments and call the controller
    def extractCommand(self):
        # these are exclusive, there should be only one: 
        #acts ="ugadd ugdel ugmod vmgadd vmdel vmmod uadd udel umod ulist vmadd vmrun vmmod vmlist permset permlist"
        # don't forget the space at the end, in case you add more !
        acts = "init user_group_add user_group_del user_group_mod list_user_groups "+\
                "vm_group_add vm_group_del vm_group_mod list_vm_groups "+\
                "user_add user_del user_mod user_list "+\
                "vm_add vm_del vm_mod vm_run vm_list "+\
                "permset permlist maplist"
        action_list=acts.split(' ')
        self.opts_dict=vars(self.opts) 
        #print opts_dict.keys()
        no=0 # count options (there should be only one of these
        for opt in action_list:
            if(self.opts_dict[opt]):
                action=opt
                no+=1
        if(no>1 or no<1): 
            print "err: Too many actions";exit(1)
        if(not self.validateArgs(action)):
            print "err: Validating action".format(action);exit(1)
        #print action
        error=self.vmtools.execute(self.real_uid,action,self.opts_dict)
        if(error): print error

   
################################################################################# test area
    
def main():
#    if(os.getuid()!=0): print "err";exit(1)
    real_uid=commands.getstatusoutput("echo $SUDO_USER | xargs -I name id -u name ")[1] 
    vmtools=tools.VMTools(real_uid)
    ui=VMUserInterface(vmtools,real_uid)
    ui.parseOpts()
    ui.extractCommand()
    

if __name__ == "__main__": main()