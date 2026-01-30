"""
TGF CLI Main Entry Point

Main command group with global options.
"""

import click

from tgf import __version__
from tgf.data.config import init_config, get_config
from tgf.cli.utils import console, print_info


# Global context settings
CONTEXT_SETTINGS = dict(
    help_option_names=['-h', '--help'],
    max_content_width=120,
)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, '-V', '--version', prog_name='tgf')
@click.option(
    '-n', '--ns', '--namespace',
    default='default',
    help='Account namespace (default: default)',
    metavar='NAME'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Enable verbose output'
)
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug mode'
)
@click.pass_context
def cli(ctx, ns: str, verbose: bool, debug: bool):
    """
    TGF - Telegram Forwarder CLI
    
    A command-line tool for forwarding messages between Telegram channels/groups.
    
    \b
    Examples:
      tgf login                        # Login with QR code
      tgf -n work login                # Login to a different account
      tgf forward -s @channel -t me    # Forward messages
      tgf rule add -s @source -t @dest # Add a watch rule
      tgf watch                        # Start watching
    
    For more information on a specific command, use --help after the command.
    """
    # Initialize context
    ctx.ensure_object(dict)
    
    # Configure logging level
    log_level = "DEBUG" if debug else ("INFO" if verbose else "WARNING")
    
    # Initialize config with namespace
    config = init_config(
        namespace=ns,
        log_level=log_level
    )
    
    ctx.obj["config"] = config
    ctx.obj["namespace"] = ns
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug


# Import and register subcommands
from tgf.cli.login import login, logout
from tgf.cli.forward import forward
from tgf.cli.rule import rule
from tgf.cli.watch import watch, status
from tgf.cli.chat import chat
from tgf.cli.filter import filter
from tgf.cli.backup import backup

cli.add_command(login)
cli.add_command(logout)
cli.add_command(forward)
cli.add_command(rule)
cli.add_command(watch)
cli.add_command(status)
cli.add_command(chat)
cli.add_command(filter)
cli.add_command(backup)


@cli.command()
@click.pass_context
def info(ctx):
    """Show current configuration info"""
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    console.print(f"[bold]TGF Configuration[/bold]")
    console.print(f"  Namespace: [cyan]{namespace}[/cyan]")
    console.print(f"  Data dir:  [dim]{config.data_dir}[/dim]")
    console.print(f"  DB path:   [dim]{config.db_path}[/dim]")
    console.print(f"  Sessions:  [dim]{config.sessions_dir}[/dim]")
    
    if config.has_credentials():
        console.print(f"  API ID:    [green]Configured[/green]")
    else:
        console.print(f"  API ID:    [red]Not set[/red] (set TGF_API_ID)")


if __name__ == '__main__':
    cli()
