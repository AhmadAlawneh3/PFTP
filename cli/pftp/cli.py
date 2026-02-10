"""PFTP CLI commands"""

import click
import shutil
import subprocess
import re
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box

from . import __version__
from .config import Config
from .docker_manager import DockerManager
from .constants import (
    DEFAULT_DATA_DIR,
    DEFAULT_PORT,
    CONFIG_FILE,
    CONFIG_DIR,
    TOOLS_DIR,
    UPLOADS_DIR,
    FTP_PORT,
    SMB_PORT,
    SMB_NETBIOS_PORT,
)

console = Console()

# ASCII Logo
LOGO = """
[cyan]    ____  ________________[/cyan]
[cyan]   / __ \\/ ____/_  __/ __ \\[/cyan]
[cyan]  / /_/ / /_    / / / /_/ /[/cyan]
[cyan] / ____/ __/   / / / ____/[/cyan]
[cyan]/_/   /_/     /_/ /_/[/cyan]
"""


def get_config_path(data_dir: Path = None) -> Path:
    """Get configuration file path"""
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    return Path(data_dir) / CONFIG_DIR / CONFIG_FILE


def hash_password(password: str) -> str:
    """Return password as-is for multi-protocol compatibility."""
    return password


def get_local_ips():
    """Get local IP addresses (prioritize tun/VPN and eth interfaces)"""
    try:
        result = subprocess.run(['ip', 'addr', 'show'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return []

        ips = []
        current_interface = None

        for line in result.stdout.split('\n'):
            if_match = re.match(r'^\d+:\s+(\S+):', line)
            if if_match:
                current_interface = if_match.group(1)

            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
            if ip_match and current_interface:
                ip = ip_match.group(1)
                if ip != '127.0.0.1':
                    if current_interface.startswith('tun'):
                        priority = 0
                    elif current_interface.startswith('eth'):
                        priority = 1
                    elif current_interface.startswith('wlan'):
                        priority = 2
                    else:
                        priority = 3
                    ips.append((priority, ip, current_interface))

        ips.sort()
        return [ip for _, ip, _ in ips]
    except Exception:
        return []


def print_logo():
    """Print ASCII logo banner"""
    console.print(LOGO)
    console.print(f"[dim]Pentest File Transfer Protocols[/dim] [cyan]v{__version__}[/cyan]")
    console.print()


def print_header(title: str, subtitle: str = None):
    """Print a styled header with double-edge box"""
    console.print()
    header_text = Text(title, style="bold white", justify="center")
    footer = f"[dim]v{__version__} • github.com/AhmadAlawneh3/PFTP[/dim]"
    if subtitle:
        footer = f"[dim]{subtitle}[/dim] • {footer}"
    console.print(Panel(
        header_text,    
        subtitle=footer,
        border_style="cyan",
        box=box.DOUBLE_EDGE,
        padding=(0, 2)
    ))


def print_step(step: int, total: int, title: str):
    """Print a wizard step header"""
    console.print(f"\n[bold cyan][Step {step}/{total}][/bold cyan] {title}")
    console.print("[dim]" + "─" * 50 + "[/dim]")


def print_success(message: str):
    """Print success message"""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Print error message"""
    console.print(f"[red]✗[/red] {message}", style="red")


def print_warning(message: str):
    """Print warning message"""
    console.print(f"[yellow]![/yellow] {message}")


def print_success_panel(title: str, content: str):
    """Print a success panel with content"""
    panel_content = f"[bold green]✓ {title}[/bold green]\n\n{content}"
    console.print()
    console.print(Panel(
        panel_content,
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    ))


@click.group()
@click.version_option(version=__version__)
def cli():
    """PFTP - Pentest File Transfer Protocols

    A CLI tool for managing file transfer servers during penetration testing.
    """
    pass


@cli.command()
@click.option('--yes', '-y', is_flag=True, help='Skip prompts, use defaults')
@click.option('--data-dir', type=click.Path(), help='Data directory')
@click.option('--tools-dir', type=click.Path(), help='Custom tools directory')
@click.option('--uploads-dir', type=click.Path(), help='Custom uploads directory')
@click.option('--http-port', type=int, help='HTTP server port')
@click.option('--ftp-port', type=int, help='FTP server port')
@click.option('--enable-ftp/--disable-ftp', default=None, help='Enable/disable FTP')
@click.option('--enable-smb/--disable-smb', default=None, help='Enable/disable SMB')
@click.option('--auth/--no-auth', default=None, help='Enable/disable authentication')
@click.option('--auth-username', help='Authentication username')
@click.option('--auth-password', help='Authentication password')
@click.option('--restart-policy', type=click.Choice(['no', 'always', 'unless-stopped', 'on-failure']),
              help='Docker restart policy')
@click.option('--skip-pull', is_flag=True, help='Skip downloading PFTP')
def install(yes, data_dir, tools_dir, uploads_dir, http_port, ftp_port,
            enable_ftp, enable_smb, auth, auth_username, auth_password,
            restart_policy, skip_pull):
    """Install and configure pftp"""

    # print_logo()
    print_header("PFTP Installation", "Setup Wizard")

    # Interactive configuration
    if not yes:
        # Step 1: Directory Configuration
        print_step(1, 4, "Directory Configuration")

        if not data_dir:
            data_dir = Prompt.ask(
                "  [cyan]Data directory[/cyan]",
                default=str(DEFAULT_DATA_DIR)
            )

        data_dir = Path(data_dir).expanduser()

        if tools_dir is None:
            if Confirm.ask("  [cyan]Use custom tools directory[/cyan]", default=False):
                tools_dir = Prompt.ask("  [cyan]Tools directory path[/cyan]")

        if uploads_dir is None:
            if Confirm.ask("  [cyan]Use custom uploads directory[/cyan]", default=False):
                uploads_dir = Prompt.ask("  [cyan]Uploads directory path[/cyan]")

        # Step 2: Protocol Configuration
        print_step(2, 4, "Protocol Configuration")

        if http_port is None:
            http_port = int(Prompt.ask("  [cyan]HTTP port[/cyan]", default=str(DEFAULT_PORT)))

        if enable_ftp is None:
            enable_ftp = Confirm.ask("  [cyan]Enable FTP server[/cyan]", default=True)

        if enable_ftp and ftp_port is None:
            ftp_port = int(Prompt.ask("  [cyan]FTP port[/cyan]", default=str(FTP_PORT)))

        if enable_smb is None:
            enable_smb = Confirm.ask("  [cyan]Enable SMB server[/cyan]", default=False)

        # Step 3: Authentication
        print_step(3, 4, "Authentication")

        if auth is None:
            auth = Confirm.ask("  [cyan]Enable authentication[/cyan]", default=False)
        if auth:
            if auth_username is None:
                auth_username = Prompt.ask("  [cyan]Username[/cyan]", default="admin")
            if auth_password is None:
                auth_password = Prompt.ask("  [cyan]Password[/cyan]", password=True)

        # Step 4: Docker Setup
        print_step(4, 4, "Docker Setup")

        if restart_policy is None:
            if Confirm.ask("  [cyan]Configure restart policy[/cyan]", default=False):
                policy_table = Table(show_header=False, box=None, padding=(0, 2))
                policy_table.add_column("Policy", style="green")
                policy_table.add_column("Description", style="dim")
                policy_table.add_row("no", "Never restart automatically")
                policy_table.add_row("always", "Always restart (even after reboot)")
                policy_table.add_row("unless-stopped", "Restart unless manually stopped")
                policy_table.add_row("on-failure", "Restart only on errors")
                console.print(policy_table)
                restart_policy = Prompt.ask(
                    "  [cyan]Restart policy[/cyan]",
                    choices=['no', 'always', 'unless-stopped', 'on-failure'],
                    default='unless-stopped'
                )
    else:
        # Non-interactive defaults
        if not data_dir:
            data_dir = str(DEFAULT_DATA_DIR)
        data_dir = Path(data_dir).expanduser()
        if http_port is None:
            http_port = DEFAULT_PORT
        if enable_ftp is None:
            enable_ftp = True
        if ftp_port is None:
            ftp_port = FTP_PORT
        if enable_smb is None:
            enable_smb = False

    # Set up directory paths
    if tools_dir:
        tools_dir = Path(tools_dir).expanduser()
    else:
        tools_dir = data_dir / TOOLS_DIR

    if uploads_dir:
        uploads_dir = Path(uploads_dir).expanduser()
    else:
        uploads_dir = data_dir / UPLOADS_DIR

    config_dir = data_dir / CONFIG_DIR

    # Create directories
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Creating directories", total=None)
        tools_dir.mkdir(parents=True, exist_ok=True)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        config_dir.mkdir(parents=True, exist_ok=True)

    print_success(f"Created {data_dir}")

    # Create configuration
    config = Config(
        port=http_port,
        data_dir=data_dir,
        tools_dir=tools_dir if tools_dir != data_dir / TOOLS_DIR else None,
        uploads_dir=uploads_dir if uploads_dir != data_dir / UPLOADS_DIR else None,
    )

    config.protocols['http']['port'] = http_port
    config.protocols['ftp']['enabled'] = enable_ftp
    config.protocols['ftp']['port'] = ftp_port if ftp_port else FTP_PORT
    config.protocols['smb']['enabled'] = enable_smb

    if auth:
        config.auth_enabled = True
        config.auth_username = auth_username or 'admin'
        config.auth_password_hash = hash_password(auth_password) if auth_password else ''

    if restart_policy:
        config.restart_policy = restart_policy

    config_path = get_config_path(data_dir)
    config.save(config_path)
    print_success("Configuration saved")

    # Download PFTP
    if not skip_pull:
        console.print()
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading PFTP", total=None)
            try:
                dm = DockerManager(config)
                dm.pull_image(config.docker_image)
                progress.update(task, description="[green]✓ PFTP ready[/green]")
            except Exception as e:
                progress.update(task, description="[yellow]Warning: Download incomplete[/yellow]")
                console.print("  [dim]You can download it later with: pftp update[/dim]")

    # Start the server automatically
    console.print()
    print_success("Installation complete")
    
    try:
        dm = DockerManager(config)
        if dm.start_container():
            print_success("Server started")
            
            # Show URLs
            ips = get_local_ips()
            if ips:
                console.print()
                console.print("[bold cyan]Server URLs:[/bold cyan]")
                for proto_name, proto_config in config.protocols.items():
                    if proto_config.get('enabled', True):
                        p = proto_config.get('port')
                        if proto_name == 'smb':
                            console.print(f"  [cyan]•[/cyan] SMB:  [bold cyan]\\\\{ips[0]}\\tools[/bold cyan]")
                        else:
                            console.print(f"  [cyan]•[/cyan] {proto_name.upper()}:  [bold cyan]{proto_name}://{ips[0]}:{p}[/bold cyan]")
                
                console.print()
                console.print("[bold]Next steps:[/bold]")
                console.print("  [bright_black]1.[/bright_black] Add tools:  [green]pftp add-tool ~/linpeas.sh[/green]")
                console.print("  [bright_black]2.[/bright_black] Status:     [green]pftp status[/green]")
        else:
            print_error("Failed to start server")
            console.print("[bright_black]Run 'pftp start' to start the server manually[/bright_black]")
    except Exception as e:
        print_error(f"Could not start server: {e}")
        console.print("[bright_black]Run 'pftp start' to start the server manually[/bright_black]")


@cli.command()
@click.option('--enable-http/--disable-http', default=None, help='Enable/disable HTTP server')
@click.option('--enable-ftp/--disable-ftp', default=None, help='Enable/disable FTP server')
@click.option('--enable-smb/--disable-smb', default=None, help='Enable/disable SMB server')
@click.option('--http-port', type=int, help='HTTP server port')
@click.option('--ftp-port', type=int, help='FTP server port')
@click.option('--smb-port', type=int, help='SMB server port')
@click.option('--auth/--no-auth', default=None, help='Enable/disable authentication')
@click.option('--auth-username', help='Authentication username')
@click.option('--auth-password', help='Authentication password')
@click.option('--tools-dir', help='Tools directory path')
@click.option('--uploads-dir', help='Uploads directory path')
@click.option('--restart-policy', type=click.Choice(['no', 'always', 'unless-stopped', 'on-failure']),
              help='Docker restart policy')
def configure(enable_http, enable_ftp, enable_smb, http_port, ftp_port, smb_port,
              auth, auth_username, auth_password, tools_dir, uploads_dir,
              restart_policy):
    """Reconfigure pftp settings"""

    config_path = get_config_path()
    if not config_path.exists():
        print_error("pftp is not installed. Run 'pftp install' first.")
        return

    config = Config.load(config_path)

    has_flags = any([
        enable_http is not None, enable_ftp is not None, enable_smb is not None,
        http_port is not None, ftp_port is not None, smb_port is not None,
        auth is not None, auth_username is not None, auth_password is not None,
        tools_dir is not None, uploads_dir is not None, restart_policy is not None
    ])

    if not has_flags:
        # Interactive mode - show current config
        print_header("Current Configuration", "Review Settings")
        console.print()

        # General info table
        general_table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
        general_table.add_column("Setting", style="cyan", width=20)
        general_table.add_column("Value", style="white")
        general_table.add_row("Data directory", str(config.data_dir))
        general_table.add_row("Tools directory", str(config.tools_dir))
        general_table.add_row("Uploads directory", str(config.uploads_dir))
        console.print(general_table)

        # Protocols table
        console.print("\n[bold cyan]Protocols[/bold cyan]")
        proto_table = Table(box=box.HEAVY_HEAD)
        proto_table.add_column("Protocol", style="cyan")
        proto_table.add_column("Status", justify="center")
        proto_table.add_column("Port", justify="center")
        proto_table.add_column("Details", style="white")

        for proto_name, proto_config in config.protocols.items():
            enabled = proto_config.get('enabled', True)
            status = "[green]● Enabled[/green]" if enabled else "[bright_black]○ Disabled[/bright_black]"
            port = str(proto_config.get('port', '-'))
            details = ""
            if proto_name == 'ftp':
                details = f"Passive: {proto_config.get('passive_start')}-{proto_config.get('passive_end')}"
            elif proto_name == 'smb':
                details = f"NetBIOS: {proto_config.get('netbios_port')}"
            proto_table.add_row(proto_name.upper(), status, port, details)

        console.print(proto_table)

        # Auth & Docker info
        console.print("\n[bold cyan]Other Settings[/bold cyan]")
        other_table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
        other_table.add_column("Setting", style="cyan", width=20)
        other_table.add_column("Value")

        if config.auth_enabled:
            other_table.add_row("Authentication", f"[green]● Enabled[/green] [bright_black](User: {config.auth_username})[/bright_black]")
        else:
            other_table.add_row("Authentication", "[bright_black]○ Disabled[/bright_black]")

        policy_desc = {
            'no': 'Never restart',
            'always': 'Always restart',
            'unless-stopped': 'Restart unless stopped',
            'on-failure': 'Restart on failure'
        }
        other_table.add_row("Restart Policy", f"[white]{config.restart_policy} ({policy_desc.get(config.restart_policy, '')})[/white]")
        console.print(other_table)

        # Reconfigure prompt
        print_header("Reconfigure Settings", "Interactive Mode")
        console.print("[dim]Press Ctrl+C to cancel[/dim]")

        try:
            # Step 1: Protocol Settings
            print_step(1, 4, "Protocol Settings")

            config.protocols['http']['enabled'] = Confirm.ask(
                "  [cyan]Enable HTTP[/cyan]",
                default=config.protocols['http']['enabled']
            )
            if config.protocols['http']['enabled']:
                config.protocols['http']['port'] = int(Prompt.ask(
                    "  [cyan]HTTP port[/cyan]",
                    default=str(config.protocols['http']['port'])
                ))
                config.port = config.protocols['http']['port']

            config.protocols['ftp']['enabled'] = Confirm.ask(
                "  [cyan]Enable FTP[/cyan]",
                default=config.protocols['ftp']['enabled']
            )
            if config.protocols['ftp']['enabled']:
                config.protocols['ftp']['port'] = int(Prompt.ask(
                    "  [cyan]FTP port[/cyan]",
                    default=str(config.protocols['ftp']['port'])
                ))

            config.protocols['smb']['enabled'] = Confirm.ask(
                "  [cyan]Enable SMB[/cyan]",
                default=config.protocols['smb']['enabled']
            )
            if config.protocols['smb']['enabled']:
                config.protocols['smb']['port'] = int(Prompt.ask(
                    "  [cyan]SMB port[/cyan]",
                    default=str(config.protocols['smb']['port'])
                ))

            # Step 2: Authentication Settings
            print_step(2, 4, "Authentication Settings")

            config.auth_enabled = Confirm.ask(
                "  [cyan]Enable authentication[/cyan]",
                default=config.auth_enabled
            )
            if config.auth_enabled:
                config.auth_username = Prompt.ask(
                    "  [cyan]Username[/cyan]",
                    default=config.auth_username or 'admin'
                )
                new_password = Prompt.ask(
                    "  [cyan]Password[/cyan] [dim](empty to keep current)[/dim]",
                    default="",
                    password=True
                )
                if new_password:
                    config.auth_password_hash = hash_password(new_password)
                    print_success("Password updated")

            # Step 3: Directory Settings
            print_step(3, 4, "Directory Settings")

            if Confirm.ask("  [cyan]Configure custom tools directory[/cyan]", default=False):
                tools_path = Prompt.ask("  [cyan]Tools directory path[/cyan]", default=str(config.tools_dir))
                config.tools_dir = Path(tools_path)
                config.tools_dir.mkdir(parents=True, exist_ok=True)

            if Confirm.ask("  [cyan]Configure custom uploads directory[/cyan]", default=False):
                uploads_path = Prompt.ask("  [cyan]Uploads directory path[/cyan]", default=str(config.uploads_dir))
                config.uploads_dir = Path(uploads_path)
                config.uploads_dir.mkdir(parents=True, exist_ok=True)

            # Step 4: Docker Settings
            print_step(4, 4, "Docker Settings")

            if Confirm.ask("  [cyan]Configure restart policy[/cyan]", default=False):
                policy_table = Table(show_header=False, box=None, padding=(0, 2))
                policy_table.add_column("Policy", style="green")
                policy_table.add_column("Description", style="dim")
                policy_table.add_row("no", "Never restart automatically")
                policy_table.add_row("always", "Always restart (even after reboot)")
                policy_table.add_row("unless-stopped", "Restart unless manually stopped")
                policy_table.add_row("on-failure", "Restart only on errors")
                console.print(policy_table)
                config.restart_policy = Prompt.ask(
                    "  [cyan]Restart policy[/cyan]",
                    choices=['no', 'always', 'unless-stopped', 'on-failure'],
                    default=config.restart_policy
                )

            config.save(config_path)
            console.print()
            print_success("Configuration updated")
            console.print("[dim]Run 'pftp restart' to apply changes[/dim]")

        except KeyboardInterrupt:
            console.print()
            print_warning("Configuration cancelled")
            return

    else:
        # Non-interactive mode
        print_header("Reconfigure PFTP", "Flag Mode")
        console.print()

        if enable_http is not None:
            config.protocols['http']['enabled'] = enable_http
            print_success(f"{'Enabled' if enable_http else 'Disabled'} HTTP protocol")

        if enable_ftp is not None:
            config.protocols['ftp']['enabled'] = enable_ftp
            print_success(f"{'Enabled' if enable_ftp else 'Disabled'} FTP protocol")

        if enable_smb is not None:
            config.protocols['smb']['enabled'] = enable_smb
            print_success(f"{'Enabled' if enable_smb else 'Disabled'} SMB protocol")

        if http_port is not None:
            config.protocols['http']['port'] = http_port
            config.port = http_port
            print_success(f"Set HTTP port to {http_port}")

        if ftp_port is not None:
            config.protocols['ftp']['port'] = ftp_port
            print_success(f"Set FTP port to {ftp_port}")

        if smb_port is not None:
            config.protocols['smb']['port'] = smb_port
            print_success(f"Set SMB port to {smb_port}")

        if auth is not None:
            config.auth_enabled = auth
            print_success(f"{'Enabled' if auth else 'Disabled'} authentication")

        if auth_username is not None:
            config.auth_username = auth_username
            print_success(f"Set username to {auth_username}")

        if auth_password is not None:
            config.auth_password_hash = hash_password(auth_password)
            print_success("Set authentication password")

        if tools_dir is not None:
            config.tools_dir = Path(tools_dir)
            config.tools_dir.mkdir(parents=True, exist_ok=True)
            print_success(f"Set tools directory to {tools_dir}")

        if uploads_dir is not None:
            config.uploads_dir = Path(uploads_dir)
            config.uploads_dir.mkdir(parents=True, exist_ok=True)
            print_success(f"Set uploads directory to {uploads_dir}")

        if restart_policy is not None:
            config.restart_policy = restart_policy
            print_success(f"Set restart policy to {restart_policy}")

        config.save(config_path)
        console.print()
        console.print("[dim]Run 'pftp restart' to apply changes[/dim]")


@cli.command()
@click.option('--detach', '-d', is_flag=True, default=True, help='Run in background')
@click.option('--port', type=int, help='Override config port')
@click.option('--foreground', is_flag=True, help='Run in foreground (show logs)')
def start(detach, port, foreground):
    """Start pftp server"""

    config_path = get_config_path()
    if not config_path.exists():
        print_error("pftp is not installed. Run 'pftp install' first.")
        return

    config = Config.load(config_path)

    if port:
        config.port = port

    config.tools_dir.mkdir(parents=True, exist_ok=True)
    config.uploads_dir.mkdir(parents=True, exist_ok=True)

    try:
        dm = DockerManager(config)

        if dm.is_running():
            print_warning("pftp is already running")
            console.print("[dim]Run 'pftp status' for details[/dim]")
            return

        if dm.start_container():
            print_success("Server started")
            
            # Show URLs
            ips = get_local_ips()
            if ips:
                console.print()
                console.print("[bold cyan]Server URLs:[/bold cyan]")
                for proto_name, proto_config in config.protocols.items():
                    if proto_config.get('enabled', True):
                        p = proto_config.get('port')
                        if proto_name == 'smb':
                            console.print(f"  [cyan]•[/cyan] SMB:  [bold cyan]\\\\{ips[0]}\\tools[/bold cyan]")
                        else:
                            console.print(f"  [cyan]•[/cyan] {proto_name.upper()}:  [bold cyan]{proto_name}://{ips[0]}:{p}[/bold cyan]")
        else:
            print_error("Failed to start server")
            return

        if foreground:
            console.print("\n[dim]Following logs (Ctrl+C to stop)...[/dim]\n")
            dm.get_logs(follow=True)

    except Exception as e:
        print_error(str(e))


@cli.command()
def stop():
    """Stop pftp server"""

    config_path = get_config_path()
    if not config_path.exists():
        print_error("pftp is not installed. Run 'pftp install' first.")
        return

    config = Config.load(config_path)

    try:
        dm = DockerManager(config)

        if not dm.is_running():
            print_warning("pftp is not running")
            return

        dm.stop_container()
        print_success("Server stopped")
    except Exception as e:
        print_error(str(e))


@cli.command()
def restart():
    """Restart pftp server"""

    config_path = get_config_path()
    if not config_path.exists():
        print_error("pftp is not installed. Run 'pftp install' first.")
        return

    config = Config.load(config_path)

    try:
        dm = DockerManager(config)

        dm.stop_container()
        dm.remove_container()
        dm.start_container()
        
        print_success("Server restarted")
        
        # Show URLs
        ips = get_local_ips()
        if ips:
            console.print()
            console.print("[bold cyan]Server URLs:[/bold cyan]")
            for proto_name, proto_config in config.protocols.items():
                if proto_config.get('enabled', True):
                    p = proto_config.get('port')
                    if proto_name == 'smb':
                        console.print(f"  [cyan]•[/cyan] SMB:  [bold cyan]\\\\{ips[0]}\\tools[/bold cyan]")
                    else:
                        console.print(f"  [cyan]•[/cyan] {proto_name.upper()}:  [bold cyan]{proto_name}://{ips[0]}:{p}[/bold cyan]")

    except Exception as e:
        print_error(str(e))


@cli.command()
def status():
    """Show pftp status and configuration"""

    config_path = get_config_path()
    if not config_path.exists():
        print_warning("pftp is not installed")
        console.print("[dim]Run 'pftp install' to get started[/dim]")
        return

    config = Config.load(config_path)

    try:
        dm = DockerManager(config)
        status_info = dm.get_status()
        ips = get_local_ips()

        # Build status panel
        is_running = status_info and status_info.get('status') == 'running'

        if is_running:
            status_text = "[bold green]● RUNNING[/bold green]"
        elif status_info and status_info.get('status') != 'not_found':
            status_text = f"[yellow]○ {status_info['status'].upper()}[/yellow]"
        else:
            status_text = "[red]○ STOPPED[/red]"

        # Print logo and header
        # print_logo()
        print_header("PFTP Status", "Server Information")
        console.print()

        # Server status table
        status_table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
        status_table.add_column("Label", style="cyan", width=15)
        status_table.add_column("Value")

        status_table.add_row("Status", status_text)

        console.print(status_table)

        # Protocols table with URL column
        console.print("\n[bold cyan]Protocols[/bold cyan]")
        proto_table = Table(box=box.HEAVY_HEAD)
        proto_table.add_column("Protocol", style="cyan", width=10)
        proto_table.add_column("Status", justify="center", width=14)
        proto_table.add_column("Port", justify="center", width=8)
        proto_table.add_column("URL", style="white")

        for proto_name, proto_config in config.protocols.items():
            enabled = proto_config.get('enabled', True)
            status = "[green]● Running[/green]" if (enabled and is_running) else (
                "[yellow]● Enabled[/yellow]" if enabled else "[bright_black]○ Disabled[/bright_black]"
            )
            port = str(proto_config.get('port', '-'))

            # Build URL
            if enabled and ips:
                if proto_name == 'smb':
                    url = f"\\\\{ips[0]}\\tools"
                else:
                    url = f"{proto_name}://{ips[0]}:{port}"
            else:
                url = "-"

            proto_table.add_row(proto_name.upper(), status, port, url)

        console.print(proto_table)

        # Configuration table
        console.print("\n[bold cyan]Configuration[/bold cyan]")
        info_table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
        info_table.add_column("Setting", style="cyan", width=18)
        info_table.add_column("Value")

        auth_status = f"[green]● Enabled[/green] [bright_black](User: {config.auth_username})[/bright_black]" if config.auth_enabled else "[bright_black]○ Disabled[/bright_black]"
        info_table.add_row("Authentication", auth_status)
        info_table.add_row("Tools Directory", f"[white]{config.tools_dir}[/white]")
        info_table.add_row("Uploads Directory", f"[white]{config.uploads_dir}[/white]")

        policy_desc = {
            'no': 'Never restart',
            'always': 'Always restart',
            'unless-stopped': 'Restart unless stopped',
            'on-failure': 'Restart on failure'
        }
        policy = config.restart_policy or 'unless-stopped'
        info_table.add_row("Restart Policy", f"[white]{policy}[/white]")

        console.print(info_table)

        # Quick commands hint
        if is_running:
            console.print("\n[dim]Commands: pftp stop | pftp logs | pftp restart[/dim]")
        else:
            console.print("\n[dim]Commands: pftp start | pftp configure | pftp remove[/dim]")

    except Exception as e:
        print_error(str(e))


@cli.command()
@click.option('--follow', '-f', is_flag=True, default=True, help='Follow log output')
@click.option('--lines', '-n', type=int, default=50, help='Number of lines to show')
def logs(follow, lines):
    """View pftp server logs"""

    config_path = get_config_path()
    if not config_path.exists():
        print_error("pftp is not installed. Run 'pftp install' first.")
        return

    config = Config.load(config_path)

    try:
        dm = DockerManager(config)
        dm.get_logs(follow=follow, lines=lines)
    except Exception as e:
        print_error(str(e))


@cli.command()
@click.option('--restart', 'do_restart', is_flag=True, help='Automatically restart after update')
def update(do_restart):
    """Update to latest Docker image"""

    config_path = get_config_path()
    if not config_path.exists():
        print_error("pftp is not installed. Run 'pftp install' first.")
        return

    config = Config.load(config_path)

    try:
        dm = DockerManager(config)
        was_running = dm.is_running()

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Updating PFTP", total=None)
            if dm.pull_image(config.docker_image):
                progress.update(task, description="[green]✓ PFTP updated[/green]")

                if was_running and do_restart:
                    progress.update(task, description="Restarting server")
                    dm.stop_container()
                    dm.remove_container()
                    dm.start_container()
                    progress.update(task, description="[green]✓ Server restarted[/green]")
                elif was_running:
                    console.print("\n[dim]Run 'pftp restart' to use the new version[/dim]")
            else:
                progress.update(task, description="[red]✗ Update failed[/red]")

    except Exception as e:
        print_error(str(e))


@cli.command()
@click.option('--keep-data', is_flag=True, default=True, help='Keep data directories')
@click.option('--purge', is_flag=True, help='Remove all data including tools and uploads')
def remove(keep_data, purge):
    """Uninstall pftp"""

    config_path = get_config_path()
    if not config_path.exists():
        print_warning("pftp is not installed")
        return

    config = Config.load(config_path)

    if purge:
        keep_data = False

    print_header("Uninstall PFTP", "Remove Container")
    console.print()

    try:
        dm = DockerManager(config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            console=console,
        ) as progress:
            if dm.is_running():
                task = progress.add_task("Removing PFTP", total=None)
                dm.stop_container()
            else:
                task = progress.add_task("Removing PFTP", total=None)

            dm.remove_container()
            progress.update(task, description="[green]✓ PFTP removed[/green]")

        if not keep_data:
            console.print()
            if Confirm.ask(f"[yellow]Remove all data from {config.data_dir}?[/yellow]", default=False):
                shutil.rmtree(config.data_dir)
                print_success(f"Removed {config.data_dir}")
            else:
                print_success(f"Data preserved in {config.data_dir}")
        else:
            print_success(f"Data preserved in {config.data_dir}")

        console.print()
        print_success("pftp uninstalled successfully")
        console.print("[dim]Run 'pftp install' to reinstall[/dim]")

    except Exception as e:
        print_error(str(e))


@cli.command()
@click.argument('source', type=click.Path(exists=True))
@click.option('--category', help='Subdirectory name in tools/')
@click.option('--recursive', '-r', is_flag=True, help='Copy directories recursively')
def add_tool(source, category, recursive):
    """Add file or directory to tools"""

    config_path = get_config_path()
    if not config_path.exists():
        print_error("pftp is not installed. Run 'pftp install' first.")
        return

    config = Config.load(config_path)
    source_path = Path(source).resolve()

    if category:
        dest_dir = config.tools_dir / category
    else:
        dest_dir = config.tools_dir

    dest_dir.mkdir(parents=True, exist_ok=True)

    if source_path.is_file():
        dest_file = dest_dir / source_path.name
        shutil.copy2(source_path, dest_file)
        print_success(f"Added: [cyan]{source_path.name}[/cyan]")
        console.print(f"  [bright_black]Location: {dest_dir}[/bright_black]")

    elif source_path.is_dir():
        if not recursive:
            print_error("Use --recursive (-r) to copy directories")
            return

        dest_subdir = dest_dir / source_path.name
        shutil.copytree(source_path, dest_subdir, dirs_exist_ok=True)
        print_success(f"Added directory: [cyan]{source_path.name}[/cyan]")
        console.print(f"  [bright_black]Location: {dest_dir}[/bright_black]")
    else:
        print_error(f"{source} is not a file or directory")
        return

    try:
        dm = DockerManager(config)
        if dm.is_running():
            console.print("  [green]•[/green] [bright_black]Tool is immediately available[/bright_black]")
    except:
        pass


@cli.command()
def version():
    """Show pftp version"""
    # print_logo()
    print_header("PFTP Version", "Current Version")


if __name__ == '__main__':
    cli()
