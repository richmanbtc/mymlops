
## todo

- gpu
- start
- idle shutdown
- raise in run_redirect
- commit message
- fix --allow-error

## setup

instance template

- os: cos
- required scope: compute engine read/write (for self deletion)

config

- see mymlops-testrepo

## command completion

add this to ~/.bash_profile

```bash
eval "$(_MYMLOPS_COMPLETE=bash_source mymlops)"
```

bash >=4.4 required. how to check shell version

```bash
$SHELL --version
```

change shell

- https://qiita.com/pnpnd1111/items/2bb7927cea9134574dc3

## nbconvert --allow-error

- Sometimes it does not output to a file.
- and exit code is 0

## gcp batch vs gce

- use gce
- gcp batch sometimes did not start the job for unknown reasons
- I decided to use gce because it is new, there is little information, and it is not mature.

## batch docs

- supported os image https://cloud.google.com/batch/docs/vm-os-environment-overview?hl=ja
- job reference https://cloud.google.com/batch/docs/reference/rest/v1/projects.locations.jobs#Disk

## install

pip install  -e .

## command

- mymlops commit cpu notebook_path
- mymlops commit gpu notebook_path
- mymlops start cpu1
- mymlops start cpu2

## mymlops.yml

commit:
  cpu:
    instance_type: cpu_default
    command: docker-compose ...
  gpu:
    instance_type: gpu_default
    command: docker-compose ...

start:
  cpu1:
    instance_type: cpu_default
  cpu2:
    instance_type: cpu_default

instance_type:
  cpu_default:
    machine_type: a
    gpu: a
    spot: true

## commit interface that must be defined in each repo

- [command defined in config] notebook_path
- input: notebook relative path from repository root
- output:
- notebook_path/[datetime]/output.ipynb
- notebook_path/[datetime]/metrics.json
- notebook_path/[datetime]/params.json
- notebook_path/[datetime]/artifacts/*.*

any standard exists?

## start

- create or start compute engine instance
- start jupyter (startup script)
- ssh tunnel

## instance type

- defined in config
- used for commit config and start config

## programming language

- python
- Any language is fine since it uses gcloud cli.
- I might use pandas in the future, so I use python.
