"""PFTP CLI commands"""

import click
import shutil
import subprocess
import re
from pathlib import Path

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


def get_config_path(data_dir: Path = None) -> Path:
    """Get configuration file path"""
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    return Path(data_dir) / CONFIG_DIR / CONFIG_FILE


def hash_password(password: str) -> str:
    """Return password as-is for multi-protocol compatibility.

    FTP and SMB protocols need the plaintext password to compute
    their own authentication hashes (NTLM, etc). Bcrypt is one-way
    and incompatible with these protocols.
    """
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
            # Match interface name
            if_match = re.match(r'^\d+:\s+(\S+):', line)
            if if_match:
                current_interface = if_match.group(1)

            # Match IPv4 address
            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
            if ip_match and current_interface:
                ip = ip_match.group(1)
                # Skip localhost
                if ip != '127.0.0.1':
                    # Priority system:
                    # 0 = tun interfaces (VPN/pentest)
                    # 1 = eth interfaces (ethernet)
                    # 2 = wlan interfaces (wifi)
                    # 3 = other interfaces
                    if current_interface.startswith('tun'):
                        priority = 0
                    elif current_interface.startswith('eth'):
                        priority = 1
                    elif current_interface.startswith('wlan'):
                        priority = 2
                    else:
                        priority = 3

                    ips.append((priority, ip, current_interface))

        # Sort by priority and return IPs
        ips.sort()
        return [ip for _, ip, _ in ips]
    except Exception:
        return []


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
@click.option('--skip-pull', is_flag=True, help='Skip pulling Docker image')
def install(yes, data_dir, tools_dir, uploads_dir, http_port, ftp_port,
            enable_ftp, enable_smb, auth, auth_username, auth_password,
            restart_policy, skip_pull):
    """Install and configure pftp"""

    click.echo(click.style("=== PFTP Installation ===\n", fg='cyan', bold=True))

    # Data directory
    if not data_dir:
        if yes:
            data_dir = str(DEFAULT_DATA_DIR)
        else:
            data_dir = click.prompt('Data directory',
                                   default=str(DEFAULT_DATA_DIR),
                                   type=click.Path())

    data_dir = Path(data_dir).expanduser()

    # Interactive configuration (skip if --yes)
    if not yes:
        click.echo(f"\n{click.style('Protocol Configuration:', fg='yellow', bold=True)}")

        # HTTP configuration
        if http_port is None:
            http_port = click.prompt('HTTP port', default=DEFAULT_PORT, type=int)

        # FTP configuration
        if enable_ftp is None:
            enable_ftp = click.confirm('Enable FTP server', default=True)

        if enable_ftp and ftp_port is None:
            ftp_port = click.prompt('FTP port', default=FTP_PORT, type=int)

        # SMB configuration
        if enable_smb is None:
            enable_smb = click.confirm('Enable SMB server', default=False)

        # Directory configuration
        click.echo(f"\n{click.style('Directory Configuration:', fg='yellow', bold=True)}")

        if tools_dir is None:
            if click.confirm('Use custom tools directory', default=False):
                tools_dir = click.prompt('Tools directory path', type=click.Path())

        if uploads_dir is None:
            if click.confirm('Use custom uploads directory', default=False):
                uploads_dir = click.prompt('Uploads directory path', type=click.Path())

        # Authentication configuration
        click.echo(f"\n{click.style('Authentication Configuration:', fg='yellow', bold=True)}")
        if auth is None:
            auth = click.confirm('Enable authentication', default=False)
        if auth:
            if auth_username is None:
                auth_username = click.prompt('Username', default='admin')
            if auth_password is None:
                auth_password = click.prompt('Password', hide_input=True)

        # Docker configuration
        click.echo(f"\n{click.style('Docker Configuration:', fg='yellow', bold=True)}")
        if restart_policy is None:
            if click.confirm('Configure restart policy', default=False):
                click.echo("  Options:")
                click.echo("    no             - Never restart automatically")
                click.echo("    always         - Always restart (even after reboot)")
                click.echo("    unless-stopped - Restart unless manually stopped (default)")
                click.echo("    on-failure     - Restart only if container exits with error")
                restart_policy = click.prompt('Restart policy',
                    type=click.Choice(['no', 'always', 'unless-stopped', 'on-failure']),
                    default='unless-stopped')
    else:
        # Use defaults for --yes mode
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
    click.echo(f"\n{click.style('Creating directories...', fg='cyan')}")
    tools_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"✓ Created {data_dir}")
    if tools_dir != data_dir / TOOLS_DIR:
        click.echo(f"✓ Tools directory: {tools_dir}")
    if uploads_dir != data_dir / UPLOADS_DIR:
        click.echo(f"✓ Uploads directory: {uploads_dir}")

    # Create configuration
    config = Config(
        port=http_port,
        data_dir=data_dir,
        tools_dir=tools_dir if tools_dir != data_dir / TOOLS_DIR else None,
        uploads_dir=uploads_dir if uploads_dir != data_dir / UPLOADS_DIR else None,
    )

    # Configure protocols
    config.protocols['http']['port'] = http_port
    config.protocols['ftp']['enabled'] = enable_ftp
    config.protocols['ftp']['port'] = ftp_port if ftp_port else FTP_PORT
    config.protocols['smb']['enabled'] = enable_smb

    # Authentication
    if auth:
        config.auth_enabled = True
        config.auth_username = auth_username or 'admin'
        config.auth_password_hash = hash_password(auth_password) if auth_password else ''

    # Restart policy
    if restart_policy:
        config.restart_policy = restart_policy

    config_path = get_config_path(data_dir)
    config.save(config_path)
    click.echo(f"✓ Configuration saved to {config_path}")

    # Pull Docker image
    if not skip_pull:
        click.echo(f"\nPulling Docker image...")
        try:
            dm = DockerManager(config)
            dm.pull_image(config.docker_image)
        except Exception as e:
            click.echo(f"Warning: Could not pull image: {e}", err=True)
            click.echo("You can pull it later with: pftp update")

    click.echo(click.style(f"\n✓ Installation complete!", fg='green', bold=True))
    click.echo(f"\n{click.style('Next steps:', fg='cyan', bold=True)}")
    click.echo(f"  1. Add tools to {click.style(str(tools_dir), fg='yellow')}")
    click.echo(f"  2. Run: {click.style('pftp start', fg='green')}")

    # Show actual IPs if available
    ips = get_local_ips()
    if ips:
        click.echo(f"  3. Access the web UI at:")
        for ip in ips:
            click.echo(f"     {click.style(f'http://{ip}:{http_port}', fg='cyan', bold=True)}")
    else:
        click.echo(f"  3. Access the web UI at {click.style(f'http://<your-ip>:{http_port}', fg='cyan')}")


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
    """Reconfigure pftp settings (interactive if no options provided)"""

    config_path = get_config_path()
    if not config_path.exists():
        click.echo("Error: pftp is not installed. Run 'pftp install' first.", err=True)
        return

    # Load current config
    config = Config.load(config_path)

    # Check if any CLI flags were provided
    has_flags = any([
        enable_http is not None, enable_ftp is not None, enable_smb is not None,
        http_port is not None, ftp_port is not None, smb_port is not None,
        auth is not None, auth_username is not None, auth_password is not None,
        tools_dir is not None, uploads_dir is not None, restart_policy is not None
    ])

    # If no flags provided, run interactive mode
    if not has_flags:
        click.echo(click.style("=== Current Configuration ===", fg='cyan', bold=True))
        click.echo(f"\n{click.style('General:', fg='yellow', bold=True)}")
        click.echo(f"  Data directory: {config.data_dir}")
        click.echo(f"  Tools directory: {config.tools_dir}")
        click.echo(f"  Uploads directory: {config.uploads_dir}")
        click.echo(f"  Docker image: {config.docker_image}")

        click.echo(f"\n{click.style('Protocols:', fg='yellow', bold=True)}")
        for proto_name, proto_config in config.protocols.items():
            status = click.style('✓ Enabled', fg='green') if proto_config.get('enabled') else click.style('✗ Disabled', fg='red')
            click.echo(f"  {proto_name.upper()}: {status}")
            click.echo(f"    Port: {proto_config.get('port')}")
            if proto_name == 'ftp':
                click.echo(f"    Passive ports: {proto_config.get('passive_start')}-{proto_config.get('passive_end')}")
            elif proto_name == 'smb':
                click.echo(f"    NetBIOS port: {proto_config.get('netbios_port')}")

        click.echo(f"\n{click.style('Authentication:', fg='yellow', bold=True)}")
        if config.auth_enabled:
            click.echo(f"  Status: {click.style('✓ Enabled', fg='green')}")
            click.echo(f"  Username: {config.auth_username}")
        else:
            click.echo(f"  Status: {click.style('✗ Disabled', fg='red')}")

        click.echo(f"\n{click.style('Docker:', fg='yellow', bold=True)}")
        policy_desc = {
            'no': 'Never restart',
            'always': 'Always restart',
            'unless-stopped': 'Restart unless stopped manually',
            'on-failure': 'Restart on failure only'
        }
        click.echo(f"  Restart policy: {config.restart_policy} ({policy_desc.get(config.restart_policy, '')})")

        click.echo(f"\n{click.style('=== Reconfigure Settings ===', fg='cyan', bold=True)}")
        click.echo(click.style("Press Ctrl+C to cancel at any time\n", fg='yellow'))

        try:
            # Protocol configuration
            click.echo(click.style('Protocol Settings:', fg='yellow', bold=True))
            config.protocols['http']['enabled'] = click.confirm('Enable HTTP', default=config.protocols['http']['enabled'])
            if config.protocols['http']['enabled']:
                config.protocols['http']['port'] = click.prompt('HTTP port',
                    default=config.protocols['http']['port'], type=int)
                config.port = config.protocols['http']['port']  # Update legacy

            config.protocols['ftp']['enabled'] = click.confirm('Enable FTP', default=config.protocols['ftp']['enabled'])
            if config.protocols['ftp']['enabled']:
                config.protocols['ftp']['port'] = click.prompt('FTP port',
                    default=config.protocols['ftp']['port'], type=int)

            config.protocols['smb']['enabled'] = click.confirm('Enable SMB', default=config.protocols['smb']['enabled'])
            if config.protocols['smb']['enabled']:
                config.protocols['smb']['port'] = click.prompt('SMB port',
                    default=config.protocols['smb']['port'], type=int)

            # Authentication
            click.echo(f"\n{click.style('Authentication Settings:', fg='yellow', bold=True)}")
            config.auth_enabled = click.confirm('Enable authentication', default=config.auth_enabled)
            if config.auth_enabled:
                config.auth_username = click.prompt('Username',
                    default=config.auth_username or 'admin')
                new_password = click.prompt('Password (leave empty to keep current)',
                    default='', hide_input=True, show_default=False)
                if new_password:
                    config.auth_password_hash = hash_password(new_password)
                    click.echo(click.style('  ✓ Password set', fg='green'))

            # Directory configuration
            click.echo(f"\n{click.style('Directory Settings:', fg='yellow', bold=True)}")
            if click.confirm('Configure custom tools directory', default=False):
                from pathlib import Path
                tools_path = click.prompt('Tools directory path',
                    default=str(config.tools_dir), type=str)
                config.tools_dir = Path(tools_path)
                config.tools_dir.mkdir(parents=True, exist_ok=True)

            if click.confirm('Configure custom uploads directory', default=False):
                from pathlib import Path
                uploads_path = click.prompt('Uploads directory path',
                    default=str(config.uploads_dir), type=str)
                config.uploads_dir = Path(uploads_path)
                config.uploads_dir.mkdir(parents=True, exist_ok=True)

            # Docker settings
            click.echo(f"\n{click.style('Docker Settings:', fg='yellow', bold=True)}")
            if click.confirm('Configure restart policy', default=False):
                click.echo("  Options:")
                click.echo("    no             - Never restart automatically")
                click.echo("    always         - Always restart (even after reboot)")
                click.echo("    unless-stopped - Restart unless manually stopped (default)")
                click.echo("    on-failure     - Restart only if container exits with error")
                config.restart_policy = click.prompt('Restart policy',
                    type=click.Choice(['no', 'always', 'unless-stopped', 'on-failure']),
                    default=config.restart_policy)

            config.save(config_path)
            click.echo(click.style(f"\n✓ Configuration updated", fg='green', bold=True))

            # Check if we're on Windows (PowerShell doesn't support &&)
            import platform
            if platform.system() == 'Windows':
                click.echo(f"Directory changes require container recreation:")
                click.echo(f"  1. {click.style('pftp remove', fg='cyan')}")
                click.echo(f"  2. {click.style('pftp start', fg='cyan')}")
            else:
                click.echo(f"Run '{click.style('pftp remove && pftp start', fg='cyan')}' to recreate container")

            click.echo(f"For other changes, run '{click.style('pftp restart', fg='cyan')}'")

        except click.Abort:
            click.echo(click.style("\n✗ Configuration cancelled", fg='yellow'))
            return

    else:
        # Non-interactive mode with CLI flags
        click.echo("=== Reconfigure PFTP ===\n")

        # Protocol enable/disable flags
        if enable_http is not None:
            config.protocols['http']['enabled'] = enable_http
            click.echo(f"{'Enabled' if enable_http else 'Disabled'} HTTP protocol")

        if enable_ftp is not None:
            config.protocols['ftp']['enabled'] = enable_ftp
            click.echo(f"{'Enabled' if enable_ftp else 'Disabled'} FTP protocol")

        if enable_smb is not None:
            config.protocols['smb']['enabled'] = enable_smb
            click.echo(f"{'Enabled' if enable_smb else 'Disabled'} SMB protocol")

        # Port configuration
        if http_port is not None:
            config.protocols['http']['port'] = http_port
            config.port = http_port  # Update legacy port
            click.echo(f"Set HTTP port to {http_port}")

        if ftp_port is not None:
            config.protocols['ftp']['port'] = ftp_port
            click.echo(f"Set FTP port to {ftp_port}")

        if smb_port is not None:
            config.protocols['smb']['port'] = smb_port
            click.echo(f"Set SMB port to {smb_port}")

        # Authentication
        if auth is not None:
            config.auth_enabled = auth
            click.echo(f"{'Enabled' if auth else 'Disabled'} authentication")

        if auth_username is not None:
            config.auth_username = auth_username
            click.echo(f"Set authentication username to {auth_username}")

        if auth_password is not None:
            config.auth_password_hash = hash_password(auth_password)
            click.echo(f"Set authentication password")

        # Directory configuration
        dirs_changed = False
        if tools_dir is not None:
            from pathlib import Path
            config.tools_dir = Path(tools_dir)
            config.tools_dir.mkdir(parents=True, exist_ok=True)
            click.echo(f"Set tools directory to {tools_dir}")
            dirs_changed = True

        if uploads_dir is not None:
            from pathlib import Path
            config.uploads_dir = Path(uploads_dir)
            config.uploads_dir.mkdir(parents=True, exist_ok=True)
            click.echo(f"Set uploads directory to {uploads_dir}")
            dirs_changed = True

        # Docker settings
        if restart_policy is not None:
            config.restart_policy = restart_policy
            click.echo(f"Set restart policy to {restart_policy}")

        config.save(config_path)

        click.echo(click.style(f"\n✓ Configuration updated", fg='green', bold=True))
        if dirs_changed:
            import platform
            if platform.system() == 'Windows':
                click.echo(f"Directory changes require container recreation:")
                click.echo(f"  1. {click.style('pftp remove', fg='cyan')}")
                click.echo(f"  2. {click.style('pftp start', fg='cyan')}")
            else:
                click.echo(f"Directory changes require container recreation:")
                click.echo(f"  Run '{click.style('pftp remove && pftp start', fg='cyan')}'")
        else:
            click.echo(f"Run '{click.style('pftp restart', fg='cyan')}' to apply changes")


@cli.command()
@click.option('--detach', '-d', is_flag=True, default=True, help='Run in background')
@click.option('--port', type=int, help='Override config port')
@click.option('--foreground', is_flag=True, help='Run in foreground (show logs)')
def start(detach, port, foreground):
    """Start pftp server"""

    config_path = get_config_path()
    if not config_path.exists():
        click.echo("Error: pftp is not installed. Run 'pftp install' first.", err=True)
        return

    config = Config.load(config_path)

    # Override port if specified
    if port:
        config.port = port

    # Ensure directories exist
    config.tools_dir.mkdir(parents=True, exist_ok=True)
    config.uploads_dir.mkdir(parents=True, exist_ok=True)

    try:
        dm = DockerManager(config)

        if dm.is_running():
            click.echo("pftp is already running")
            click.echo("Run 'pftp status' for details")
            return

        if dm.start_container():
            if foreground:
                dm.get_logs(follow=True)
        else:
            click.echo("Failed to start container", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
def stop():
    """Stop pftp server"""

    config_path = get_config_path()
    if not config_path.exists():
        click.echo("Error: pftp is not installed. Run 'pftp install' first.", err=True)
        return

    config = Config.load(config_path)

    try:
        dm = DockerManager(config)
        dm.stop_container()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
def restart():
    """Restart pftp server"""

    config_path = get_config_path()
    if not config_path.exists():
        click.echo(click.style("Error: pftp is not installed. Run 'pftp install' first.", fg='red'), err=True)
        return

    config = Config.load(config_path)

    try:
        dm = DockerManager(config)

        click.echo(click.style("Stopping container...", fg='yellow'))
        dm.stop_container()

        click.echo(click.style("Removing old container...", fg='yellow'))
        dm.remove_container()

        click.echo(click.style("Starting container with new configuration...", fg='yellow'))
        dm.start_container()
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)


@cli.command()
def status():
    """Show pftp status and configuration"""

    config_path = get_config_path()
    if not config_path.exists():
        click.echo(click.style("pftp is not installed", fg='yellow'))
        click.echo(f"Run '{click.style('pftp install', fg='green')}' to get started")
        return

    config = Config.load(config_path)

    click.echo(click.style("=== PFTP Status ===\n", fg='cyan', bold=True))

    try:
        dm = DockerManager(config)
        status_info = dm.get_status()

        if status_info and status_info.get('status') != 'not_found':
            status_color = 'green' if status_info['status'] == 'running' else 'yellow'
            click.echo(f"Status: {click.style(status_info['status'], fg=status_color, bold=True)}")
            click.echo(f"Container ID: {click.style(status_info['id'], fg='cyan')}")
            click.echo(f"Image: {click.style(status_info['image'], fg='cyan')}")

            if status_info['status'] == 'running':
                ips = get_local_ips()
                if ips:
                    click.echo(f"\n{click.style('Server URLs:', fg='green', bold=True)}")
                    for ip in ips:
                        click.echo(f"  {click.style(f'http://{ip}:{config.port}', fg='cyan', bold=True)}")
                else:
                    click.echo(f"\nServer: {click.style(f'http://<your-ip>:{config.port}', fg='cyan')}")
        else:
            click.echo(f"Status: {click.style('not running', fg='red')}")

        click.echo(f"\n{click.style('=== Configuration ===', fg='cyan', bold=True)}")

        # Show protocol status
        click.echo(f"\n{click.style('Protocols:', fg='yellow', bold=True)}")
        for proto_name, proto_config in config.protocols.items():
            enabled = proto_config.get('enabled', True)
            status_icon = click.style('✓', fg='green') if enabled else click.style('✗', fg='red')
            port = proto_config.get('port')

            if enabled and status_info and status_info.get('status') == 'running':
                ips = get_local_ips()
                if ips and ips[0]:
                    url = f"{proto_name}://{ips[0]}:{port}"
                    click.echo(f"  {status_icon} {proto_name.upper()}: {click.style(url, fg='cyan', bold=True)}")
                else:
                    click.echo(f"  {status_icon} {proto_name.upper()}: Port {port}")
            else:
                state = "Enabled" if enabled else "Disabled"
                click.echo(f"  {status_icon} {proto_name.upper()}: {state} (Port {port})")

        # Show authentication status
        click.echo(f"\n{click.style('Authentication:', fg='yellow', bold=True)}")
        if config.auth_enabled:
            click.echo(f"  {click.style('✓', fg='green')} Enabled (User: {config.auth_username})")
        else:
            click.echo(f"  {click.style('✗', fg='red')} Disabled")

        # Show directories
        click.echo(f"\n{click.style('Directories:', fg='yellow', bold=True)}")
        click.echo(f"  Data: {click.style(str(config.data_dir), fg='cyan')}")
        click.echo(f"  Tools: {click.style(str(config.tools_dir), fg='cyan')}")
        click.echo(f"  Uploads: {click.style(str(config.uploads_dir), fg='cyan')}")

        # Show Docker settings
        click.echo(f"\n{click.style('Docker:', fg='yellow', bold=True)}")
        policy_desc = {
            'no': 'Never restart',
            'always': 'Always restart',
            'unless-stopped': 'Restart unless stopped',
            'on-failure': 'Restart on failure'
        }
        policy = config.restart_policy or 'unless-stopped'
        click.echo(f"  Restart policy: {click.style(policy, fg='cyan')} ({policy_desc.get(policy, '')})")

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)


@cli.command()
@click.option('--follow', '-f', is_flag=True, default=True, help='Follow log output')
@click.option('--lines', '-n', type=int, default=50, help='Number of lines to show')
def logs(follow, lines):
    """View pftp server logs"""

    config_path = get_config_path()
    if not config_path.exists():
        click.echo("Error: pftp is not installed. Run 'pftp install' first.", err=True)
        return

    config = Config.load(config_path)

    try:
        dm = DockerManager(config)
        dm.get_logs(follow=follow, lines=lines)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--restart', is_flag=True, help='Automatically restart after update')
def update(restart):
    """Update to latest Docker image"""

    config_path = get_config_path()
    if not config_path.exists():
        click.echo("Error: pftp is not installed. Run 'pftp install' first.", err=True)
        return

    config = Config.load(config_path)

    try:
        dm = DockerManager(config)

        # Check if running
        was_running = dm.is_running()

        # Pull latest image
        if dm.pull_image(config.docker_image):
            if was_running and restart:
                click.echo("\nRestarting with new image...")
                dm.stop_container()
                dm.start_container()
            elif was_running:
                click.echo("\nRun 'pftp restart' to use the new image")
        else:
            click.echo("Update failed", err=True)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--keep-data', is_flag=True, default=True, help='Keep data directories')
@click.option('--purge', is_flag=True, help='Remove all data including tools and uploads')
def remove(keep_data, purge):
    """Uninstall pftp"""

    config_path = get_config_path()
    if not config_path.exists():
        click.echo("pftp is not installed")
        return

    config = Config.load(config_path)

    if purge:
        keep_data = False

    click.echo("=== Uninstalling PFTP ===\n")

    try:
        dm = DockerManager(config)

        # Stop and remove container
        if dm.is_running():
            click.echo("Stopping container...")
            dm.stop_container()

        click.echo("Removing container...")
        dm.remove_container()

        # Remove data if requested
        if not keep_data:
            if click.confirm(f"Remove all data from {config.data_dir}?", default=False):
                shutil.rmtree(config.data_dir)
                click.echo(f"✓ Removed {config.data_dir}")
        else:
            click.echo(f"✓ Data preserved in {config.data_dir}")

        click.echo("\n✓ pftp uninstalled")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument('source', type=click.Path(exists=True))
@click.option('--category', help='Subdirectory name in tools/')
@click.option('--recursive', '-r', is_flag=True, help='Copy directories recursively')
def add_tool(source, category, recursive):
    """Add file or directory to tools"""

    config_path = get_config_path()
    if not config_path.exists():
        click.echo(click.style("Error: pftp is not installed. Run 'pftp install' first.", fg='red'), err=True)
        return

    config = Config.load(config_path)
    source_path = Path(source).resolve()

    # Determine destination
    if category:
        dest_dir = config.tools_dir / category
    else:
        dest_dir = config.tools_dir

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Handle file or directory
    if source_path.is_file():
        dest_file = dest_dir / source_path.name
        shutil.copy2(source_path, dest_file)
        click.echo(click.style(f"✓ Copied: {source_path.name} → {dest_dir}", fg='green'))

    elif source_path.is_dir():
        if not recursive:
            click.echo(click.style("Error: Use --recursive to copy directories", fg='red'), err=True)
            return

        dest_subdir = dest_dir / source_path.name
        shutil.copytree(source_path, dest_subdir, dirs_exist_ok=True)
        click.echo(click.style(f"✓ Copied directory: {source_path.name} → {dest_dir}", fg='green'))
    else:
        click.echo(click.style(f"Error: {source} is not a file or directory", fg='red'), err=True)
        return

    # Notify if container is running
    try:
        dm = DockerManager(config)
        if dm.is_running():
            click.echo(click.style("✓ Container is running - new tools are immediately available", fg='green'))
    except:
        pass


@cli.command()
def version():
    """Show pftp version"""
    click.echo(f"pftp version {__version__}")


if __name__ == '__main__':
    cli()
