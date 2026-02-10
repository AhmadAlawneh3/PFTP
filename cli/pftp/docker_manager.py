"""Docker container management for PFTP"""

import click
import docker
from docker.errors import DockerException, ImageNotFound, NotFound
from typing import Dict, Optional

from .config import Config
from .constants import CONTAINER_NAME


class DockerManager:
    """Manage PFTP Docker container"""

    def __init__(self, config: Config):
        """Initialize Docker manager

        Args:
            config: PFTP configuration
        """
        self.config = config
        try:
            self.client = docker.from_env()
        except DockerException as e:
            click.echo(f"Error: Cannot connect to Docker daemon. Is Docker running?", err=True)
            click.echo(f"Details: {e}", err=True)
            raise

    def pull_image(self, image_name: str) -> bool:
        """Pull Docker image from registry

        Args:
            image_name: Full image name (e.g., 'ahmadalawneh3/pftp:latest')

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.images.pull(image_name)
            return True
        except DockerException as e:
            return False

    def is_running(self) -> bool:
        """Check if container is running

        Returns:
            True if container exists and is running
        """
        try:
            container = self.client.containers.get(CONTAINER_NAME)
            return container.status == 'running'
        except NotFound:
            return False

    def start_container(self) -> bool:
        """Start PFTP container

        Returns:
            True if successful, False otherwise
        """
        # Check if container exists
        try:
            container = self.client.containers.get(CONTAINER_NAME)
            if container.status == 'running':
                return True
            # Container exists but not running - start it
            container.start()
            return True
        except NotFound:
            # Create new container
            return self._create_and_start()

    def _create_and_start(self) -> bool:
        """Create and start new container

        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare volume mappings
            volumes = {
                str(self.config.tools_dir): {'bind': '/app/data/tools', 'mode': 'rw'},
                str(self.config.uploads_dir): {'bind': '/app/data/uploads', 'mode': 'rw'},
            }

            # Prepare environment variables
            environment = {
                # General
                'PROTOCOL': 'http',
                'HOST': self.config.host,
                'PORT': str(self.config.port),
                'DEBUG': 'false',
                'UPLOAD_FOLDER': 'data/uploads',
                'TOOLS_FOLDER': 'data/tools',
                'IGNORE_DIRS': '.git,__pycache__,.vscode',

                # HTTP
                'HTTP_ENABLED': str(self.config.protocols.get('http', {}).get('enabled', True)).lower(),
                'HTTP_PORT': str(self.config.protocols.get('http', {}).get('port', 1234)),

                # FTP
                'FTP_ENABLED': str(self.config.protocols.get('ftp', {}).get('enabled', True)).lower(),
                'FTP_PORT': str(self.config.protocols.get('ftp', {}).get('port', 21)),
                'FTP_PASSIVE_START': str(self.config.protocols.get('ftp', {}).get('passive_start', 60000)),
                'FTP_PASSIVE_END': str(self.config.protocols.get('ftp', {}).get('passive_end', 60100)),

                # SMB
                'SMB_ENABLED': str(self.config.protocols.get('smb', {}).get('enabled', True)).lower(),
                'SMB_PORT': str(self.config.protocols.get('smb', {}).get('port', 445)),
                'SMB_NETBIOS_PORT': str(self.config.protocols.get('smb', {}).get('netbios_port', 139)),

                # Authentication
                'AUTH_ENABLED': str(self.config.auth_enabled).lower(),
                'AUTH_USERNAME': self.config.auth_username or '',
                'AUTH_PASSWORD_HASH': self.config.auth_password_hash or '',
            }

            # Prepare restart policy
            restart_policy_name = self.config.restart_policy or 'unless-stopped'
            restart_policy = {'Name': restart_policy_name}
            if restart_policy_name == 'on-failure':
                restart_policy['MaximumRetryCount'] = 5

            # Create and start container
            container = self.client.containers.run(
                self.config.docker_image,
                name=CONTAINER_NAME,
                volumes=volumes,
                environment=environment,
                network_mode='host',  # Required for IP detection
                restart_policy=restart_policy,
                cap_add=['NET_BIND_SERVICE'],  # Allow binding to privileged ports
                detach=True,
                stdin_open=True,
                tty=True
            )

            return True

        except ImageNotFound:
            return False
        except DockerException as e:
            return False

    def stop_container(self) -> bool:
        """Stop container

        Returns:
            True if successful, False otherwise
        """
        try:
            container = self.client.containers.get(CONTAINER_NAME)
            container.stop(timeout=10)
            return True
        except NotFound:
            return False
        except DockerException as e:
            return False

    def remove_container(self) -> bool:
        """Remove container

        Returns:
            True if successful, False otherwise
        """
        try:
            container = self.client.containers.get(CONTAINER_NAME)
            container.remove(force=True)
            return True
        except NotFound:
            # Already removed
            return True
        except DockerException as e:
            return False

    def get_logs(self, follow: bool = True, lines: int = 50):
        """Get container logs

        Args:
            follow: Stream logs (like tail -f)
            lines: Number of lines to show
        """
        try:
            container = self.client.containers.get(CONTAINER_NAME)
            if follow:
                click.echo(click.style(f"Following logs from '{CONTAINER_NAME}' (Ctrl+C to stop)...", fg='cyan'))
                buffer = b''
                for chunk in container.logs(stream=True, follow=True, tail=lines):
                    if isinstance(chunk, bytes):
                        buffer += chunk
                    else:
                        buffer += chunk.encode('utf-8')
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        click.echo(line.decode('utf-8', errors='replace').rstrip())
                if buffer:
                    click.echo(buffer.decode('utf-8', errors='replace').rstrip())
            else:
                # Get logs as bytes, decode to string
                logs_bytes = container.logs(tail=lines)
                if isinstance(logs_bytes, bytes):
                    click.echo(logs_bytes.decode('utf-8', errors='replace'))
                else:
                    click.echo(str(logs_bytes))
        except NotFound:
            click.echo(click.style(f"Container '{CONTAINER_NAME}' not found", fg='red'), err=True)
        except KeyboardInterrupt:
            click.echo(click.style("\n✓ Stopped following logs", fg='green'))
        except DockerException as e:
            click.echo(click.style(f"Error getting logs: {e}", fg='red'), err=True)

    def get_status(self) -> Optional[Dict]:
        """Get container status information

        Returns:
            Dictionary with container info or None if not found
        """
        try:
            container = self.client.containers.get(CONTAINER_NAME)
            return {
                'status': container.status,
                'id': container.short_id,
                'image': container.image.tags[0] if container.image.tags else 'unknown',
                'created': container.attrs['Created'],
                'ports': container.attrs.get('NetworkSettings', {}).get('Ports', {})
            }
        except NotFound:
            return {'status': 'not_found'}
        except DockerException as e:
            return None
