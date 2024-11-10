import datetime
from .gce_create import gce_create
from .gce_zones import gce_select_zone


def do_start(start_config):
    print(f'do_start')

    repo_config = start_config['repository']
    repo_branch = repo_config.get('branch', 'master')
    repo_url = repo_config['url']
    with open(repo_config['deploy_key'], 'r') as f:
        repo_deploy_key = f.read()

    now = datetime.datetime.now(datetime.timezone.utc)

    vm_name = 'mymlops-' + now.strftime('%Y%m%d-%H%M%S')
    instance_config = start_config['instance']
    zones = instance_config['zones']
    zone = gce_select_zone(zones)

    command = start_config['command']

    script = f'''
cd /root
echo "{repo_deploy_key}" > ~/.ssh/id_rsa
chmod 400 ~/.ssh/id_rsa
git clone --recursive -b "{repo_branch}" "{repo_url}" repo
cd repo

{command}
'''

    gce_create(
        vm_name=vm_name,
        zone=zone,
        accelerator=instance_config.get('accelerator'),
        machine_type=instance_config.get('machine_type'),
        snapshot=instance_config['snapshot'],
        label='start',
        startup_script=script,
    )
