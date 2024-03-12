import os
import datetime
import base64
import gzip
import json
from retry import retry
from .utils import remove_notebook_output
from .startup_logs import do_startup_logs
from .gce_create import gce_create


def do_commit(config, config_name, path):
    print(f'config_name {config_name}')
    print(f'path {path}')

    with open(path, 'r') as f:
        input = remove_notebook_output(json.load(f))
    input_gzip_base64 = base64.b64encode(gzip.compress(
        json.dumps(input).encode('utf-8'))).decode('ascii')

    optipng_ipynb_path = os.path.join(os.path.dirname(__file__), 'optipng_ipynb.js')
    with open(optipng_ipynb_path, 'rb') as f:
        optipng_ipynb_gzip_base64 = base64.b64encode(gzip.compress(f.read())).decode('ascii')

    branch = config['repository'].get('branch', 'master')

    assert path[-6:] == '.ipynb'
    now = datetime.datetime.now(datetime.timezone.utc)
    commit_dir = os.path.join(path[:-6], now.strftime('%Y%m%d_%H%M%S'))

    vm_name = 'mymlops-' + now.strftime('%Y%m%d-%H%M%S')

    commit_config = config['commits'][config_name]
    instance_type_config = config['instance_types'][commit_config['instance_type']]
    zone = instance_type_config['zone']

    command = commit_config['command']
    compression = commit_config.get('compression', False)

    commit_message = f'commit {config_name} {commit_dir}'

    compress_script = f'''
echo "{optipng_ipynb_gzip_base64}" | base64 -d | gzip -d > /tmp/optipng_ipynb.js
docker run \
  -v /tmp/optipng_ipynb.js:/optipng_ipynb.js \
  -v "$PWD/{commit_dir}":/commit_dir \
  node bash -c 'npm install -g optipng-bin && (cat /commit_dir/output.ipynb | node /optipng_ipynb.js > /tmp/a) && mv /tmp/a /commit_dir/output.ipynb'
'''

    script = f'''
mkdir -p "{commit_dir}"
echo "{input_gzip_base64}" | base64 -d | gzip -d > "{commit_dir}/output.ipynb"

{command} "{commit_dir}/output.ipynb"

{compress_script if compression else ''}

git add "{commit_dir}"
git commit -m "{commit_message}"
git stash
git pull --rebase origin "{branch}"
git push origin "{branch}"
'''

    gce_create(
        config=config,
        vm_name=vm_name,
        instance_type=commit_config['instance_type'],
        startup_script=script,
        delete_after_startup=True
    )

    @retry(tries=10, delay=1)
    def logs():
        do_startup_logs(vm_name, zone)

    logs()
