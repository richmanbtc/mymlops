import os
import re
import json
import subprocess
import logging
from git import Repo


logger = logging.getLogger(__name__)

def do_status(commit_config):
    metadata_list = {}

    # fetch gce status
    options = [
        'gcloud',
        'compute',
        'instances',
        'list',
        '--filter=labels.mymlops:*',
        '--format=json',
    ]
    res = subprocess.check_output(options)
    res = json.loads(res)
    for inst in res:
        prefix = 'mymlops-'
        metadata = {
            item['key'][len(prefix):]: item['value']
            for item in inst['metadata']['items']
            if item['key'].startswith(prefix)
        }
        if 'artifacts' in metadata:
            metadata['artifacts'] = metadata['artifacts'] == 'true'
        metadata['status'] = 'processing'
        metadata_list[metadata['commit']] = metadata

    # fetch output repo status
    repo_url = commit_config['output_repository']['url']
    repo_branch = commit_config['output_repository'].get('branch', 'master')
    sanitized_repo = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f\t\n\r ]+', '_', f'{repo_url}{repo_branch}')
    work_dir = f'/tmp/mymlops_status/{sanitized_repo}'
    deploy_key = os.path.abspath(commit_config['output_repository']['deploy_key'])
    git_ssh_cmd = f'ssh -o "IdentitiesOnly=yes" -i {deploy_key} -F /dev/null'
    try:
        repo = Repo(work_dir)
    except:
        os.makedirs(os.path.dirname(work_dir), exist_ok=True)
        repo_url = commit_config['output_repository']['url']
        Repo.clone_from(
            repo_url, work_dir,
            branch=repo_branch,
            env=dict(GIT_SSH_COMMAND=git_ssh_cmd)
        )
        repo = None
    if repo is not None:
        with repo.git.custom_environment(GIT_SSH_COMMAND=git_ssh_cmd):
            repo.remotes.origin.pull()

    for commit in os.listdir(work_dir):
        commit_path = os.path.join(work_dir, commit)
        if not os.path.isdir(commit_path):
            continue

        try:
            notebook_name = next(name for name in os.listdir(commit_path) if name.endswith('.ipynb'))
        except StopIteration:
            continue

        try:
            metadata_path = os.path.join(commit_path, 'metadata.json')
            with open(metadata_path, 'r') as f:
                metadata = f.read()
            metadata = json.loads(metadata)
        except Exception as err:
            logger.warning(f'failed to load metadata: {err}')
            metadata = {}

        notebook_path = os.path.join(commit_path, notebook_name)
        metadata['status'] = 'failed' if _notebook_has_error(notebook_path) else 'succeeded'
        metadata['commit'] = commit
        metadata['notebook'] = notebook_name
        metadata_list[metadata['commit']] = metadata

    metadata_list = sorted(metadata_list.values(), key=lambda x: x['commit'])
    print(json.dumps(metadata_list, indent=4, sort_keys=True))


def _notebook_has_error(notebook_path):
    with open(notebook_path, 'r') as f:
        notebook = f.read()
    notebook = json.loads(notebook)
    for cell in notebook['cells']:
        for output in cell.get('outputs', []):
            if output['output_type'] == 'error':
                return True
    return False
