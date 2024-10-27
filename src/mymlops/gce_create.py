import os
import tempfile
from .consts import GITHUB_KNOWN_HOSTS
from .utils import run_redirect


def gce_create(vm_name, instance_config, startup_script='', delete_after_startup=False):
    print(f'gce_create vm_name {vm_name} instance_config {instance_config}')

    zone = instance_config['zone']
    accelerator_type = instance_config.get('accelerator_type')
    machine_type = instance_config.get('machine_type')
    snapshot = instance_config['snapshot']

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

{cleanup_script if delete_after_startup else ''}

export HOME=/root

mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "{GITHUB_KNOWN_HOSTS}" > ~/.ssh/known_hosts
export GIT_SSH_COMMAND="ssh -o "UserKnownHostsFile=/root/.ssh/known_hosts" -i ~/.ssh/id_rsa -F /dev/null"

git config --global user.email "you@example.com"
git config --global user.name "Your Name"

apt-get update
apt-get install -y docker-compose-plugin

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
            f'--metadata-from-file=startup-script={script_path}',
            f'--zone={zone}',
            f'--accelerator=type={accelerator_type},count=1' if accelerator_type is not None else None,
            f'--machine-type={machine_type}' if machine_type is not None else None,
            '--scopes=default,bigquery,compute-rw',
            '--provisioning-model=SPOT',
            f'--create-disk=auto-delete=yes,boot=yes,device-name=mymlops,source-snapshot={snapshot},mode=rw,size=100,type=pd-ssd',
        ]

        options = [x for x in options if x is not None]
        run_redirect(options)
