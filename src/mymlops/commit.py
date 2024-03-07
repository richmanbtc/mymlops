import os
import datetime
import subprocess
import tempfile
import json
import base64
import gzip
from .consts import GITHUB_KNOWN_HOSTS


def do_commit(config, config_name, path):
    print(f'config_name {config_name}')
    print(f'path {path}')

    repo_url = config['repository']['remote']
    with open(config['repository']['key'], 'r') as f:
        deploy_key = f.read()

    with open(path, 'rb') as f:
        input_gzip_base64 = base64.b64encode(gzip.compress(f.read())).decode('ascii')

    branch = 'master'
    location = 'us-central1'

    assert path[-6:] == '.ipynb'
    now = datetime.datetime.now(datetime.timezone.utc)
    commit_dir = os.path.join(path[:-6], now.strftime('%Y%m%d_%H%M%S'))

    commit_config = config['commits'][config_name]
    instance_type = config['instance_types'][commit_config['instance_type']]

    machine_type = instance_type['machine_type']
    gpu = instance_type.get('gpu')

    command = commit_config['command']

    commit_message = f'commit {config_name} {commit_dir}'

    script = f'''#!/bin/bash
set -ex

export HOME=/tmp
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "{deploy_key}" > ~/.ssh/id_rsa
chmod 400 ~/.ssh/id_rsa
echo "{GITHUB_KNOWN_HOSTS}" > ~/.ssh/known_hosts
export GIT_SSH_COMMAND="ssh -o "UserKnownHostsFile=/tmp/.ssh/known_hosts" -i /tmp/.ssh/id_rsa -F /dev/null"

git config --global user.email "you@example.com"
git config --global user.name "Your Name"

cd /tmp
git clone --recursive -b "{branch}" "{repo_url}" repo

cd repo
mkdir -p "{commit_dir}"
echo "{input_gzip_base64}" | base64 -d | gzip -d > "{commit_dir}/output.ipynb"

shopt -s expand_aliases
alias docker-compose='docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD:$PWD" \
    -w="$PWD" \
    docker/compose:1.24.0'

{command} "{commit_dir}/output.ipynb"

git add "{commit_dir}"
git commit -m "{commit_message}"
git stash
git pull --rebase origin "{branch}"
git push origin "{branch}"
'''

    job = {
      "taskGroups": [
        {
          "taskSpec": {
            "runnables": [
              {
                "script": {
                  "text": script,
                }
              }
            ],
            "volumes": [],
            "maxRetryCount": 0,
            "maxRunDuration": "3600s"
          },
          "taskCount": 1,
          "parallelism": 1
        }
      ],
      "allocationPolicy": {
        "instances": [
          {
            "installGpuDrivers": gpu is not None,
            "policy": {
              "machineType": machine_type,
              "provisioningModel": "SPOT",
              "accelerators": [] if gpu is None else [
                              {
                    'aaa': gpu,
                              }
                            ],
                "bootDisk": {
                    'image': 'batch-cos',
                    'sizeGb': 100,
                    'type': 'pd-ssd',
                },
            },
          }
        ]
      },
      "labels": {},
      "logsPolicy": {
        "destination": "CLOUD_LOGGING"
      }
    }

    with tempfile.TemporaryDirectory() as dir:
        job_path = os.path.join(dir, 'job.json')
        with open(job_path, "w") as f:
            json.dump(job, f)

        options = [
            'gcloud',
            'batch',
            'jobs',
            'submit',
            f'--config={job_path}',
            f'--location={location}',
        ]
        res = subprocess.run(options, stdout=subprocess.PIPE)

    print(res.stdout.decode('utf-8'))
