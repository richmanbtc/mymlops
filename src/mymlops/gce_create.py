import os
import tempfile
from .consts import GITHUB_KNOWN_HOSTS
from .utils import run_redirect


def gce_create(config, vm_name, instance_type, startup_script='', delete_after_startup=False):
    print(f'gce_create instance_type {instance_type}')

    repo_url = config['repository']['remote']
    with open(config['repository']['key'], 'r') as f:
        deploy_key = f.read()

    branch = config['repository'].get('branch', 'master')

    instance_type_config = config['instance_types'][instance_type]
    instance_template = instance_type_config['instance_template']
    zone = instance_type_config['zone']
    accelerator_type = instance_type_config.get('accelerator_type')
    machine_type = instance_type_config.get('machine_type')

    # https://qiita.com/relu/items/6a3bb240084948f4a578
    cleanup_script = '''
function cleanup {
    NAME=$(curl metadata.google.internal/computeMetadata/v1/instance/name -H "Metadata-Flavor: Google")
    ZONE=$(curl metadata.google.internal/computeMetadata/v1/instance/zone -H "Metadata-Flavor: Google" | cut -d/ -f4)
    docker run google/cloud-sdk gcloud compute instances delete $NAME --zone=$ZONE --quiet
}
trap cleanup EXIT
'''

    gpu_script = '''
cos-extensions install gpu
mount --bind /var/lib/nvidia /var/lib/nvidia
mount -o remount,exec /var/lib/nvidia
'''

    script = f'''#!/bin/bash
set -ex

{cleanup_script if delete_after_startup else ''}

export HOME=/home/work
mkdir -p /home/work

mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "{deploy_key}" > ~/.ssh/id_rsa
chmod 400 ~/.ssh/id_rsa
echo "{GITHUB_KNOWN_HOSTS}" > ~/.ssh/known_hosts
export GIT_SSH_COMMAND="ssh -o "UserKnownHostsFile=/home/work/.ssh/known_hosts" -i /home/work/.ssh/id_rsa -F /dev/null"

git config --global user.email "you@example.com"
git config --global user.name "Your Name"

shopt -s expand_aliases
alias docker-compose='docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD:$PWD" \
    -w="$PWD" \
    docker/compose:1.24.0'

{gpu_script if accelerator_type is not None else ''}

cd /home/work
git clone --recursive -b "{branch}" "{repo_url}" repo

cd repo

{startup_script}
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
            f'--accelerator=type={accelerator_type},count=1' if accelerator_type is not None else None,
            f'--machine-type={machine_type}' if machine_type is not None else None,
            # '--scopes=compute-rw',
            # '--provisioning-model=SPOT',
            # '--max-run-duration=24h',
            # '--instance-termination-action=DELETE',
        ]
        options = [x for x in options if x is not None]
        run_redirect(options)
