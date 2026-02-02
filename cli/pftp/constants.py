"""Constants and default values for PFTP"""

from pathlib import Path

# Default configuration values
DEFAULT_PORT = 1234
DEFAULT_HOST = "0.0.0.0"
DEFAULT_DATA_DIR = Path.home() / ".pftp"
DEFAULT_DOCKER_IMAGE = "ahmadalawneh3/pftp:latest"

# Protocol ports
FTP_PORT = 21
FTP_PASSIVE_START = 60000
FTP_PASSIVE_END = 60100
SMB_PORT = 445
SMB_NETBIOS_PORT = 139

# Container and config settings
CONTAINER_NAME = "pftp"
CONFIG_FILE = "config.yaml"
CONFIG_DIR = "config"
TOOLS_DIR = "tools"
UPLOADS_DIR = "uploads"

# Docker environment variables
ENV_PROTOCOL = "PROTOCOL"
ENV_HOST = "HOST"
ENV_PORT = "PORT"
ENV_DEBUG = "DEBUG"
ENV_UPLOAD_FOLDER = "UPLOAD_FOLDER"
ENV_TOOLS_FOLDER = "TOOLS_FOLDER"
ENV_IGNORE_DIRS = "IGNORE_DIRS"
