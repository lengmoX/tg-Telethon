import click
import io
import getpass

from rich.panel import Panel
from rich.prompt import Prompt
import qrcode

from tgf.cli.utils import (
    console, async_command, print_success, print_error, print_info
)
from tgf.service.auth_service import AuthService
from tgf.data.config import get_config


@click.command()
@click.pass_context
@async_command
async def login(ctx):
    """
    Login to Telegram using QR code
    
    \b
    Scan the QR code with your Telegram app:
    Settings -> Devices -> Link Desktop Device
    
    \b
    Examples:
      tgf login              # Login as default account
      tgf -n work login      # Login as 'work' account
    """
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    # Check for API credentials
    if not config.has_credentials():
        print_error("API credentials not configured!")
        console.print("\n[yellow]Please configure .env file:[/yellow]")
        console.print("  [bold]TGF_API_ID[/bold]=your_api_id")
        console.print("  [bold]TGF_API_HASH[/bold]=your_api_hash")
        console.print("\nGet these from [link=https://my.telegram.org]https://my.telegram.org[/link]")
        raise click.Abort()
    
    auth_service = AuthService(config)
    
    # Check if already logged in
    existing = await auth_service.check_login(namespace)
    if existing:
        console.print(f"\n[green]Already logged in as:[/green]")
        _print_account_info(existing, namespace)
        
        if not click.confirm("Login again?", default=False):
            return
    
    print_info(f"Logging in as namespace: [bold]{namespace}[/bold]")
    
    def on_qr(url: str):
        """Display QR code in terminal"""
        _display_qr_terminal(url)
    
    def on_2fa() -> str:
        """Prompt for 2FA password"""
        console.print()
        console.print(Panel(
            "[yellow]Two-step verification is enabled[/yellow]\n"
            "Please enter your cloud password",
            title="[bold]2FA Required[/bold]",
            border_style="yellow"
        ))
        password = getpass.getpass("2FA Password: ")
        return password
    
    try:
        account = await auth_service.login(
            namespace=namespace,
            on_qr=on_qr,
            on_2fa=on_2fa
        )
        
        console.print("\n")
        print_success("Login successful!")
        _print_account_info(account, namespace)
        
    except Exception as e:
        print_error(f"Login failed: {e}")
        raise click.Abort()


@click.command()
@click.option('--force', '-f', is_flag=True, help='Force logout without confirmation')
@click.pass_context
@async_command
async def logout(ctx, force: bool):
    """
    Logout from Telegram
    
    \b
    Examples:
      tgf logout            # Logout from default account
      tgf -n work logout    # Logout from 'work' account
    """
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    auth_service = AuthService(config)
    
    # Check if logged in
    account = await auth_service.check_login(namespace)
    
    if not account:
        print_info(f"No session found for namespace: {namespace}")
        return
    
    console.print(f"[yellow]Will logout from:[/yellow]")
    _print_account_info(account, namespace)
    
    if not force:
        if not click.confirm("Are you sure?", default=False):
            return
    
    try:
        await auth_service.logout(namespace)
        print_success(f"Logged out from namespace: {namespace}")
    except Exception as e:
        print_error(f"Logout failed: {e}")


def _display_qr_terminal(url: str):
    """Display QR code in terminal using Rich"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Generate string
    f = io.StringIO()
    qr.print_ascii(out=f, invert=True)
    f.seek(0)
    qr_string = f.read()
    
    # Display in panel
    console.print()
    console.print(Panel(
        qr_string,
        title="[bold cyan]Scan with Telegram[/bold cyan]",
        subtitle="Settings → Devices → Link Desktop Device",
        border_style="cyan"
    ))
    console.print("[dim]Waiting for scan...[/dim]")


def _print_account_info(account, namespace: str):
    """Print account information"""
    name = account.first_name
    if account.last_name:
        name += f" {account.last_name}"
    
    username = f"@{account.username}" if account.username else "[no username]"
    premium = " [yellow]★ Premium[/yellow]" if account.is_premium else ""
    
    console.print(f"  Name:      [bold]{name}[/bold]{premium}")
    console.print(f"  Username:  [cyan]{username}[/cyan]")
    console.print(f"  Namespace: [dim]{namespace}[/dim]")
