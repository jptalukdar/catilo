import uuid 
import os
import yaml
import json
from flatten_dict import flatten
import unittest
import jsonpath_ng
import warnings
import requests
"""
Var source priority:
    ENV: 1
    RUNTIME: 2
"""
class Priority():
    ENV = 1
    USER_VARS = 2
    DEFAULT= 10

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
            return __loadAsJSON(path)
        else:
            raise UnsupportedFileTypeException(path.split('.')[-1])

class UnsupportedFileTypeException(Exception):
    def __init__(self,value="Unsupported File Type Exception"):
        self.value = value
    
    def __str__(self):
        return str(self.value)

class Source():
    def __init__(self,name,priority,dictionary : dict=None,store_flat :bool = True):
        self._add_source(name,priority,dictionary,store_flat)

    def _add_source(self,name,priority,dictionary : dict=None,store_flat :bool = True):
        self.name = name
        self.priority = int(priority)
        self.variables = {}
        self.raw_variables = {}
        self.store_flat = store_flat
        if dictionary != None:
            if self.store_flat:
                dictionary = flatten(dictionary, reducer="dot", keep_empty_types=(dict, list,))
            self.variables.update(dictionary)

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

class FileSource(Source):
    def __init__(self,name,priority,file : str=None,store_flat :bool = True):
        dictionary = self.loadFile(file)
        self._add_source(name,priority,dictionary,store_flat)
    
    def loadFile(self,path):
        try:
            variables =__loadFile(path)
            if self.store_flat:
                variables = flatten(variables, reducer="dot", keep_empty_types=(dict, list,))
            return variables
        except Exception:
            Exception('Could not read file, check again')

class URLSource(Source):
    def __init__(self,name,priority,url,filetype='json',store_flat :bool = True):
        self.filetype = filetype
        dictionary = self.loadUrl(url)
        self._add_source(name,priority,json.loads(dictionary),store_flat)

    def loadUrl(self,url):
        response = requests.get(url)
        return response.text
        
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
    def __init__(self,store_flat=True):
        self.store_flat = store_flat
        self.prioritylist = {}
        self.sources = {}
        self.variables = {}
        self.raw_variables = {}
        self.uuidMappings = {}
        self.__add_base_sources()
        self.__update_vars()

    def getUUID(self):
        return str(uuid.uuid4().hex)

    def add_source(self,source: Source):
        uuid = self.getUUID()
        name = source.name
        priority = source.priority
        if name in self.uuidMappings:
            raise DuplicateSourceException((name,self.uuidMappings[name]),msg = "Source {value[0]} already exists with uuid {value[1]}")
        self.sources[uuid] = source
        self.uuidMappings[name] = uuid
        if priority in self.prioritylist:
            self.prioritylist[priority].append(uuid)
        else:
            self.prioritylist[priority] = [uuid]
        self.__update_vars()
    
    def add_new_file_source(self,name,priority,file=None):
        uuid = self.getUUID()
        if name in self.uuidMappings:
            raise DuplicateSourceException((name,self.uuidMappings[name]),msg = "Source {value[0]} already exists with uuid {value[1]}")
        self.sources[uuid] = FileSource(name,priority,file,store_flat=self.store_flat)
        self.uuidMappings[name] = uuid
        if priority in self.prioritylist:
            self.prioritylist[priority].append(uuid)
        else:
            self.prioritylist[priority] = [uuid]
        self.__update_vars()
    
    def add_new_url_source(self,name,priority,url):
        uuid = self.getUUID()
        if name in self.uuidMappings:
            raise DuplicateSourceException((name,self.uuidMappings[name]),msg = "Source {value[0]} already exists with uuid {value[1]}")
        self.sources[uuid] = URLSource(name,priority,url=url,store_flat=self.store_flat)
        self.uuidMappings[name] = uuid
        if priority in self.prioritylist:
            self.prioritylist[priority].append(uuid)
        else:
            self.prioritylist[priority] = [uuid]
        self.__update_vars()

    def add_new_source(self,name,priority,dictionary=None):
        uuid = self.getUUID()
        if name in self.uuidMappings:
            raise DuplicateSourceException((name,self.uuidMappings[name]),msg = "Source {value[0]} already exists with uuid {value[1]}")
        self.sources[uuid] = Source(name,priority,dictionary,store_flat=self.store_flat)
        self.uuidMappings[name] = uuid
        if priority in self.prioritylist:
            self.prioritylist[priority].append(uuid)
        else:
            self.prioritylist[priority] = [uuid]
        self.__update_vars()

    def __add_base_sources(self):
        self.add_new_source('USER_VARS',Priority.USER_VARS)

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

    def jsonquery(self,expression:str):
        if self.store_flat:
            warnings.warn("VariableDirectory:jsonquery => Variables are stored in flat dictionary. Expression may result in incorrect results")
        expr = jsonpath_ng.parse("$."+expression)
        return [match.value for match in expr.find(self.variables)]

class TestStringMethods(unittest.TestCase):

    def test_runtime_priority(self):
        varsource = VariableDirectory()
        varsource.add_new_source("test1",priority=5,dictionary={
            "key" : "val1"
        })
        varsource.add_runtime_var("key","val2")
        self.assertEqual(varsource.get("key"), 'val2')
    def test_flat_dict(self):
        varsource = VariableDirectory()
        varsource.add_new_source("test1",priority=5,dictionary={
            "key" : {
                "key2" : 5
            }
        })
        # print(varsource.variables)
        self.assertEqual(varsource.get("key.key2"), 5)
    
    def test_flat_dict_keys_with_dot(self):
        varsource = VariableDirectory()
        varsource.add_new_source("test1",priority=5,dictionary={
            "key.key1" : 
                {"key2" : 5
            }
            
                
        })
        # print(varsource.variables)
        self.assertEqual(varsource.get("key.key1.key2"), 5)

    def test_dict_keys_with_dot_json_query(self):
        varsource = VariableDirectory(store_flat=False)
        varsource.add_new_source("test1",priority=5,dictionary={
            "key" : {"key2" : 5
            } 
        })
        # print(varsource.variables)
        self.assertEqual(varsource.jsonquery("key.key2"), [5])

    def test_flat_dict_keys_with_dot_json_query(self):
        varsource = VariableDirectory(store_flat=True)
        varsource.add_new_source("test1",priority=5,dictionary={
            "key" : {"key2" : 5
            } 
        })
        # print(varsource.variables)
        self.assertNotEqual(varsource.jsonquery("key.key2"), [5])
    
    def test_url_source(self):
        varsource = VariableDirectory()
        varsource.add_new_url_source("SampleJson",6,"https://filesamples.com/samples/code/json/sample1.json")
        self.assertEqual(varsource.get("color"),"Red")
if __name__ == '__main__':
    unittest.main()