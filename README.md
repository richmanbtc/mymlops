A MLOps tool built for my own needs.

## current status

todo

- finished time (need to know if I need work)
- detailed status (processing, stopped, succeeded, failed)
- push from local before create gce
- interval push notebook during papermill process
- start
- idle shutdown
- commit message
- gcp project from config

## personal memo

When working on ML tasks:

1. Open `mymlops status --server` in a browser and keep it next to the Jupyter tab.
2. Use `mymlops commit path/to/notebooks -n "notes"` to make quick commits.

## install

```bash
git clone https://github.com/richmanbtc/mymlops.git
cd mymlops
pip install -e .
```

## how to use

```bash
mymlops --help
```

see
https://github.com/richmanbtc/mymlops-testrepo

## troubleshooting

- Q: An unexecuted output.ipynb has been uploaded.
- A: Please check if the Docker running the notebook is mounting the directory that includes output.ipynb.

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

## design notes

### gcp batch vs gce

- use gce
- gcp batch sometimes did not start the job for unknown reasons
- I decided to use gce because it is new, there is little information, and it is not mature.

batch docs

- supported os image https://cloud.google.com/batch/docs/vm-os-environment-overview?hl=ja
- job reference https://cloud.google.com/batch/docs/reference/rest/v1/projects.locations.jobs#Disk

### mymlops.yml

schema is defined in src/mymlops/config_schema.json

### commit specification

Division of responsibilities between mymlops and each repository

| process              | mymlops | repository |
|----------------------|-------|------------|
| source snapshot      |       | o          |
| start gce instance   | o     |            |
| setup gce instance   | o     |            |
| git clone repo       | o     |            |
| execute notebook     |       | o          |
| git push output_repo | o     |            |
| delete gce instance  | o     |            |

In each repository, the following actions are required:

- Execute the notebook at the specified path and overwrite it with the execution results.
- If necessary, create an artifacts directory in the same directory as the notebook and place the outputs inside it.

### start

- create compute engine instance
- git clone your repository
- execute start command defined in your repository

out of scopes

- existence check (creates a new one if already exists)
- deletion (manual deletion on gcp)
- recreation (delete manually on gcp, then start)

### papermill vs nbconvert

By default, nbconvert does not update the ipynb file when an error occurs.
However, when you use the --allow-error option, it updates the ipynb file and does not stop at the first error.
On the other hand, papermill stops when an error occurs and updates the ipynb file with execution results up to the error point.
Since papermill's behavior is more convenient, it is recommended to use papermill.

### gpu list

```bash
gcloud compute accelerator-types list --format="table(zone, name, description)" | sort
```

### Design Guideline

- Build what I’ll use.
- Don’t build what I won’t.
- Remove anything I’ve built but don’t use. 
