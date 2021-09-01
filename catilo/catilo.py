import uuid 
import os
import yaml
import json
import enum
from flatten_dict import flatten

"""
Var source priority:
    ENV: 1
    RUNTIME: 2
"""
class Priority(enum.Enum):
    ENV : 1
    USER_VARS : 2
    DEFAULT: 10
def __loadAsYml(path):
        with open(path,'r') as fp:
            data = yaml.safe_load(fp)
        return data

def __loadAsJSON(path):
        with open(path,'r') as fp:
            data = json.loads(fp.read())
        return data

def __loadFile(path):
        if str(path).lower().endswith('.yml') or str(path).lower().endswith('.yaml'):
            return __loadAsYml(path)
        elif str(path).lower().endswith('.json'):
            return __loadAsYml(path)
        else:
            raise UnsupportedFileTypeException(path.split('.')[-1])

class UnsupportedFileTypeException(Exception):
    def __init__(self,value="Unsupported File Type Exception"):
        self.value = value
    
    def __str__(self):
        return str(self.value)

class Source():
    def __init__(self,name,priority,file=None,dictionary : dict=None,url=None):
        self.name = name
        self.priority = int(priority)
        self.variables = {}
        if file != None:
            self.loadFile(file)
        if dictionary != None:
            self.variables.update(dictionary)

    def loadFile(self,path):
        try:
            variables =__loadFile(path)
            self.variables.update(dict(variables))
        except Exception:
            Exception('Could not read file, check again')

    def addVar(self,key,value):
        self.variables[key] = value
    
    def getVar(self,key):
        if key not in self.variables:
            raise UndefinedVariableException(key)
        else:
            return self.variables[key]
    
    def getVarsDict(self):
        return self.variables

    def getPriority(self):
        return self.priority
    
    def setPriority(self,priority):
        try:
            priority = int(priority)
        except Exception:
            raise IncorrectPriorityException(priority)

class BaseException(Exception):
    msg = "{value}"

    def __init__(self,value,msg=None):
        self.value = value
        if msg != None:
            self.msg = msg
        

    def __str__(self):
        return self.msg.format(self.value)
        
class IncorrectPriorityException(BaseException):
    msg = "Incorrect Priority Set {value}"

class UndefinedVariableException(BaseException):
    msg = "{value} not defined"

class DuplicateSourceException(BaseException):
    msg = "Source {value} already exists"

class UnknownSourceException(BaseException):
    msg = "Exception adding vars to unknown source [{value}]. PS: Source names are case sensitive"

class VariableDirectory():
    def __init__(self):
        self.prioritylist = {}
        self.sources = {}
        self.variables = {}
        self.uuidMappings = {}
        self.__add_base_sources()
        self.__update_vars()
    def getUUID(self):
        return str(uuid.uuid4().hex)

    def add_new_source(self,name,priority,file=None,dictionary=None):
        uuid = self.getUUID()
        if name in self.uuidMappings:
            raise DuplicateSourceException((name,self.uuidMappings[name]),msg = "Source {value[0]} already exists with uuid {value[1]}")
        self.sources[uuid] = Source(name,priority,file,dictionary)
        self.uuidMappings[name] = uuid
        if priority in self.prioritylist:
            self.prioritylist[priority].append(uuid)
        else:
            self.prioritylist[priority] = [uuid]
        self.__update_vars()

    def __add_base_sources(self):
        self.addNewSource('USER_VARS',Priority.USER_VARS)

    def add_new_files_to_source(self,name,path):
        if name not in self.uuidMappings:
            raise UnknownSourceException(name)

        uuid = self.uuidMappings[name]
        self.sources[uuid].loadFile(path)
        self.__update_vars()

    def add_runtime_var(self,key,value):
        uuid = self.uuidMappings['USER_VARS']
        self.sources[uuid].addVar(key,value)
        self.__update_vars()
    
    def enable_environment_vars(self,prefix:str="CATILO_",strip:bool=False):
        """
        Enables config retrieval from Environment variables
        @Params:
            prefix:str : A prefix value for bulk retrieval
            strip:bool : strip removes the prefix during storages. Eg, CATILO_VAR would be stored as VAR for prefix "CATILO_"   
        """
        identifier = "ENV_" + prefix
        if identifier in self.sources:
            raise DuplicateSourceException(prefix, msg=f"Environment source for prefix {prefix} is already present. Use refresh_env_vars(prefix) to refresh the vars")

        varsdict = self.__get_environment_vars(prefix)
        if strip:
            varsdict = { k.strip(prefix):v for k,v in varsdict.items()}
        self.add_new_source(identifier,priority=Priority.ENV,dictionary=varsdict)


    def __get_environment_vars(self,prefix="CATILO_"):
        envvars = dict(os.environ)
        envvars = { k: v for k,v in envvars.items() if str(k).startswith("CATILO_")}
        return envvars

    def __update_vars(self):
        priorities = sorted(list(self.prioritylist.keys()),reverse=True)
        for priority in priorities:
            for source in self.prioritylist[priority]:
                self.variables.update(self.sources[source].getVarsDict())
        
    def get(self,key):
        if key not in self.variables:
            raise UndefinedVariableException(key)
        else:
            return self.variables[key]

