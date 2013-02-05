import ast
import db


debug=0

# works with IDs only
class Authorizer():
    def __init__(self):pass
    
            
    # {'who':uid}
    def isAdmin(self):
        try:
            row=self.db.getOneRowWithCriteria('User','*','and',{'id':self.items_dict['who']})
            gid_list=ast.literal_eval(row['gid_list'])
            if 0 in gid_list:
                return True
        except db.DatabaseException as e:  
            print e.err
            return False
        return False
    
    # {'who':uid,'what':vmid}
    def isOwner(self):
        try:
            row=self.db.getOneRowWithCriteria('VM','*','and',{'id':self.items_dict['what']})
            if(not row):
                raise db.DatabaseException("Userid not found (--owner option)")
            if(int(row['owner_id'])==int(self.items_dict['who'])):
                return True
        except db.DatabaseException as e:  
            print e.err
        return False
    
    # {'who':{uid,ugid..},'what':{vmid,vmgid,..}} 
    def hasPerm(self,perm):
        try:
            for who in self.items_dict['who']:
                for what in self.items_dict['what']:
                    rows=self.db.getRowsWithCriteria('Permission','*', 'and', {'user_g_id':who,'vm_g_id':what, perm:1})
                    if(len(rows)==1):
                        #print "rows",rows
                        return True                  
        except db.DatabaseException as e:  
            print e.err
            exit(1)
        return False
        
    def isOk(self,action,items_dict,_db):
        self.db=_db
        if(debug): print "Authorizer: verifying ",action," ",items_dict
        self.items_dict=items_dict
        # same perm names as in db
        if(action=="isadmin"):
            return self.isAdmin()
        if(action=="isowner"):
            return self.isOwner()
        if(action=="derive"):
            return self.hasPerm('derive')
        if(action=="modify"):
            return self.hasPerm('modify')
        if(action=="run"):
            return self.hasPerm('run')
        if(action=="force_isolated"):
            return self.hasPerm('force_isolated')
        print "err: authorizer: no such permission"
    