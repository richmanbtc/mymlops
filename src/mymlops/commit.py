import os
import datetime
import base64
import gzip
import json
from retry import retry
from .utils import remove_notebook_output
from .startup_logs import do_startup_logs
from .gce_create import gce_create


def do_commit(commit_config, deploy_key, path, artifacts):
    print(f'path {path}')
    assert path[-6:] == '.ipynb'

    with open(path, 'r') as f:
        input = json.load(f)
    input = remove_notebook_output(input)
    input_gzip_base64 = base64.b64encode(gzip.compress(
        json.dumps(input).encode('utf-8'))).decode('ascii')

    repo_config = commit_config['repository']
    repo_branch = repo_config.get('branch', 'master')
    repo_url = repo_config['url']

    output_repo_config = commit_config['output_repository']
    output_repo_branch = output_repo_config.get('branch', 'master')
    output_repo_url = output_repo_config['url']

    now = datetime.datetime.now(datetime.timezone.utc)

    vm_name = 'mymlops-' + now.strftime('%Y%m%d-%H%M%S')
    instance_config = commit_config['instance']
    zone = instance_config['zone']

    command = commit_config['command']
    output_repo_dir = '/root/output_repo'
    commit_path = now.strftime('%Y%m%d_%H%M%S')
    commit_message = f'commit {commit_path}'

    artifacts_path = f"{os.path.dirname(path)}/artifacts"
    copy_artifacts_script = f'''
if [ -d "{artifacts_path}" ]; then
    cp -r "{artifacts_path}" "{output_repo_dir}/{commit_path}"
fi
'''

    script = f'''
cd /root
git clone --recursive -b "{repo_branch}" "{repo_url}" repo
cd repo

echo "{input_gzip_base64}" | base64 -d | gzip -d > "{path}"

{command} "{path}"

git clone --recursive -b "{output_repo_branch}" "{output_repo_url}" "{output_repo_dir}"

mkdir "{output_repo_dir}/{commit_path}"
cp "{path}" "{output_repo_dir}/{commit_path}"
{copy_artifacts_script if artifacts else ''}

(
cd "{output_repo_dir}"
git add "{commit_path}"
git commit -m "{commit_message}"
git push origin "{output_repo_branch}"
)
'''

    gce_create(
        vm_name=vm_name,
        instance_config=instance_config,
        deploy_key=deploy_key,
        startup_script=script,
        delete_after_startup=True
    )

    @retry(tries=20, delay=5)
    def logs():
        do_startup_logs(vm_name, zone)

    logs()
