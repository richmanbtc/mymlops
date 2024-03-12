import subprocess
import yaml
import time
from .gce_create import gce_create
from .utils import run_redirect

def do_start(config, config_name, recreate):
    print(f'do_start config_name {config_name}')
    vm_name = 'mymlops-' + config_name

    start_config = config['starts'][config_name]
    instance_type_config = config['instance_types'][start_config['instance_type']]
    zone = instance_type_config['zone']
    local_port = start_config['local_port']
    port = start_config['port']

    if recreate:
        raise Exception('not implemented')

    desc = _describe(vm_name, zone)
    if desc is None:
        _create(config, config_name, vm_name)
    elif desc['status'] == 'TERMINATED':
        _start(vm_name, zone)

    for i in range(10):
        desc = _describe(vm_name, zone)
        if desc is not None and desc['status'] == 'RUNNING':
            break
        time.sleep(1)

    proxy_command = [
        'gcloud',
        'compute',
        'ssh',
        vm_name,
        f'--zone={zone}',
        '--',
        '-NL',
        f'{local_port}:localhost:{port}'
    ]
    print(proxy_command)
    run_redirect(proxy_command)


def _delete(vm_name, zone):
    print(subprocess.check_output([
        'gcloud',
        'compute',
        'instances',
        'start',
        vm_name,
        f'--zone={zone}'
    ]))

def _start(vm_name, zone):
    print(subprocess.check_output([
        'gcloud',
        'compute',
        'instances',
        'start',
        vm_name,
        f'--zone={zone}'
    ]))

def _describe(vm_name, zone):
    try:
        yaml_str = subprocess.check_output([
            'gcloud',
            'compute',
            'instances',
            'describe',
            vm_name,
            f'--zone={zone}'
        ])
    except Exception as e:
        print(e)
        return None

    desc = yaml.safe_load(yaml_str)
    return desc

def _create(config, config_name, vm_name):
    print('_create')

    start_config = config['starts'][config_name]
    instance_type_config = config['instance_types'][start_config['instance_type']]
    zone = instance_type_config['zone']

    command = start_config['command']



    script = f'''
{command}
'''

    gce_create(
        config=config,
        vm_name=vm_name,
        instance_type=start_config['instance_type'],
        startup_script=script,
        delete_after_startup=False
    )
