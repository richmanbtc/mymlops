import base64
import gzip
import os
import tempfile
from .consts import GITHUB_KNOWN_HOSTS
from .utils import run_redirect


def gce_create(vm_name, zone, machine_type, accelerator, snapshot, label,
               metadata={}, startup_script='', delete_after_startup=False):
    print(
        f'gce_create vm_name {vm_name} zone {zone} '
        f'machine_type {machine_type} accelerator {accelerator} '
        f'snapshot {snapshot} label {label}'
    )

    with open(os.path.join(os.path.dirname(__file__), 'idle_shutdown.sh'), 'r') as f:
        idle_shutdown_script = f.read()
    idle_shutdown_script_gzip_base64 = base64.b64encode(gzip.compress(
        idle_shutdown_script.encode('utf-8'))).decode('ascii')

    script = f'''#!/bin/bash
set -ex

echo "{idle_shutdown_script_gzip_base64}" | base64 -d | gzip -d > /usr/local/bin/idle_shutdown.sh
chmod +x /usr/local/bin/idle_shutdown.sh
/usr/local/bin/idle_shutdown.sh &

STARTUP_FLAG_FILE="/etc/first_boot_completed"
if [ -f "$STARTUP_FLAG_FILE" ]; then
    echo "Startup script has already run. Skipping."
    exit 0
fi
echo "Running startup script for the first time..."

{_cleanup_script if delete_after_startup else ''}

export HOME=/root

mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "{GITHUB_KNOWN_HOSTS}" > ~/.ssh/known_hosts
export GIT_SSH_COMMAND="ssh -o "UserKnownHostsFile=/root/.ssh/known_hosts" -i ~/.ssh/id_rsa -F /dev/null"

git config --global user.email "you@example.com"
git config --global user.name "Your Name"

echo "source /usr/share/bash-completion/completions/git" >> ~/.bashrc

{startup_script}

touch "$STARTUP_FLAG_FILE"
echo "Startup script execution completed."
'''

    with tempfile.TemporaryDirectory() as dir:
        script_path = os.path.join(dir, 'script.sh')
        with open(script_path, "w") as f:
            f.write(script)

        def to_string(value):
            if isinstance(value, bool):
                return "true" if value else "false"
            return str(value)

        metadata_options = ','.join([f'{k}={to_string(v)}' for k, v in metadata.items() if v is not None])

        options = [
            'gcloud',
            'compute',
            'instances',
            'create',
            vm_name,
            f'--metadata-from-file=startup-script={script_path}',
            f'--metadata={metadata_options}' if metadata else None,
            f'--zone={zone}',
            f'--accelerator=type={accelerator},count=1' if accelerator is not None else None,
            f'--machine-type={machine_type}' if machine_type is not None else None,
            '--scopes=default,bigquery,compute-rw',
            '--provisioning-model=SPOT',
            f'--create-disk=auto-delete=yes,boot=yes,device-name=mymlops,source-snapshot={snapshot},mode=rw,size=100,type=pd-ssd',
            f'--labels=mymlops={label}',
        ]

        options = [x for x in options if x is not None]
        run_redirect(options)


# https://qiita.com/relu/items/6a3bb240084948f4a578
_cleanup_script = '''
function cleanup {
    NAME=$(curl metadata.google.internal/computeMetadata/v1/instance/name -H "Metadata-Flavor: Google")
    ZONE=$(curl metadata.google.internal/computeMetadata/v1/instance/zone -H "Metadata-Flavor: Google" | cut -d/ -f4)
    docker run google/cloud-sdk gcloud compute instances delete $NAME --zone=$ZONE --quiet
}
trap cleanup EXIT
'''
