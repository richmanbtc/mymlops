import click
from .config import read_config
from .commit import do_commit
from .start import do_start
from .startup_logs import do_startup_logs


@click.group()
def cli():
    pass

@cli.command()
@click.argument('config_name')
@click.argument('path')
def commit(config_name, path):
    """run notebook and save outputs like kaggle commit"""
    config = read_config()
    do_commit(config, config_name, path)

@cli.command()
@click.argument('instance_name')
def startup_logs(instance_name):
    """tail startup script logs of compute engine instance"""
    do_startup_logs(instance_name)

@cli.command()
@click.argument('config_name')
def start(config_name):
    """run notebook and save outputs like kaggle commit"""
    config = read_config()
    do_start(config, config_name)

if __name__ == '__main__':
    cli()

