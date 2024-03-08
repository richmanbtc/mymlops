import subprocess

def run_redirect(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    for line in proc.stdout:
        print(line.decode('utf-8').strip())
