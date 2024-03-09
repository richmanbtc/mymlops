from .utils import run_redirect

def do_startup_logs(instance_name, zone):
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
