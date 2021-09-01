import uuid 
import os
import yaml
import json

def loadAsYml(path):
        with open(path,'r') as fp:
            data = yaml.safe_load(fp)
        return data

def loadAsJSON(path):
        with open(path,'r') as fp:
            data = json.loads(fp.read())
        return data

def loadFile(path):
        if str(path).lower().endswith('.yml'):
            return loadAsYml(path)
        elif str(path).lower().endswith('.json'):
            return loadAsJSON(path)
        else:
            raise UnsupportedFileTypeException(path.split('.')[-1])

class UnsupportedFileTypeException(Exception):
    def __init__(self,value="Unsupported File Type Exception"):
        self.value = value
    
    def __str__(self):
        return str(self.value)

class Source():
    def __init__(self,name,priority,file=None,dictionary : dict=None):
        self.name = name
        self.priority = int(priority)
        self.variables = {}
        if file != None:
            self.loadFile(file)
        if dictionary != None:
            self.variables.update(dictionary)

    def loadFile(self,path):
        try:
            variables =loadFile(path)
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
        self.baseSources()
        self.updateVars()
    def getUUID(self):
        return str(uuid.uuid4().hex)

    def addNewSource(self,name,priority,file=None,dictionary=None):
        uuid = self.getUUID()
        if name in self.uuidMappings:
            raise DuplicateSourceException((name,self.uuidMappings[name]),msg = "Source {value[0]} already exists with uuid {value[1]}")
        self.sources[uuid] = Source(name,priority,file,dictionary)
        self.uuidMappings[name] = uuid
        if priority in self.prioritylist:
            self.prioritylist[priority].append(uuid)
        else:
            self.prioritylist[priority] = [uuid]
        self.updateVars()

    def baseSources(self):
        self.addNewSource('USER_VARS',2)
        self.addNewSource('ENV',1,dictionary=self.getEnvironmentVars())

    def addNewFilesToSource(self,name,path):
        if name not in self.uuidMappings:
            raise UnknownSourceException(name)

        uuid = self.uuidMappings[name]
        self.sources[uuid].loadFile(path)
        self.updateVars()

    def runtimeVars(self,key,value):
        uuid = self.uuidMappings['USER_VARS']
        self.sources[uuid].addVar(key,value)
        self.updateVars()
        
    def getEnvironmentVars(self):
        PREFIX = 'ARENA_'
        envvars = dict(os.environ)
        envvars = { k: v for k,v in envvars.items() if str(k).startswith(PREFIX)}
        return envvars

    def updateVars(self):
        priorities = sorted(list(self.prioritylist.keys()),reverse=True)
        for priority in priorities:
            for source in self.prioritylist[priority]:
                self.variables.update(self.sources[source].getVarsDict())

    def getVar(self,key):
        if key not in self.variables:
            raise UndefinedVariableException(key)
        else:
            return self.variables[key]

