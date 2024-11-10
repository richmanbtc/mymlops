import json
import subprocess
from collections import Counter


def gce_get_zone(instance):
    options = [
        'gcloud',
        'compute',
        'instances',
        'list',
        f"--filter=name=('{instance}')",
        '--format=get(zone)',
    ]
    res = subprocess.check_output(options)
    return shorten_zone(res.decode('ascii').strip())


def shorten_zone(zone):
    return zone.split("/")[-1]


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

    zones = [shorten_zone(instance["zone"]) for instance in instances]
    return Counter(zones)
