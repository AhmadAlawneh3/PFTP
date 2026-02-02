"""Configuration management for PFTP"""

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Dict
import yaml

from .constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_DATA_DIR,
    DEFAULT_DOCKER_IMAGE,
    CONTAINER_NAME,
    FTP_PORT,
    FTP_PASSIVE_START,
    FTP_PASSIVE_END,
    SMB_PORT,
    SMB_NETBIOS_PORT,
)


@dataclass
class Config:
    """PFTP configuration v2.0 with multi-protocol support"""

    # Server settings
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    # v2.0 Protocol configurations
    protocols: Dict = field(default_factory=lambda: {
        'http': {'enabled': True, 'port': DEFAULT_PORT},
        'ftp': {'enabled': True, 'port': FTP_PORT, 'passive_start': FTP_PASSIVE_START, 'passive_end': FTP_PASSIVE_END},
        'smb': {'enabled': True, 'port': SMB_PORT, 'netbios_port': SMB_NETBIOS_PORT}
    })

    # Authentication
    auth_enabled: bool = False
    auth_username: Optional[str] = None
    auth_password_hash: Optional[str] = None

    # Docker and directories
    docker_image: str = DEFAULT_DOCKER_IMAGE
    data_dir: Path = DEFAULT_DATA_DIR
    tools_dir: Optional[Path] = None
    uploads_dir: Optional[Path] = None
    ignore_dirs: str = ".git,__pycache__,.vscode"
    debug: bool = False

    # Docker restart policy: 'no', 'always', 'unless-stopped', 'on-failure'
    restart_policy: str = "unless-stopped"

    def __post_init__(self):
        """Initialize paths"""
        self.data_dir = Path(self.data_dir).expanduser()
        if not self.tools_dir:
            self.tools_dir = self.data_dir / "tools"
        if not self.uploads_dir:
            self.uploads_dir = self.data_dir / "uploads"

    @classmethod
    def load(cls, config_path: Path) -> 'Config':
        """Load configuration from YAML file with v1.0 to v2.0 migration"""
        if not config_path.exists():
            return cls()

        with open(config_path, 'r') as f:
            data = yaml.safe_load(f) or {}

        version = data.get('version', '1.0')

        # v1.0 config - migrate to v2.0
        if version == '1.0':
            http_port = data.get('server', {}).get('port', DEFAULT_PORT)
            config = cls(
                host=data.get('server', {}).get('host', DEFAULT_HOST),
                port=http_port,
                docker_image=data.get('docker', {}).get('image', DEFAULT_DOCKER_IMAGE),
                data_dir=Path(data.get('directories', {}).get('data_dir', DEFAULT_DATA_DIR)),
                ignore_dirs=data.get('advanced', {}).get('ignore_dirs', ".git,__pycache__,.vscode"),
                debug=data.get('advanced', {}).get('debug', False)
            )
            # Update HTTP port to match legacy config
            config.protocols['http']['port'] = http_port
            # Auto-save as v2.0
            config.save(config_path)
            return config

        # v2.0 config
        tools_dir_str = data.get('directories', {}).get('tools_dir')
        uploads_dir_str = data.get('directories', {}).get('uploads_dir')

        return cls(
            host=data.get('server', {}).get('host', DEFAULT_HOST),
            port=data.get('server', {}).get('port', DEFAULT_PORT),
            protocols=data.get('protocols', cls().protocols),
            auth_enabled=data.get('authentication', {}).get('enabled', False),
            auth_username=data.get('authentication', {}).get('username'),
            auth_password_hash=data.get('authentication', {}).get('password_hash'),
            docker_image=data.get('docker', {}).get('image', DEFAULT_DOCKER_IMAGE),
            data_dir=Path(data.get('directories', {}).get('data_dir', DEFAULT_DATA_DIR)),
            tools_dir=Path(tools_dir_str) if tools_dir_str else None,
            uploads_dir=Path(uploads_dir_str) if uploads_dir_str else None,
            ignore_dirs=data.get('advanced', {}).get('ignore_dirs', ".git,__pycache__,.vscode"),
            debug=data.get('advanced', {}).get('debug', False),
            restart_policy=data.get('docker', {}).get('restart_policy', 'unless-stopped')
        )

    def save(self, config_path: Path):
        """Save configuration to YAML file in v2.0 format"""
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'version': '2.0',
            'server': {
                'host': self.host,
                'port': self.port
            },
            'protocols': self.protocols,
            'authentication': {
                'enabled': self.auth_enabled,
                'username': self.auth_username,
                'password_hash': self.auth_password_hash
            },
            'docker': {
                'image': self.docker_image,
                'container_name': CONTAINER_NAME,
                'restart_policy': self.restart_policy
            },
            'directories': {
                'data_dir': str(self.data_dir),
                'tools_dir': str(self.tools_dir),
                'uploads_dir': str(self.uploads_dir),
                'permissions': {
                    'tools': 'ro',
                    'uploads': 'rw'
                }
            },
            'advanced': {
                'ignore_dirs': self.ignore_dirs,
                'debug': self.debug
            }
        }

        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

    def merge_cli_args(self, **kwargs):
        """Merge CLI arguments into configuration"""
        for key, value in kwargs.items():
            if value is not None and hasattr(self, key):
                setattr(self, key, value)
