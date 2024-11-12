import click
import logging
from .config import read_config
from .commit import do_commit
from .start import do_start
from .startup_logs import do_startup_logs
from .dashboard import do_dashboard


logging.basicConfig(level=logging.INFO)


@click.group()
def cli():
    pass

@cli.command()
def validate():
    """validate config"""
    read_config()
    print('ok')

@cli.command()
@click.argument('path', type=click.Path(exists=False))
@click.option('-a', '--artifacts', is_flag=True, show_default=True, default=False)
@click.option('-n', '--notes', show_default=True, default='')
@click.option('-i', '--instance', show_default=True, default='')
@click.option('-k', '--keep_instance', is_flag=True, show_default=True, default=False)
def commit(path, artifacts, notes, instance, keep_instance):
    """run notebook and save outputs like kaggle commit"""
    config = read_config()
    do_commit(config['commit'], path, artifacts, notes, instance, keep_instance)


@cli.command()
@click.argument('instance_name')
def startup_logs(instance_name):
    """tail startup script logs of compute engine instance"""
    do_startup_logs(instance_name)

@cli.command()
def start():
    """start compute engine instance and setup"""
    config = read_config()
    do_start(config['start'])

@cli.command()
def dashboard():
    """"""
    config = read_config()
    do_dashboard(config)


if __name__ == '__main__':
    cli()

