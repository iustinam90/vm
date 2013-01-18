import sqlite3
import os
import subprocess

class DatabaseException:
    def __init__(self,err_string):
        self.err= err_string;

defaultDb = "vm.db"
defaultAdmin="503"

class VMDatabase:
    _dbPath = ""
    
    def __init__(self):pass
    def __del__(self):
        if(hasattr(self,'_conn')): self._conn.close()
        
    def init(self,db=defaultDb):  
        # open db 
        print "db ",db
        if(not os.path.exists(db)): 
            raise  DatabaseException("Database not found at {0}".format(db))
        self._dbPath = db
        self._conn = sqlite3.connect(self._dbPath)
        self._conn.row_factory = sqlite3.Row    # some useful sh.. I guess
        # create the tables if this is the first time
      
    def firstInit(self,db=defaultDb):
        print db  
        if(os.path.exists(db)): 
            raise  DatabaseException("Database already exists: {0}".format(db))
        if(subprocess.call("touch {0}".format(db),shell=True)): 
            raise DatabaseException("Cannot touch db at: "+db)
        self.init(db)
        self._init_tables()

    def insert(self,table,row):
        # suppose the details are ordered , # ! convention: name goes after id in any table
        print "inserting in {0} {1}".format(table,row)
        _noCols=dict(User=7,VM=12,Permission=6,UserGroup=3,VMGroup=2,Mapping=9) # !!todo update..dunno how right now
        # vrfy duplicate id/name
        if(table=='Permission' or table=="Mapping"):
            cursor=self._conn.execute('select count(*) from {0} where user_g_id=? and vm_g_id=?'.format(table),(row[0],row[1],))
            if(cursor.fetchone()[0]):
                raise  DatabaseException("Insert: duplicate uid-vm_id mapping")
        else:
            cursor=self._conn.execute('select count(*) from {0} where id = ?'.format(table),(row[0],))
            if(cursor.fetchone()[0]):
                raise  DatabaseException("Insert: duplicate id")
            cursor=self._conn.execute('select count(*) from {0} where name = ?'.format(table),(row[1],))
            if(cursor.fetchone()[0]):
                raise  DatabaseException("Insert: duplicate name")
        # insert
        cmd='insert into {0} values (?'.format(table)+',?'*(int(_noCols[table])-1)+')'
        self._conn.execute(cmd,row)
        self._conn.commit()
            
            
    def _init_tables(self):
        print "..creating tables"
        self._conn.execute('''CREATE TABLE User (id integer, name text, ip_range text, gid_list text,
            max_running_vm integer, max_storage integer,storage_folder text)''')
        self._conn.execute('''CREATE TABLE VM (id integer, name text, owner_id integer, gid_list text, storage integer, 
            derivable integer, base_id integer,mac text,ip text,vnc text,desc text,started integer)''')
        self._conn.execute('''CREATE TABLE Permission (user_g_id integer, vm_g_id integer, run integer, modify integer, 
            derive integer, force_isolated integer)''')
        self._conn.execute('''CREATE TABLE Mapping (user_g_id integer, vm_g_id integer, ip text, mac text, isolated integer,
            exechost text, vncport integer, tap text, date text)''')
        self._conn.execute('''CREATE TABLE UserGroup (id integer, name text, ip_range text)''')
        self._conn.execute('''CREATE TABLE VMGroup (id integer, name text)''')
        self._conn.commit()
        self.insert("UserGroup",(0,"admin","10.42.0.0/24"))
        self.insert("UserGroup",(1,"all_users","10.42.0.0/16"))
        self.insert("VMGroup",(1,"all_vms"))
        self.insert("User",(503,'admin1','','(0,)',1000,1000,'/home/me'))
        self._conn.commit()
    
            
    # this can update any set of columns ("mappings") in any existing table.
    def update(self,table,item_id,mappings):
        if(table!="User" and table!="VM" and table!="VMGroup" and table!="UserGroup"):
            raise DatabaseException("wrong update function for table type")
        cursor=self._conn.execute('select count(*) from {0} where id = ?'.format(table),(item_id,))
        if(cursor.fetchone()[0]!=1):
            raise DatabaseException("Update: 0/>1 rows found")
        sets=""
        for key in dict(mappings).keys():
            if(type(mappings[key]) is str):
                sets+="{0} = \"{1}\",".format(key,mappings[key])
            else:
                sets+="{0} = {1},".format(key,mappings[key])
        sets=sets[:-1]
        print 'update {0} set {1} where id = {2}'.format(table,sets,item_id)
        self._conn.execute('update {0} set {1} where id = ?'.format(table,sets),(item_id,))
        self._conn.commit()
    
    # this is updated separately because it has 2 identifiers: vmid/vmgid and uid/gid; rest is the same as above
    def update2(self,table,user_g_id,vm_g_id,mappings):
        if(table!="Permission" and table!="Mapping"):
            raise DatabaseException("wrong update function for table type")
        cursor=self._conn.execute('select count(*) from {0} where user_g_id = ? and vm_g_id = ? '.format(table),(user_g_id,vm_g_id,))
        if(cursor.fetchone()[0]!=1):
            raise  DatabaseException("Update: 0/>1 rows found")
        sets=""
        for key in dict(mappings).keys():
            if(type(mappings[key]) is str):
                sets+="{0} = \"{1}\",".format(key,mappings[key])
            else:
                sets+="{0} = {1},".format(key,mappings[key])
        sets=sets[:-1]
        print 'update {0} set {1} where  user_g_id = {2} and vm_g_id = {3}'.format(table,sets,user_g_id,vm_g_id)
        self._conn.execute('update {0} set {1} where  user_g_id = ? and vm_g_id = ?'.format(table,sets),(user_g_id,vm_g_id,))
        self._conn.commit()
        
        
    def getRowsWithCriteria(self,table,what,and_or,col_dict):
        # {'id':'1', 'name': gigi}
        # check if we need the 'where' and get the length of the bool op
        if(and_or=='or'):
            and_or_length=3
        elif(and_or=='and'):
            and_or_length=4
        elif(and_or==''):
            select_stmt="select {0} from {1} ".format(what,table)
        else:
            raise DatabaseException("Columns can only be 'or'ed or 'and'ed")
        
        #add criteria
        if(and_or=='and' or and_or=='or'):
            select_stmt="select {0} from {1} where ".format(what,table)
            for key in col_dict.keys():
                select_stmt+="{0} = ? {1} ".format(key,and_or)
            select_stmt=select_stmt[:-and_or_length]
        
        #print select_stmt
        #print tuple(col_dict.values())
        cursor=self._conn.execute(select_stmt,tuple(col_dict.values()));
        ls=cursor.fetchall()
        #print ls[0]['vm_g_id']
        return ls
    
    def getOneRowWithCriteria(self,table,what,and_or,col_dict):
        rows=self.getRowsWithCriteria(table,what,and_or,col_dict)
        if(len(rows)>1):
            raise DatabaseException("Inconsistent db: Too many items with this id/name in {0}".format(table))
        if(len(rows)==0):
            raise DatabaseException("No item was found in {0} for your criteria: {1}".format(table,str(col_dict)))
        return rows[0]
        
    def deleteRowsWithCriteria(self,table,and_or,col_dict):
        # check if we need the 'where' and get the length of the bool op
        if(and_or=='or'):
            and_or_length=3
        elif(and_or=='and'):
            and_or_length=4
        elif(and_or==''):
            stmt="delete from {0} ".format(table)
        else:
            raise DatabaseException("Columns can only be 'or'ed or 'and'ed")
        
        #add criteria
        if(and_or=='and' or and_or=='or'):
            stmt="delete from {0} where ".format(table)
            for key in col_dict.keys():
                stmt+="{0} = ? {1} ".format(key,and_or)
            stmt=stmt[:-and_or_length]
        
        print stmt,tuple(col_dict.values())
        self._conn.execute(stmt,tuple(col_dict.values()));
        self._conn.commit()
    
    # returns 1 tuple for the found row (.. which can be used as a dictionary too)
    def getOneByNameOrId(self,table,identifier):
        found_list=[]
        cursor=self._conn.execute('select * from {0} where id = ?'.format(table),(identifier,))
        found_list+=cursor.fetchall()
        cursor=self._conn.execute('select * from {0} where name = ?'.format(table),(identifier,))
        found_list+=cursor.fetchall()
        if(len(found_list)!=1):
            raise  DatabaseException("Too many / no rows returned for identifier: {0}".format(identifier))
        return found_list[0]
    
    def getRowsForOnePK(self,table,id):
        cursor=self._conn.execute('select * from {0} where id = ? '.format(table),(id,))
        ls=cursor.fetchall()
        return ls
    
    def getRowsForTwoPKs(self,table, u_g_id, vm_g_id):
        cursor=self._conn.execute('select * from {0} where user_g_id = ? and vm_g_id = ?'.format(table),(u_g_id,vm_g_id,))
        ls=cursor.fetchall()
        #if(len(ls)!=1):return None
        #return (list[0]['run'],list[0]['modify'],list[0]['derive'],list[0]['force_isolated'],)
        return ls
        
    # broken. don;t use. 
    def setPermissions(self, uid, vm_id, perms):
        # perms is a dict with perm to change
        # should allow to modify one or more perms 
        oldPerms=self.getRowsForTwoPKs('Permission',uid,vm_id)
        if(len(oldPerms)!=1): #assumed 0, hope is ok, else the table is not good
            self.insert('Permission',(uid,vm_id,perms.get('run',0),perms.get('modify',0),perms.get('derive',0),perms.get('force_isolated',0))) 
        else:
            self.update2("Permission",uid,vm_id,perms)
    
    def getVMsWithPermission(self,uid,perm):
        cursor=self._conn.execute('select VM.name from Permission,VM where VM.id=Permission.vm_g_id and user_g_id = ? and  {0} = 1'.format(perm),
                                  (uid,))
        return cursor.fetchall()
     
    def genNextId(self,table,sign):
        cursor=self._conn.execute('select max(id) from {0}'.format(table))
        maxx=cursor.fetchone()[0]
        if(not maxx):
            if(sign=='>'):
                maxx=1000
            elif(sign=='<'):
                maxx=0
        return int(maxx)+1
    
################################################################################# test area

def try_insert(db):
    db.insert("UserGroup",(2,"ug2","giprange"))
    db.insert("VMGroup",(2,"vmg2"))
    #User (id, name, ip_range, gid_list,max_running_vm, max_storage,storage_folder)
    db.insert("User",(2,"username","iprange","(0,1)",3,10,"storage_folder"))
    #VM (id, name, owner_id, gid_list, storage,derivable, base_uuid,mac,ip,vnc,desc,started)
    db.insert("VM",(124,"vmname",11,"0,1",10,1,0,"mac","ip",5901,"desc",0))
    db.insert("Permission",(2,124,1,1,1,0))
    print "inserted"
    
def main():
    try:
        db=VMDatabase()
        db.firstInit(db="vm.db")
        #db.init(db="vm.db")
        #db=VMDatabase(db="vm.db")
        try_insert(db)
        print dict(db.getOneByNameOrId("User","username")) # ! use
        print db.getOneByNameOrId("VM","vmname")
        print db.getRowsForTwoPKs("Permission",2,124)
        db.setPermissions(2,124,{'modify':0,'derive':0})
        print db.getRowsForTwoPKs("Permission",2,124)
        db.update('User',2,dict(name="myname",max_storage=3))
        print db.getOneByNameOrId('User',2)
        print "user 2 has run perm on: ",db.getVMsWithPermission(2,"run")
        print "user 2 has modify perm on: ",db.getVMsWithPermission(2,"modify")
        #(user_g_id,vm_g_id,ip,mac,isolated,exechost,vncport,date)
        db.insert('Mapping',(2,124,"ip","mac",1,"this",5901,"tap1","today"))
        db.update2('Mapping',2,124,dict(ip="myip",mac="mymac"))
        print "a",db.getRowsForTwoPKs("Mapping",2,124)
        
        print db.getRowsWithCriteria('Permission','*','and',{'user_g_id':2,'vm_g_id':124})
        print db.getRowsWithCriteria('User','*','or',{'id':2,'name':'username'})
        print db.getRowsWithCriteria('User','*', '', {})
        print db.getRowsWithCriteria('UserGroup','*', 'and', {'name':'admin'})
        # try some exceptions
        # duplicate user name/id
#        db.insert("User",(3,"myname","iprange","macrange",3,10,"storage_folder",1))
#        db.insert("User",(2,"username1","iprange","macrange",3,10,"storage_folder",1))
        # update nonexistent user/perm
#        db.update('User',6,dict(name="myname",max_storage=3))
    except DatabaseException as e:
        print e.err
        exit(1)
    
    
                    
if __name__ == "__main__": main()

