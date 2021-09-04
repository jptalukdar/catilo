# catilo

Manage configuration files from multiple source in python. Create a variable directory for your configuration sources. 

Directories contain sources and each source has a priority. The lower the priority value, higher is the priority. When you retrieve a variables, it looks into all the sources and retrieve the one with the highest priority. For eg, 
you have added two source - 
* **source1** : json config file - contain default values - priority = 10
* **source2** : url - contains overrides -  priority = 5

It will look into source 2 first, if not found will search in source1 , if then not found will raise "UndefinedVariableException"

## Quickstart

Import the module at the start and define a variable directory. 
```python
from catilo.catilo import VariableDirectory
my_directory = VariableDirectory()
```

For simple dictionaries: 
```python
my_directory.add_source("fruitdetails",priority=5,dictionary={
    "fruit": "Apple",
    "size": "Large",
    "color": "Red"
})
value = my_directory.get("fruit") ## returns "Apple"
```

For yaml/json based files
```python
my_directory.add_file_source("configfile",priority=6,file="path/to/config.yaml")
my_directory.get("variable")
```

For URL's
```python
my_directory.add_url_source("sampleurl",3,"https://raw.githubusercontent.com/jptalukdar/catilo/master/tests/tests_data/json/sample1.json")
value = my_directory.get("fruit") ## returns "Apple"
```

For Environment variables
```python
my_directory.enable_environment_vars(prefix="CATILO_")
value = my_directory.get("CATILO_my_variable")

## If you don't want to strip the prefix during get, use `strip_prefix=True`
my_directory.enable_environment_vars(prefix="CATILO_",strip_prefix=True)
value = my_directory.get("my_variable")
```


## Features

1. Allows you to store multiple configuration files with priority value.
2. Support for the following sources
    1. python dictionaries 
    1. yaml files
    1. json files
    1. url (get method, json format)
    1. Environment variables
3. Ability to add custom sources
4. Stores config in flat_dictionary (can be overriden) for '.' notation access
5. Ability to add variables in runtime
    1. Add as default variable
    1. Add as normal variable
6. Output multiple sources into a single json or yaml file