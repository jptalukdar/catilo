from catilo.catilo import VariableDirectory
from catilo.catilo import UndefinedVariableException
my_directory = VariableDirectory()
my_directory.add_source("fruitdetails",priority=5,dictionary={
    "fruit": "Apple",
    "size": "Large",
    "color": "Red"
})

my_directory.add_source("fruitdetails2",priority=3,dictionary={
    "fruit": "Mango",
    "size": "Large",
    "color": "Orange"
})

value = my_directory.get("fruit") ## Returns mango 

my_directory.add_url_source("sampleurl",3,"https://raw.githubusercontent.com/jptalukdar/catilo/master/tests_data/json/sample1.json")


my_directory.add_file_source("configfile",priority=6,file="path/to/config.yaml")
my_directory.get("variable")

my_directory.enable_environment_vars()

