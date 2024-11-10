import json
import logging
import subprocess
import threading
import time


logger = logging.getLogger(__name__)


class TunnelManager:
    def __init__(self, tunnel_config):
        options = [
            'gcloud',
            'compute',
            'instances',
            'list',
            '--filter=labels.mymlops:start',
            '--format=json',
        ]
        res = subprocess.check_output(options)
        instances = json.loads(res)
        instances = sorted(instances, key=lambda x: x['name'])

        local_port = tunnel_config['local_port_min']
        tunnels = []
        for inst in instances:
            for remote_port in tunnel_config['remote_ports']:
                tunnels.append(Tunnel(inst['name'], inst['zone'].split("/")[-1], local_port, remote_port))
                local_port += 1

        self.tunnels = tunnels


class Tunnel:
    def __init__(self, name, zone, local_port, remote_port):
        self.name = name
        self.zone = zone
        self.local_port = local_port
        self.remote_port = remote_port

        def run():
            while True:
                try:
                    options = [
                        'gcloud',
                        'compute',
                        'ssh',
                        name,
                        f'--zone={zone}',
                        '--',
                        '-L', f'{local_port}:127.0.0.1:{remote_port}',
                        '-o', 'ServerAliveInterval=1',
                    ]
                    logger.info(f'ssh tunnel connect {name} {zone} {local_port}:127.0.0.1:{remote_port}')
                    subprocess.run(options, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as err:
                    logger.error(f'ssh tunnel failed {err}')

                time.sleep(1)

        self._thread = threading.Thread(target=run)
        self._thread.start()
