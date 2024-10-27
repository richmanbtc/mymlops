import click
from .config import read_config
from .commit import do_commit
from .start import do_start
from .startup_logs import do_startup_logs


@click.group()
def cli():
    pass

@cli.command()
def validate():
    """validate config"""
    read_config()
    print('ok')

@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('-a', '--artifacts', is_flag=True, show_default=True, default=False)
def commit(path, artifacts):
    """run notebook and save outputs like kaggle commit"""
    config = read_config()
    do_commit(config['commit'], path, artifacts)

@cli.command()
@click.argument('instance_name')
@click.argument('zone')
def startup_logs(instance_name, zone):
    """tail startup script logs of compute engine instance"""
    do_startup_logs(instance_name, zone)

@cli.command()
@click.argument('config_name')
@click.option('-r', '--recreate', is_flag=True, show_default=True, default=False)
def start(config_name, recreate):
    """run notebook and save outputs like kaggle commit"""
    config = read_config()
    do_start(config, config_name, recreate)

if __name__ == '__main__':
    cli()

