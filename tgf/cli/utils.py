"""
CLI Utility Functions for TGF
"""

import asyncio
from functools import wraps
from typing import Callable, Any

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from tgf.data.config import get_config, init_config


# Rich console for formatted output
console = Console()
error_console = Console(stderr=True)


def async_command(f: Callable) -> Callable:
    """Decorator to run async click commands"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


def require_login(f: Callable) -> Callable:
    """Decorator to require login before command execution"""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        from tgf.data.session import SessionManager
        
        # Get namespace from context
        ctx = click.get_current_context()
        namespace = ctx.obj.get("namespace", "default")
        config = ctx.obj.get("config", get_config())
        
        session_mgr = SessionManager(config.sessions_dir)
        
        if not session_mgr.session_exists(namespace):
            error_console.print(
                f"[red]✗[/red] Not logged in. Run [bold]tgf login[/bold] first."
            )
            raise click.Abort()
        
        return await f(*args, **kwargs)
    
    return wrapper


def print_success(message: str) -> None:
    """Print success message"""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print error message"""
    error_console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print warning message"""
    console.print(f"[yellow]![/yellow] {message}")


def print_info(message: str) -> None:
    """Print info message"""
    console.print(f"[blue]ℹ[/blue] {message}")


def create_table(title: str, columns: list) -> Table:
    """Create a Rich table with consistent styling"""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    for col in columns:
        if isinstance(col, tuple):
            table.add_column(col[0], **col[1])
        else:
            table.add_column(col)
    return table


def create_progress() -> Progress:
    """Create a Rich progress bar"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    )


def format_chat(chat_str: str) -> str:
    """Format chat string for display"""
    if chat_str.startswith("-100"):
        return f"Channel({chat_str})"
    elif chat_str.startswith("-"):
        return f"Group({chat_str})"
    elif chat_str.startswith("@"):
        return chat_str
    elif chat_str.lower() == "me":
        return "Saved Messages"
    return chat_str


def confirm_action(message: str) -> bool:
    """Ask for confirmation"""
    return click.confirm(message, default=False)
