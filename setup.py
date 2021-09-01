
from distutils.core import setup

setup(name='catilo',
      version='0.1',
      description='Manage configuration files from multiple source in python',
      author='Jyotiplaban Talukdar',
      author_email='jyotiplaban@gmail.com',
      url='https://bitbucket.org/jyotiplaban/catilo.git',
      packages=['catilo'],
      install_reqires=[
            "pyyaml" , "flatten_dict"
      ]
     )