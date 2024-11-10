import os
import datetime
import base64
import gzip
import json
import subprocess
from retry import retry
from .utils import remove_notebook_output
from .startup_logs import do_startup_logs
from .gce_create import gce_create
from .gce_zones import gce_select_zone, gce_get_zone


def do_commit(commit_config, path, artifacts, notes, instance):
    print(f'path {path}')
    assert path[-6:] == '.ipynb'

    if instance:
        zone = gce_get_zone(instance)
        options = [
            'gcloud',
            'compute',
            'ssh',
            f'root@{instance}',
            f'--zone={zone}',
            f'--command=cat /root/repo/{path}',
        ]
        input = subprocess.check_output(options)
    else:
        with open(path, 'r') as f:
            input = f.read()

    input = json.loads(input)
    input = remove_notebook_output(input)
    input_gzip_base64 = base64.b64encode(gzip.compress(
        json.dumps(input).encode('utf-8'))).decode('ascii')

    repo_config = commit_config['repository']
    repo_branch = repo_config.get('branch', 'master')
    repo_url = repo_config['url']
    with open(repo_config['deploy_key'], 'r') as f:
        repo_deploy_key = f.read()

    output_repo_config = commit_config['output_repository']
    output_repo_branch = output_repo_config.get('branch', 'master')
    output_repo_url = output_repo_config['url']
    with open(output_repo_config['deploy_key'], 'r') as f:
        output_repo_deploy_key = f.read()

    now = datetime.datetime.now(datetime.timezone.utc)

    vm_name = 'mymlops-' + now.strftime('%Y%m%d-%H%M%S')
    instance_config = commit_config['instance']
    zones = instance_config['zones']
    zone = gce_select_zone(zones)

    command = commit_config['command']
    output_repo_dir = '/root/output_repo'
    commit_path = now.strftime('%Y%m%d_%H%M%S')
    commit_message = f'commit {commit_path}'

    metadata = {
        'commit': commit_path,
        'notebook': os.path.basename(path),
        'repository': repo_url,
        'branch': repo_branch,
        'artifacts': artifacts,
        'notes': notes if notes else None,
        'accelerator': instance_config.get('accelerator'),
    }
    metadata_gzip_base64 = base64.b64encode(gzip.compress(
        json.dumps(metadata, indent=4, sort_keys=True).encode('utf-8'))).decode('ascii')

    artifacts_path = f"{os.path.dirname(path)}/artifacts"
    copy_artifacts_script = f'''
if [ -d "{artifacts_path}" ]; then
    cp -r "{artifacts_path}" "{output_repo_dir}/{commit_path}"
fi
'''

    script = f'''
cd /root
echo "{repo_deploy_key}" > ~/.ssh/id_rsa
chmod 400 ~/.ssh/id_rsa
git clone --recursive -b "{repo_branch}" "{repo_url}" repo
cd repo

echo "{input_gzip_base64}" | base64 -d | gzip -d > "{path}"

{command} "{path}"

rm ~/.ssh/id_rsa
echo "{output_repo_deploy_key}" > ~/.ssh/id_rsa
chmod 400 ~/.ssh/id_rsa
git clone --recursive -b "{output_repo_branch}" "{output_repo_url}" "{output_repo_dir}"

mkdir "{output_repo_dir}/{commit_path}"
cp "{path}" "{output_repo_dir}/{commit_path}"
{copy_artifacts_script if artifacts else ''}
echo "{metadata_gzip_base64}" | base64 -d | gzip -d > "{output_repo_dir}/{commit_path}/metadata.json"

(
cd "{output_repo_dir}"
git add "{commit_path}"
git commit -m "{commit_message}"
git push origin "{output_repo_branch}"
)
'''

    gce_metadata = {
        f'mymlops-{k}': v
        for k, v in metadata.items()
    }

    gce_create(
        vm_name=vm_name,
        zone=zone,
        accelerator=instance_config.get('accelerator'),
        machine_type=instance_config.get('machine_type'),
        snapshot=instance_config['snapshot'],
        label='commit',
        metadata=gce_metadata,
        startup_script=script,
        delete_after_startup=True
    )

    @retry(tries=20, delay=5)
    def logs():
        do_startup_logs(vm_name)

    logs()
