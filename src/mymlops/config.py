import yaml
from string import Template
from dotenv import dotenv_values


def read_config():
    with open('mymlops.yml', 'r') as f:
        s = f.read()
    ev = dotenv_values('.env')
    s = Template(s).substitute(ev)
    config = yaml.safe_load(s)
    return config
