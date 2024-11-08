import os
import re
import json
import subprocess
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from git import Repo
from tabulate import tabulate


logger = logging.getLogger(__name__)

def do_status(commit_config, format, server):
    if server:
        _start_server(commit_config)
        return

    metadata_list = _get_metadata_list(commit_config)

    if format == 'json':
        print(json.dumps(metadata_list, indent=4, sort_keys=True))
    else:
        headers = ['status', 'commit', 'notebook', 'notes']
        data = [
            [metadata.get(h) for h in headers]
            for metadata in metadata_list
        ]
        print(tabulate(data, headers, tablefmt="plain"))


def _start_server(commit_config):
    class CustomHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                with open(os.path.join(os.path.dirname(__file__), 'status_server.html'), 'rb') as f:
                    content = f.read()
                self.wfile.write(content)
            elif self.path == '/favicon.png':
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                with open(os.path.join(os.path.dirname(__file__), 'blake-verdoorn-cssvEZacHvQ-unsplash-resized.png'), 'rb') as f:
                    content = f.read()
                self.wfile.write(content)
            elif self.path == '/data.json':
                self.send_response(200)
                self.send_header('Content-type', 'text/json')
                self.end_headers()
                metadata_list = _get_metadata_list(commit_config)
                data = {
                    'commit_config': commit_config,
                    'metadata_list': metadata_list,
                }
                self.wfile.write(json.dumps(data, indent=4, sort_keys=True).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 Not Found")

    host = "0.0.0.0"
    port = 8000
    server = HTTPServer((host, port), CustomHandler)
    print(f"Serving on http://{host}:{port}")
    server.serve_forever()


def _get_metadata_list(commit_config):
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
        if os.path.exists(work_dir):
            temp_dir = tempfile.mkdtemp(prefix='mymlops_removed_', dir='/tmp')
            shutil.move(work_dir, temp_dir)
            logger.warning(f"Moved the old, corrupted directory to {temp_dir}.")

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

    for x in metadata_list:
        x['timestamp'] = _parse_timestamp(x['commit']).isoformat()

    return metadata_list


def _notebook_has_error(notebook_path):
    with open(notebook_path, 'r') as f:
        notebook = f.read()
    notebook = json.loads(notebook)
    for cell in notebook['cells']:
        for output in cell.get('outputs', []):
            if output['output_type'] == 'error':
                return True
    return False

def _parse_timestamp(timestamp_str):
    dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
    # UTCに設定
    return dt.replace(tzinfo=timezone.utc)
