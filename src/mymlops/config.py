import os
import json
import yaml
from string import Template
from dotenv import dotenv_values
from jsonschema import validate


def read_config():
    with open('mymlops.yml', 'r') as f:
        s = f.read()
    ev = dotenv_values('.env')
    s = Template(s).substitute(ev)
    config = yaml.safe_load(s)
    _validate_config(config)
    return config


def _validate_config(config):
    with open(os.path.join(os.path.dirname(__file__), 'config_schema.json'), 'r') as f:
        schema = f.read()
    schema = json.loads(schema)
    validate(config, schema)
