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

    branch = config['repository'].get('branch', 'master')

    assert path[-6:] == '.ipynb'
    now = datetime.datetime.now(datetime.timezone.utc)
    commit_dir = os.path.join(path[:-6], now.strftime('%Y%m%d_%H%M%S'))

    vm_name = 'mymlops-' + now.strftime('%Y%m%d-%H%M%S')

    commit_config = config['commits'][config_name]
    instance_type_config = config['instance_types'][commit_config['instance_type']]
    zone = instance_type_config['zone']

    command = commit_config['command']

    commit_message = f'commit {config_name} {commit_dir}'

    script = f'''
mkdir -p "{commit_dir}"
echo "{input_gzip_base64}" | base64 -d | gzip -d > "{commit_dir}/output.ipynb"

{command} "{commit_dir}/output.ipynb"

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
