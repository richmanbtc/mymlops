import copy
import subprocess

def run_redirect(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    for line in proc.stdout:
        print(line.decode('utf-8').strip())

    proc.wait()
    if proc.returncode != 0:
        raise Exception(f'command failed {proc.returncode}: {command}')

def remove_notebook_output(x):
    x = copy.deepcopy(x)
    cells = x['cells']
    for i in range(len(cells)):
        if 'outputs' in cells[i]:
            cells[i]['outputs'] = []
        if 'execution_count' in cells[i]:
            cells[i]['execution_count'] = None
    return x
