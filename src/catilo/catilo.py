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
    DEFAULT= 100

def _loadAsYml(path):
        with open(path,'r') as fp:
            data = yaml.safe_load(fp)
        return data

def _loadAsJSON(path):
        with open(path,'r') as fp:
            data = json.loads(fp.read())
        return data

def _load_file(path):
        if str(path).lower().endswith('.yml') or str(path).lower().endswith('.yaml'):
            return _loadAsYml(path)
        elif str(path).lower().endswith('.json'):
            return _loadAsJSON(path)
        else:
            raise UnsupportedFileTypeException(path.split('.')[-1])

def _dump_json(data,path):
    with open(path,'w') as fp:
        fp.write(json.dumps(data,indent=4))

def _dump_yaml(data,path):
    with open(path,'w') as fp:
        yaml.dump(data,fp)
class UnsupportedFileTypeException(Exception):
    def __init__(self,value="Unsupported File Type Exception",msg=None):
        self.value = value
        if msg is not None:
            self.msg = msg
        else:
            self.msg = f"Unsupported File format - [{value}]"

    def __str__(self):
        return self.msg

    def __str__(self):
        return str(self.value) + " is not supported. Only [yml,yaml,json] supported"

class Source():
    def __init__(self,name:str,priority:int,dictionary : dict,store_flat :bool = True):
        """Initialize a variable source

        Args:
            name (str): [description]
            priority (int): [description]
            dictionary (dict, optional): [description]. Defaults to None.
            store_flat (bool, optional): [description]. Defaults to True.
        """
        self._add_source(name,priority,dictionary,store_flat)

    def _add_source(self,name:str,priority:int,dictionary : dict=None,store_flat :bool = True):
        self.name = name
        self.priority = int(priority)
        self.variables = {}
        self.raw_variables = {}
        self.store_flat = store_flat
        if dictionary is not None:
            if self.store_flat:
                dictionary = flatten(dictionary, reducer="dot", keep_empty_types=(dict, list,))
            self.variables.update(dictionary)

    def add_var(self,key:str,value:any):
        """ Add a variable to source

        Args:
            key (str): [a key for your variable]
            value (any): [value for the corresponding variable]
        """
        self.variables[key] = value
    
    def get_var(self,key):
        if key not in self.variables:
            raise UndefinedVariableException(key)
        else:
            return self.variables[key]
    
    def get_vars_dict(self):
        return self.variables

    def get_priority(self):
        return self.priority
    
    def set_priority(self,priority):
        try:
            priority = int(priority)
        except Exception:
            raise IncorrectPriorityException(priority)

class FileSource(Source):
    def __init__(self,name,priority,file : str=None,store_flat :bool = True):
        self.store_flat = store_flat
        dictionary = self.load_file(file)
        self._add_source(name,priority,dictionary,store_flat)
    
    def load_file(self,path):
        try:
            variables =_load_file(path)
            if self.store_flat:
                variables = flatten(variables, reducer="dot", keep_empty_types=(dict, list,))
            return variables
        except FileNotFoundError as ex:
            raise Exception('Could not find file, check again')

class URLSource(Source):
    def __init__(self,name,priority,url,filetype='json',store_flat :bool = True):
        self.filetype = filetype
        self.store_flat = store_flat
        dictionary = self.load_url(url)
        try:
            dictionary = json.loads(dictionary)
        except json.decoder.JSONDecodeError:
            raise UnsupportedFileTypeException(f"The data received from url is not in json format. Please check again. URL: {url}")
        self._add_source(name,priority,dictionary,store_flat)

    def load_url(self,url):
        response = requests.get(url)
        return response.text
        
class BaseException(Exception):
    msg = "{value}"

    def __init__(self,value,msg=None):
        self.value = value
        if msg is not None:
            self.msg = msg
        
    def __str__(self):
        return self.msg
        
class IncorrectPriorityException(BaseException):
    msg = "Incorrect Priority Set {value}"
    def __init__(self,value,msg=None):
        self.value = value
        if msg is not None:
            self.msg = msg
        else:
            self.msg = f"Incorrect Priority Set {value}"
    def __str__(self):
        return self.msg 

class UndefinedVariableException(BaseException):
    msg = "{value} not defined"
    def __init__(self,value,msg=None):
        self.value = value
        if msg is not None:
            self.msg = msg
        else:
            self.msg = f"Variable - [{value}] is not defined"
    def __str__(self):
        return self.msg

class DuplicateSourceException(BaseException):
    msg = "Source {value} already exists"
    def __init__(self,value,msg=None):
        self.value = value
        if msg is not None:
            self.msg = msg
        else:
            self.msg = f"Source {value} already exists"

    def __str__(self):
        return self.msg
class UnknownSourceException(BaseException):
    msg = "Exception adding vars to unknown source [{value}]. PS: Source names are case sensitive"
    def __init__(self,value,msg=None):
        self.value = value
        if msg is not None:
            self.msg = msg
        else:
            self.msg = f"Exception adding vars to unknown source [{value}]. PS: Source names are case sensitive"
    def __str__(self):
        return self.msg
class UnknownOutputExtensionException(BaseException):
    msg = "Found Unknown extension while saving directory: [{value}]"
    def __init__(self,value,msg=None):
        self.value = value
        if msg is not None:
            self.msg = msg
        else:
            self.msg = f"Found Unknown extension while saving directory: [{value}]"
        
    def __str__(self):
        return self.msg
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

    def __generate_uuid(self):
        return str(uuid.uuid4().hex)

    def add_custom_source(self,source: Source):
        """add_custom_source: Allows you to add custom source.

        Args:
            source (Source): [Any object inheriting catilo.Source class]

        Raises:
            DuplicateSourceException: [Raises DuplicateSourceException if same source name is added previously]
        """
        uuid = self.__generate_uuid()
        name = source.name
        priority = source.priority
        if name in self.uuidMappings:
            raise DuplicateSourceException((name,self.uuidMappings[name]),msg = f"Source {name} already exists with uuid {self.uuidMappings[name]}")
        self.sources[uuid] = source
        self.uuidMappings[name] = uuid
        if priority in self.prioritylist:
            self.prioritylist[priority].append(uuid)
        else:
            self.prioritylist[priority] = [uuid]
        self.__update_vars()
    
    def add_file_source(self,name:str,priority:int,file:str):
        """Allows you to add a yaml or json file as source.

        Args:
            name (str): [unique name for your source]
            priority (int): [set priority of the source]
            file (str): [a path containing json or yaml file]

        Raises:
            DuplicateSourceException: [Raises DuplicateSourceException if same source name is added previously]
        """
        uuid = self.__generate_uuid()
        if name in self.uuidMappings:
            raise DuplicateSourceException((name,self.uuidMappings[name]),msg = f"Source {name} already exists with uuid {self.uuidMappings[name]}")
        self.sources[uuid] = FileSource(name,priority,file,store_flat=self.store_flat)
        self.uuidMappings[name] = uuid
        if priority in self.prioritylist:
            self.prioritylist[priority].append(uuid)
        else:
            self.prioritylist[priority] = [uuid]
        self.__update_vars()
    
    def add_url_source(self,name:str,priority:int,url:str):
        """Allows you to add an url returning json data as source.

        Args:
            name (str): [unique name for your source]
            priority (int): [set priority of the source]
            url (str): [description]

        Raises:
            DuplicateSourceException: [description]
        """
        uuid = self.__generate_uuid()
        if name in self.uuidMappings:
            raise DuplicateSourceException((name,self.uuidMappings[name]),msg = f"Source {name} already exists with uuid {self.uuidMappings[name]}")
        self.sources[uuid] = URLSource(name,priority,url=url,store_flat=self.store_flat)
        self.uuidMappings[name] = uuid
        if priority in self.prioritylist:
            self.prioritylist[priority].append(uuid)
        else:
            self.prioritylist[priority] = [uuid]
        self.__update_vars()

    def add_source(self,name:str,priority:str,dictionary:dict):
        """Allows you to add a dictionary as source

        Args:
            name (str): [unique name for your source]
            priority (int): [set priority of the source]
            dictionary (dict): [description]

        Raises:
            DuplicateSourceException: [description]
        """
        uuid = self.__generate_uuid()
        if name in self.uuidMappings:
            raise DuplicateSourceException((name,self.uuidMappings[name]),msg = f"Source '{name}' already exists with uuid {self.uuidMappings[name]}")
        self.sources[uuid] = Source(name,priority,dictionary,store_flat=self.store_flat)
        self.uuidMappings[name] = uuid
        if priority in self.prioritylist:
            self.prioritylist[priority].append(uuid)
        else:
            self.prioritylist[priority] = [uuid]
        self.__update_vars()

    def __add_base_sources(self):
        self.add_source('USER_VARS',Priority.USER_VARS,{})
        self.add_source("DEFAULT",Priority.DEFAULT,{})

    # def add_new_files_to_source(self,name,path):
    #     if name not in self.uuidMappings:
    #         raise UnknownSourceException(name)

    #     uuid = self.uuidMappings[name]
    #     self.sources[uuid].loadFile(path)
    #     self.__update_vars()

    def add_runtime_var(self,key:str,value:any):
        """Allows you to add variables in runtime. If Variable exist will replace

        Args:
            key (str): [variable name]
            value (any): [variable value]
        """
        uuid = self.uuidMappings['USER_VARS']
        self.sources[uuid].add_var(key,value)
        self.__update_vars()
    
    def add_default_var(self,key:str,value:any):
        """Allows you to add variables in runtime. If variable exist will replace

        Args:
            key (str): [description]
            value (any): [description]
        """
        uuid = self.uuidMappings['DEFAULT']
        self.sources[uuid].add_var(key,value)
        self.__update_vars()
    
    def enable_environment_vars(self,prefix:str="CATILO_",strip:bool=False):
        """Enables variable retrieval from Environment variables

        Args:
            prefix (str, optional): [A prefix value for bulk retrieval]. Defaults to "CATILO_".
            strip (bool, optional): [strip removes the prefix during storages. Eg, CATILO_VAR would be stored as VAR for prefix "CATILO_"]. Defaults to False.

        Raises:
            DuplicateSourceException: [Raises if same prefix is added twice]
        """
        identifier = "ENV_" + prefix
        if identifier in self.sources:
            raise DuplicateSourceException(prefix, msg=f"Environment source for prefix {prefix} is already present. Use refresh_env_vars(prefix) to refresh the vars")

        varsdict = self.__get_environment_vars(prefix)
        if strip:
            varsdict = { k.strip(prefix):v for k,v in varsdict.items()}
        self.add_source(identifier,priority=Priority.ENV,dictionary=varsdict)


    def __get_environment_vars(self,prefix="CATILO_"):
        envvars = dict(os.environ)
        envvars = { k: v for k,v in envvars.items() if str(k).startswith("CATILO_")}
        return envvars

    def __update_vars(self):
        priorities = sorted(list(self.prioritylist.keys()),reverse=True)
        for priority in priorities:
            for source in self.prioritylist[priority]:
                self.variables.update(self.sources[source].get_vars_dict())
        
    def get(self,key:str):
        """Retrieves a variable name

        Args:
            key (str): [variable name]

        Raises:
            UndefinedVariableException: [Raises if variable is not found]

        Returns:
            [any]: [value if found for the variable]
        """
        if key not in self.variables:
            raise UndefinedVariableException(key)
        else:
            return self.variables[key]

    def jsonquery(self,expression:str):
        """Allows you to query data using jsonpath-ng syntax. Use only with not-flat dictionary.


        Args:
            expression (str): [jsonpath expression]

        Returns:
            [list]: [value found using json query]
        """
        if self.store_flat:
            warnings.warn("VariableDirectory:jsonquery => Variables are stored in flat dictionary. Expression may result in incorrect results")
        expr = jsonpath_ng.parse("$."+expression)
        return [match.value for match in expr.find(self.variables)]

    def save_directory(self,path:str,extension:str="json"):
        if extension in ["json"]:
            _dump_json(self.variables,path)
        elif extension in ["yml","yaml"]:
            _dump_yaml(self.variables,path)
        else:
            raise UnsupportedFileTypeException(extension,msg="Unsupported extension [{extension}] for output. Only [json,yml,yaml] supported")
class TestStringMethods(unittest.TestCase):

    def test_runtime_priority(self):
        varsource = VariableDirectory()
        varsource.add_source("test1",priority=5,dictionary={
            "key" : "val1"
        })
        varsource.add_runtime_var("key","val2")
        self.assertEqual(varsource.get("key"), 'val2')
    def test_flat_dict(self):
        varsource = VariableDirectory()
        varsource.add_source("test1",priority=5,dictionary={
            "key" : {
                "key2" : 5
            }
        })
        self.assertEqual(varsource.get("key.key2"), 5)
    
    def test_flat_dict_keys_with_dot(self):
        varsource = VariableDirectory()
        varsource.add_source("test1",priority=5,dictionary={
            "key.key1" : 
                {"key2" : 5
            }
            
                
        })
        self.assertEqual(varsource.get("key.key1.key2"), 5)

    def test_dict_keys_with_dot_json_query(self):
        varsource = VariableDirectory(store_flat=False)
        varsource.add_source("test1",priority=5,dictionary={
            "key" : {"key2" : 5
            } 
        })
        self.assertEqual(varsource.jsonquery("key.key2"), [5])

    def test_flat_dict_keys_with_dot_json_query(self):
        varsource = VariableDirectory(store_flat=True)
        varsource.add_source("test1",priority=5,dictionary={
            "key" : {"key2" : 5
            } 
        })
        self.assertNotEqual(varsource.jsonquery("key.key2"), [5])
    
    def test_url_source(self):
        varsource = VariableDirectory()
        varsource.add_url_source("SampleJson",6,"https://raw.githubusercontent.com/jptalukdar/catilo/master/tests/tests_data/json/sample1.json")
        self.assertEqual(varsource.get("color"),"Red")
    
    def test_file_source(self):
        varsource = VariableDirectory()
        varsource.add_source("input",5,{
            "fruit" : "apple",
            "colour" : "red"
        })
        varsource.save_directory("output.json")

        varsource2 = VariableDirectory()
        varsource2.add_file_source("test",3,"output.json")
        self.assertEqual(varsource2.get("fruit"),"apple")
        
    def test_url_source(self):
        with self.assertRaises(UnsupportedFileTypeException):
            varsource = VariableDirectory()
            varsource.add_url_source("SampleJson",6,"https://raw.githubusercontent.com/jptalukdar/catilo/master/tests/tests_data/json/sample-non-existent.json")

    def test_duplicate_source(self):
        with self.assertRaises(DuplicateSourceException):
            varsource = VariableDirectory()
            varsource.add_source("SampleJson",6,{})
            varsource.add_source("SampleJson",6,{})

    def test_undefined_variables(self):    
        with self.assertRaises(UndefinedVariableException):
            varsource = VariableDirectory()
            varsource.add_source("SampleJson",6,{})
            varsource.get("MyKey")
    
    def test_non_supported_extension(self):    
        with self.assertRaises(UnsupportedFileTypeException):
            varsource = VariableDirectory()
            varsource.add_file_source("SampleJson",6,"test.xml")

    def test_save_json(self):
        varsource = VariableDirectory(store_flat=True)
        varsource.add_source("test1",priority=5,dictionary={
            "key" : {"key2" : 5
            } 
        })
        varsource.save_directory("output.json")
    def test_save_unknown(self):
        with self.assertRaises(UnsupportedFileTypeException):
            varsource = VariableDirectory(store_flat=True)
            varsource.add_source("test1",priority=5,dictionary={
                "key" : {"key2" : 5
                } 
            })
            varsource.save_directory("output.xml",extension="xml")

    def test_save_yaml(self):
        varsource = VariableDirectory(store_flat=True)
        varsource.add_source("test1",priority=5,dictionary={
            "key" : {"key2" : 5
            } 
        })
        varsource.save_directory("output.yml",extension="yml")
if __name__ == '__main__':
    unittest.main()