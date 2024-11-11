import os
import json
import re
import subprocess
from collections import Counter
import yaml


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
    return short_zone(res.decode('ascii').strip())


def short_zone(zone):
    return zone.split("/")[-1]


def _zone_to_region(zone):
    return zone[:-2]

def gce_select_zone(zone_regex, accelerator):
    if accelerator:
        zones = _get_accelerator_available_zones(accelerator)
    else:
        zones = _get_all_zones()

    zones = [x for x in zones if re.match(zone_regex, x)]

    counts_by_region = _get_instance_counts_by_region(accelerator)
    costs_by_region = _get_costs_by_region()

    def min_key(zone):
        region = _zone_to_region(zone)
        return (
            counts_by_region.get(region, 0),
            costs_by_region.get(region, 1e7),
        )

    return min(zones, key=min_key)

def _get_all_zones():
    options = [
        'gcloud',
        'compute',
        'zones',
        'list',
        '--format=json',
    ]
    res = subprocess.check_output(options)
    zones = json.loads(res)
    return sorted([short_zone(x['name']) for x in zones])

def _get_accelerator_available_zones(accelerator):
    options = [
        'gcloud',
        'compute',
        'accelerator-types',
        'list',
        f'--filter={accelerator}',
        '--format=json',
    ]
    res = subprocess.check_output(options)
    accelerators = json.loads(res)
    return sorted(set([short_zone(x['zone']) for x in accelerators]))

def _get_instance_counts_by_region(accelerator):
    options = [
        'gcloud',
        'compute',
        'instances',
        'list',
        '--format=json',
    ]
    if accelerator:
        options.append(f'--filter=guestAccelerators.acceleratorType:{accelerator}')
    res = subprocess.check_output(options)
    instances = json.loads(res)

    regions = [
        _zone_to_region(short_zone(instance["zone"]))
        for instance in instances
    ]
    return Counter(regions)

def _get_costs_by_region():
    with open(os.path.join(os.path.dirname(__file__), 'pricing.yml'), 'r') as f:
        content = f.read()
    data = yaml.safe_load(content)
    cost = data['compute']['instance']['n1-standard-8']['cost']
    return { k: v['hour'] for k, v in cost.items() }
