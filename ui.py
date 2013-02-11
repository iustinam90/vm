#!/usr/bin/python -u
from optparse import OptionParser
import commands
import ConfigParser
import os
import re
import controller

conf_file="/opt/ncit-cloud/vm.ini"
debug=1

class VMUserInterface:
    def __init__(self):
        self.parser=OptionParser()
        self.opts=None
        
    def getConf(self):
        config = ConfigParser.ConfigParser()
        config.read(conf_file)
        conf=config._sections['conf']
        errs=""
        needed_opts="default_db default_ip_range default_admin_uid default_admin_home dhcp_keyname dhcp_secret dhcp_server dhcp_port id_range_limit base_domain_location base_disc_location vmoutdir separator_len watcher_path starter_path server_ip"
        for opt in needed_opts.split(' '):
            if(not opt in conf.keys()): 
                print "Missing option: {0}".format(opt);
                exit(1)
        dirs="base_disc_location base_domain_location default_admin_home"
        for d in dirs.split(' '):
            if(not os.path.isdir(conf[d])):
                errs+="Path does not exist: {0}".format(conf[d])
        files="watcher_path starter_path"
        for f in files.split(' '):
            if(not os.path.exists(conf[f])):
                errs+="File does not exist: {0}".format(conf[f])
        if(not os.path.exists(os.path.dirname(conf['default_db']))):
            errs+="Database path does not exist: {0}".format(conf['default_db'])
        if(errs):
            print "Invalid configuration file: {0}".format(conf_file)
            print errs
            exit(1)
        self.conf=conf
        
    def parseOpts(self):
        # First thing to do
        self.parser.add_option("--ruid",dest='ruid',help="real user id")
        self.parser.add_option("--init",dest="init",action='store_true',help="to initialize the db when first used",default=False)
        self.parser.add_option("--dbpath",dest="dbpath",help="path to database")
        
        # multipurpose opts
        self.parser.add_option("--name",dest="name",help="name (for vm,user,user group or vm group) (<50 chars)")
        self.parser.add_option("--user",dest="user",help= "user id or name")
        self.parser.add_option("--vm",dest="vm",help="vm id or name")
        self.parser.add_option("--ug",dest="user_group_s",help="(list of) user group id or name")
        self.parser.add_option("--vmg",dest="vm_group_s",help="(list of) vm group id or name")
        self.parser.add_option("--uid",dest="user_id",help="user id")
        self.parser.add_option("--uuid",dest="uuid",help="identifier used with domains in libvirt #unused")
        self.parser.add_option("--ugid",dest="user_group_id",help="user group id")
        self.parser.add_option("--vmgid",dest="vm_group_id",help="vm group id")
        self.parser.add_option("--iprange",dest="ip_range",help="example: 192.168.10.1-192.168.10.254",default="")

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
        self.parser.add_option("--maxrun",dest="maxrun",help="maximum number of running vms allowed",default=2)
        self.parser.add_option("--maxstor",dest="maxstor",help="maximum storage size allowed (eg. 100G)",default="133G")
        self.parser.add_option("--stordir",dest="storage_dir",help="storage directory (in user home maybe)")
        self.parser.add_option("--ulist",dest="user_list",action='store_true',default=False,help="list users")
        self.parser.add_option("--str",dest="string_to_find",help="#unused")
        # VMs
        self.parser.add_option("--vmadd",dest="vm_add",action='store_true',help="add vm ",default=False)
        self.parser.add_option("--vmdel",dest="vm_del",action='store_true',help="delete vm ",default=False)
        self.parser.add_option("--vmmod",dest="vm_mod",action='store_true',help="modify vm ",default=False)
        self.parser.add_option("--vmrun",dest="vm_run",action='store_true',help="modify vm ",default=False)
        self.parser.add_option("--usediscs",dest="use_discs",help="list of paths separated by , (first is used to boot)")
        self.parser.add_option("--stor",dest="storage",help="eg. '5G,500M (creates 2 discs), '3G' (one disc) or wtv.")
        self.parser.add_option("--smp",dest="smp",help="# processors, default 1",default=1)
        self.parser.add_option("--mem",dest="mem",help="memory in megabytes (eg '512' or '512M','1G'), default 512",default="1G")
        self.parser.add_option("--isolate",dest="isolate",action='store_true',help="Isolates vm from the others",default=False)
        self.parser.add_option("--base",dest="base",help="template vm id or name",default="")
        self.parser.add_option("--desc",dest="desc",help="description (<50 chars)",default="")
        self.parser.add_option("--derivable",dest="derivable",action='store_true',default=False,help="make it template")
        self.parser.add_option("--noderivable",dest="noderivable",action='store_true',default=False,help="")
        self.parser.add_option("--install",dest="install",action='store_true',help="if specified, the vm will boot from the cdrom (which must be specified also)",default=False)
        self.parser.add_option("--cdrom",dest="cdrom",help="specify .iso installation file")
        self.parser.add_option("--owner",dest="owner",help="")
        self.parser.add_option("--vmlist",dest="vm_list",action='store_true',help="find vm ",default=False)
        self.parser.add_option("--perm",dest="perm",help="#unused")
        self.parser.add_option("--running",dest="running",action='store_true',default=False,help="#unused")
        # Permissions
        self.parser.add_option("--permset",dest="permset",help="set permissions: any combination of +i,+d,+r,+m,-i,-d,-r,-m")
        self.parser.add_option("--permdel",dest="permdel",help="delete permissions",action='store_true',default=False)
        self.parser.add_option("--permlist",dest="permlist",action='store_true',help="list permissions",default=False)
        # Mappings
        self.parser.add_option("--maplist",dest="maplist",action='store_true',help="list existing mappings in db",default=False)
        self.parser.add_option("--mapdel",dest="mapdel",action='store_true',help="delete mappings in db",default=False)

        (self.opts,args)=self.parser.parse_args()
    
    ############################################################################################## 

    def name_ok(self,name):
        rex1=re.compile(r"^[a-zA-Z_0-9]+$")
        if(name and rex1.match(name) and len(name)<=50):
            return True
        if(debug): print "nok name"
        return False
    
    # comparison is '<' or '>'
    def id_number_ok(self,number,comparison):
        rex2=re.compile(r"^[0-9]+$")
        if(not number or not rex2.match(str(number)) or len(str(number))>6):
            if(debug): print "nok id"
            return False
        if(comparison=='>'):
            if(int(number)<controller.id_range_limit): return False
        elif(comparison=='<'):
            if(int(number)>controller.id_range_limit): return False
        else:
            print "comparison sign incorrect"; exit(1)
        return True
    
    # for checking mixtures of ids and names, 
    # in: "nume1,12,nume2,
    # returns {'ids':[1,2..],'names':[name1,name2..]}
    def list_ok(self,mixed_list,comparison):
        if(not mixed_list):
            return False
        ids=[]
        names=[]
        for item in mixed_list.split(','):
            if(self.id_number_ok(item,comparison)):
                ids.append(int(item))
            elif(self.name_ok(item)):
                names.append(item)
        if(len(ids)==0 and len(names)==0):
            print "Nothing valid in your list"
            return False
        return {'ids':ids,'names':names}
            
    # validate memory/disc size: 1G,100M 
    # ! returns size in M
    def size_ok(self,size):
        rex1=re.compile(r"[1-9][0-9]*[MG]")
        if(rex1.match(size)):
            if(size[-1]=='G'):
                return int(size[:-1]+"000")
            elif(size[-1]=='M'):
                return int(size[:-1])
        return False
    
    def path_ok(self,path,is_qcow):
        if(not path or not os.path.exists(path)):
            print "Invalid path: missing/does not exist: ",path
            return False
        # returns "data" for new images. leave this for now
#        if(is_qcow):
#            if(not commands.getstatusoutput("file {0} |grep 'Qemu Image,'".format(path))[1]):
#                print "Invalid path: not a qemu image"
#                return False
        return True
    
    def ip_range_ok(self,iprange):
        if(not iprange):
            return False
        #todo check format, eg 10.42.31.1-10.42.334.3"
        for ip in iprange.split('-'):
            for n in ip.split('.'):
                if(not n.isdigit()):
                    return False
                if(int(n)>255):
                    return False
        return True
    ############################################################################################## 
    
    def check_init(self):
        if(not self.path_ok(os.path.dirname(self.opts_dict['dbpath']), 0)):
            print "Invalid action. Usage: --init --dbpath _ (please provide a valid path (including filename) where database will be created)"
            return False
        return True
    
    def check_user_group_add(self):
        if(not self.name_ok(self.opts_dict['name']) or not self.id_number_ok(self.opts_dict['user_group_id'], '<')):
            print "Invalid action. Usage: --ugadd --name _ --ugid _  (name allowed characters: 0-9a-zA-Z_)"
            return False
        self.opts_dict['user_group_id']=int(self.opts_dict['user_group_id'])
        return True
        
    def check_user_group_del(self):
        filteredDict=self.list_ok(self.opts_dict['user_group_s'],'<')
        if(not filteredDict):
            print "Invalid action. Usage: --ugdel --ug _id/name[,..]"
            return False
        self.opts_dict['user_group_s']=filteredDict
        return True
    
    def check_user_group_mod(self):
        if(not (self.name_ok(self.opts_dict['user_group_s']) or self.id_number_ok(self.opts_dict['user_group_s'], '<')) or
            not  self.name_ok(self.opts_dict['name']) ):
            print "Invalid action. Usage: --ugmod --ug _id/name --name _ (name allowed characters: 0-9a-zA-Z_)"
            return False
        return True
    ############################################################################################## 
    
    def check_vm_group_add(self):
        if(not self.name_ok(self.opts_dict['name']) or not self.id_number_ok(self.opts_dict['vm_group_id'], '<')
           or not self.ip_range_ok(self.opts_dict['ip_range'])):
            print "Invalid action. Usage: --vmgadd --name _ --vmgid _ --iprange _ (name allowed characters: 0-9a-zA-Z_, iprange x.x.x.x-x.x.x.x)"
            return False
        self.opts_dict['vm_group_id']=int(self.opts_dict['vm_group_id'])
        return True
        
    def check_vm_group_del(self):
        filteredDict=self.list_ok(self.opts_dict['vm_group_s'],'<')
        if(not filteredDict):
            print "Invalid action. Usage: --vmgdel --vmg _id/name[,..]"
            return False
        self.opts_dict['vm_group_s']=filteredDict
        return True
    
    def check_vm_group_mod(self):
        if(not (self.name_ok(self.opts_dict['vm_group_s']) or self.id_number_ok(self.opts_dict['vm_group_s'], '<')) or
           not  (self.name_ok(self.opts_dict['name']) or self.ip_range_ok(self.opts_dict['ip_range']))):
            print "Invalid action. Usage: --vmgmod --vmg _id/name[,..] --name _ --iprange _ (name allowed characters: 0-9a-zA-Z_, iprange x.x.x.x-x.x.x.x)"
            return False
        return True
    ############################################################################################## 

    def check_user_add(self):
        #print self.id_number_ok(self.opts_dict['user_id'],'>')
        #print self.path_ok(self.opts_dict['storage_dir'], 0)
        if(not self.name_ok(self.opts_dict['name']) or not self.id_number_ok(self.opts_dict['user_id'],'>')
           or not self.path_ok(self.opts_dict['storage_dir'], 0)):
            print "Invalid action. Usage: --uadd --name _ --uid _ --stordir _ [-ug _id1/name1,..  --maxrun _(def=2) --maxstor _(def=133G) ]"
            return False
        #optional params
        if(self.opts_dict['user_group_s']):
            filteredDict=self.list_ok(self.opts_dict['user_group_s'],'<')
            if(not filteredDict):
                print "Invalid user group list"
                return False
            self.opts_dict['user_group_s']=filteredDict
        if(self.opts_dict['maxstor']):
            size=self.size_ok(self.opts_dict['maxstor'])
            if(not size):
                print "Invalid size for maximum storage"
                return False
            self.opts_dict['maxstor']=size
        if(self.opts_dict['maxrun'] and not self.id_number_ok(self.opts_dict['maxrun'], '<')):
            print "Invalid number for maximum running VMs"
            return False
        return True
    
    def check_user_del(self):
        filteredDict=self.list_ok(self.opts_dict['user'],'<')
        if(not filteredDict):
            print "Invalid action. Usage:--udel --user _id/name[,..]"
            return False
        self.opts_dict['user']=filteredDict
        return True
    
    def check_user_mod(self):
        if(not (self.name_ok(self.opts_dict['user']) or self.id_number_ok(self.opts_dict['user'], '>'))):
            print "Invalid action. Usage: --umod --user _id/name [--name _ --ug +|-_,_ --maxrun _ --maxstor _ --stordir _ ]"
            return False
        if(self.opts_dict['name']):
            if(not self.name_ok(self.opts_dict['name'])):
                print "Invalid name"
                return False
        if(self.opts_dict['storage_dir']):
            if(not self.path_ok(self.opts_dict['storage_dir'], 0)):
                print "Invalid storage_dir"
        if(self.opts_dict['user_group_s']):
            toadd=[]
            todel=[]
            for i in self.opts_dict['user_group_s'].split(','):
                if(i[0]=='+'):
                    toadd.append(i[1:]) #remove the +
                if(i[0]=='-'):
                    todel.append(i[1:]) #remove the -
                    
            self.opts_dict['user_group_s']={}
            self.opts_dict['user_group_s']['add']={}
            self.opts_dict['user_group_s']['del']={}
            self.opts_dict['user_group_s']['add']=self.list_ok(','.join(toadd),'<')
            self.opts_dict['user_group_s']['del']=self.list_ok(','.join(todel),'<')
            if(debug): print self.opts_dict['user_group_s']
            if(not self.opts_dict['user_group_s']['add'] and not self.opts_dict['user_group_s']['del']):
                print "Invalid user group list"
                return False
            if(not self.opts_dict['user_group_s']['add']):
                self.opts_dict['user_group_s']['add']={'names':[],'ids':[]}
            if(not self.opts_dict['user_group_s']['del']):
                self.opts_dict['user_group_s']['del']={'names':[],'ids':[]}
        if(self.opts_dict['maxstor']):
            size=self.size_ok(self.opts_dict['maxstor'])
            if(not size):
                print "Invalid size for maximum storage"
                return False
            self.opts_dict['maxstor']=size
        if(self.opts_dict['maxrun'] and not self.id_number_ok(self.opts_dict['maxrun'], '<')):
            print "Invalid number for maximum running VMs"
            return False
        return True
    
    def check_user_list(self):
        return True
    ############################################################################################## 
    
    def check_vm_add(self):
        usage="Usage: --vmadd --name _ [ --vmg _id1/name (!unul) --desc _ --derivable] --stor 1G,500M | --base _id/name | --usediscs path1,path2.."
        #  name mandatory
        if(not self.name_ok(self.opts_dict['name'])):
            print "Invalid name"
            print usage
            return False
        # use_discs #todo check if list of valid qcow2 existing paths
        one=0 # check if only one of use_discs|storage|base was specified
        if(self.opts_dict['use_discs']):
            one=1
            paths=self.opts_dict['use_discs'].split(',')
            self.opts_dict['use_discs']=[]
            self.opts_dict['use_discs']
            for path in paths:
                if(self.path_ok(path,1)):
                    self.opts_dict['use_discs'].append(path)
                else:
                    print "Invalid path in --usediscs"
                    print usage
                    return False
        if(self.opts_dict['storage']): # validate storage format numberM|G , convert to list and into M
            if(one): print "Please specify only one of these: --base --stor --usediscs"
            else: one=1
            newsizes=[]
            for size_str in self.opts_dict['storage'].split(','):
                size_int=self.size_ok(size_str)
                if(size_int):
                    newsizes.append(size_int)
            if(len(newsizes)<1):
                print "Invalid storage"
                print usage
                return False
            self.opts_dict['storage']=newsizes
        if(self.opts_dict['base']):
            if(one): print "Please specify only one of these: --base --stor --usediscs"
            else: one=1
            if(not (self.id_number_ok(self.opts_dict['base'], '>') or self.name_ok(self.opts_dict['base']))):
                print "Invalid base VM"
                print usage
                return False
        # optional stuff 
        if(self.opts_dict['vm_group_s']):
#            if(not (self.id_number_ok(self.opts_dict['vm_group_s'],'<') or self.name_ok(self.opts_dict['vm_group_s']))):
#                print "Invalid VM group."
#                return False
            newl={'ids':[],'names':[]}
            if(self.id_number_ok(self.opts_dict['vm_group_s'],'<')):
                newl['ids'].append(self.opts_dict['vm_group_s'])
            elif(self.name_ok(self.opts_dict['vm_group_s'])):
                newl['names'].append(self.opts_dict['vm_group_s'])
            else:
                print "Invalid VM group."
                print usage
                return False
            self.opts_dict['vm_group_s']=newl
        if(self.opts_dict['desc']):
            if(not self.name_ok(self.opts_dict['desc'])):
                print "Invalid description.(maximum lenght 50 characters, [a-zA-Z0-9_]+)"
                print usage
                return False
        if(self.opts_dict['derivable'] and self.opts_dict['base']):
            print "Invalid option combination: --derivable and --base "
            print usage
            return False
        if(self.opts_dict['derivable']):
            self.opts_dict['derivable']=1
        return True
    
    def check_vm_run(self):
        if(not (self.name_ok(self.opts_dict['vm']) or self.id_number_ok(self.opts_dict['vm'], '>'))):
            print "Invalid action. Usage: --vmrun --vm _id/name [--mem _ --smp _ --install --cdrom _ --isolate]"
            return False
        if(self.opts_dict['mem']):
            if(not self.size_ok(self.opts_dict['mem'])):
                print "Invalid size for --mem"
                return False
        if(self.opts_dict['smp']):
            if(not self.id_number_ok(self.opts_dict['smp'], '<')):
                print "Invalid size for --smp"
                return False
        if(self.opts_dict['install'] and not self.path_ok(self.opts_dict['cdrom'], 0)):
            print "Invalid option combination: --install requires a valid --cdrom path"
            return False
        return True
    
    def check_vm_del(self):
        filteredDict=self.list_ok(self.opts_dict['vm'],'>')
        if(not filteredDict):
            print "Invalid action. Usage: --vmdel --vm _id/name[,..]"
            return False
        self.opts_dict['vm']=filteredDict
        return True
    
    def check_vm_mod(self):
        if(not (self.name_ok(self.opts_dict['vm']) or self.id_number_ok(self.opts_dict['vm'], '>'))):
            print "Invalid action. Usage: --vmmod --vm _id/name [--name _ --owner _ --derivable | --noderivable]"
            return False
        if(self.opts_dict['name']):
            if(not self.name_ok(self.opts_dict['name'])):
                print "Invalid name"
                return False
        if(self.opts_dict['owner']):
            if(not self.name_ok(self.opts_dict['owner']) and not self.id_number_ok(self.opts_dict['owner'], '>')):
                print "Invalid owner"
                return False
        if(self.opts_dict['derivable'] and self.opts_dict['noderivable']):
            print "..make up your mind"
            return False
        return True
    ##############################################################################################
    
    def check_permset(self):
        if(not (self.name_ok(self.opts_dict['user']) or self.id_number_ok(self.opts_dict['user'], '>') 
                or self.name_ok(self.opts_dict['user_group_s']) or self.id_number_ok(self.opts_dict['user_group_s'], '<') )):
            print "Invalid action. Usage: --permset [+m,-d,+r,-i](at least one) --user|--ug _id/name  --vm|--vmg _id/name "
            return False
        if(not (self.name_ok(self.opts_dict['vm']) or self.id_number_ok(self.opts_dict['vm'], '>')
                or self.name_ok(self.opts_dict['vm_group_s']) or self.id_number_ok(self.opts_dict['vm_group_s'], '<') )):
            print "Invalid action. Usage: --permset [+m,-d,+r,-i](at least one) --user|--ug _id/name  --vm|--vmg _id/name"
            return False
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
            elif(perm[1]=="i"): permdict['force_isolated']=add_del
            else: print perm_err
        self.opts_dict['permset']=permdict
        if(debug): print permdict
        return True
    
    def check_permdel(self):
        if(not (self.name_ok(self.opts_dict['user']) or self.id_number_ok(self.opts_dict['user'], '>') 
                or self.name_ok(self.opts_dict['user_group_s']) or self.id_number_ok(self.opts_dict['user_group_s'], '<') )):
            print "Invalid action. Usage: --permdel --user|--ug _id/name  --vm|--vmg _id/name "
            return False
        if(not (self.name_ok(self.opts_dict['vm']) or self.id_number_ok(self.opts_dict['vm'], '>')
                or self.name_ok(self.opts_dict['vm_group_s']) or self.id_number_ok(self.opts_dict['vm_group_s'], '<') )):
            print "Invalid action. Usage: --permdel --user|--ug _id/name  --vm|--vmg _id/name"
            return False
        return True
    
    def check_mapdel(self):
        if(not (self.name_ok(self.opts_dict['user']) or self.id_number_ok(self.opts_dict['user'], '>'))):
            print "Invalid action. Usage: --mapdel --user _id/name --vm _id/name "
            return False
        if(not (self.name_ok(self.opts_dict['vm']) or self.id_number_ok(self.opts_dict['vm'], '>'))):
            print "Invalid action. Usage: --mapdel --user _id/name --vm _id/name"
            return False
        return True
    ##############################################################################################
    
    def validateArgs(self,action): 
        if(action=='init'):
            return self.check_init()
        
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
        
        if(action=='user_add'):
            return self.check_user_add()
        if(action=='user_del'):
            return self.check_user_del()
        if(action=='user_mod'):
            return self.check_user_mod()
        if(action=='user_list'):
            return self.check_user_list()
        
        if(action=='vm_add'):
            return self.check_vm_add()
        if(action=='vm_run'):
            return self.check_vm_run()
        if(action=='vm_del'):
            return self.check_vm_del()
        if(action=='vm_mod'):
            return self.check_vm_mod()
        
        if(action=='permset'):
            return self.check_permset()
        if(action=='permdel'):
            return self.check_permdel()
        
        if(action=='mapdel'):
            return self.check_mapdel()
        return True # False #todo!!
    ##############################################################################################
    
    # vrfy command arguments and call the controller
    def extractCommand(self,vmcontroller):
        # these are exclusive, there should be only one: 
        #acts ="ugadd ugdel ugmod vmgadd vmdel vmmod uadd udel umod ulist vmadd vmrun vmmod vmlist permset permlist"
        # don't forget the space at the end, in case you add more !
        acts = "init user_group_add user_group_del user_group_mod list_user_groups "+\
                "vm_group_add vm_group_del vm_group_mod list_vm_groups "+\
                "user_add user_del user_mod user_list "+\
                "vm_add vm_del vm_mod vm_run vm_list "+\
                "permset permlist permdel maplist mapdel"
        action_list=acts.split(' ')
        self.opts_dict=vars(self.opts) 
        #print opts_dict.keys()
        no=0 # count options (there should be only one of these
        for opt in action_list:
            if(self.opts_dict[opt]):
                action=opt
                no+=1
        if(no>1 or no<1): 
            print "err: Too many actions / No action specified";exit(1)
        if(not self.validateArgs(action)):
            print "err: Validating action".format(action);exit(1)
        #print action
        error=vmcontroller.execute(self.real_uid,action,self.opts_dict)
        if(error): print error

   
################################################################################# test area
    
def main():
##    if(os.getuid()!=0): print "err";exit(1)
#    real_uid=commands.getstatusoutput("echo $SUDO_USER | xargs -I name id -u name ")[1] 
#    real_uid=os.getuid()
    
    
    ui=VMUserInterface()
    ui.getConf()
    ui.parseOpts()
    
    #print "you ",os.getuid()
    #os.setuid(int(ui.opts.ruid))
    #print "you ",os.getuid()
    
    ui.real_uid=ui.opts.ruid
    if(not ui.real_uid):
        print "--ruid (real uid) missing"
        exit(1)
    vmcontroller=controller.VMController(ui.conf)
    vmcontroller.setRUID(ui.real_uid)
    ui.extractCommand(vmcontroller)
    

if __name__ == "__main__": main()