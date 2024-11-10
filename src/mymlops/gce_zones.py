import json
import subprocess
from collections import Counter


def gce_select_zone(zones):
    if len(zones) <= 1:
        return zones[0]

    counts = _get_instance_counts_by_zone()
    return min(zones, key=lambda zone: counts.get(zone, 0))

def _get_instance_counts_by_zone():
    options = [
        'gcloud',
        'compute',
        'instances',
        'list',
        '--format=json',
    ]
    res = subprocess.check_output(options)
    instances = json.loads(res)

    zones = [instance["zone"].split("/")[-1] for instance in instances]
    return Counter(zones)
