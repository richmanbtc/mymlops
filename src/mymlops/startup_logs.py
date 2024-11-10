from .utils import run_redirect
from .gce_zones import gce_get_zone

def do_startup_logs(instance_name):
    zone = gce_get_zone(instance_name)
    options = [
        'gcloud',
        'compute',
        'ssh',
        instance_name,
        f'--zone={zone}',
        '--command=sudo journalctl -n 1000 -f -u google-startup-scripts.service',
        '--',
        '-o', 'ServerAliveInterval=1',
    ]
    run_redirect(options)
