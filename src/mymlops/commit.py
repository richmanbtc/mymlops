import os
import datetime
import tempfile
import base64
import gzip
from retry import retry
from .consts import GITHUB_KNOWN_HOSTS
from .utils import run_redirect
from .startup_logs import do_startup_logs


def do_commit(config, config_name, path):
    print(f'config_name {config_name}')
    print(f'path {path}')

    repo_url = config['repository']['remote']
    with open(config['repository']['key'], 'r') as f:
        deploy_key = f.read()

    with open(path, 'rb') as f:
        input_gzip_base64 = base64.b64encode(gzip.compress(f.read())).decode('ascii')

    branch = config['repository'].get('branch', 'master')

    assert path[-6:] == '.ipynb'
    now = datetime.datetime.now(datetime.timezone.utc)
    commit_dir = os.path.join(path[:-6], now.strftime('%Y%m%d_%H%M%S'))

    vm_name = 'mymlops-' + now.strftime('%Y%m%d-%H%M%S')

    commit_config = config['commits'][config_name]
    instance_type = config['instance_types'][commit_config['instance_type']]
    instance_template = instance_type['instance_template']
    zone = instance_type['zone']

    command = commit_config['command']

    commit_message = f'commit {config_name} {commit_dir}'

    # https://qiita.com/relu/items/6a3bb240084948f4a578
    cleanup_script = '''
function cleanup {
    NAME=$(curl metadata.google.internal/computeMetadata/v1/instance/name -H "Metadata-Flavor: Google")
    ZONE=$(curl metadata.google.internal/computeMetadata/v1/instance/zone -H "Metadata-Flavor: Google" | cut -d/ -f4)
    docker run google/cloud-sdk gcloud compute instances delete $NAME --zone=$ZONE --quiet
}
trap cleanup EXIT
'''

    script = f'''#!/bin/bash
set -ex

{cleanup_script}

export HOME=/tmp
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "{deploy_key}" > ~/.ssh/id_rsa
chmod 400 ~/.ssh/id_rsa
echo "{GITHUB_KNOWN_HOSTS}" > ~/.ssh/known_hosts
export GIT_SSH_COMMAND="ssh -o "UserKnownHostsFile=/tmp/.ssh/known_hosts" -i /tmp/.ssh/id_rsa -F /dev/null"

git config --global user.email "you@example.com"
git config --global user.name "Your Name"

shopt -s expand_aliases
alias docker-compose='docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD:$PWD" \
    -w="$PWD" \
    docker/compose:1.24.0'

cd /tmp
git clone --recursive -b "{branch}" "{repo_url}" repo

cd repo
mkdir -p "{commit_dir}"
echo "{input_gzip_base64}" | base64 -d | gzip -d > "{commit_dir}/output.ipynb"

{command} "{commit_dir}/output.ipynb"

git add "{commit_dir}"
git commit -m "{commit_message}"
git stash
git pull --rebase origin "{branch}"
git push origin "{branch}"
'''

    with tempfile.TemporaryDirectory() as dir:
        script_path = os.path.join(dir, 'script.sh')
        with open(script_path, "w") as f:
            f.write(script)

        options = [
            'gcloud',
            'compute',
            'instances',
            'create',
            vm_name,
            f'--source-instance-template={instance_template}',
            f'--metadata-from-file=startup-script={script_path}',
            f'--zone={zone}',
            '--scopes=compute-rw',
            # '--provisioning-model=SPOT',
            # '--max-run-duration=24h',
            # '--instance-termination-action=DELETE',
        ]
        run_redirect(options)

    @retry(tries=5, delay=1)
    def logs():
        do_startup_logs(vm_name, zone)

    logs()
