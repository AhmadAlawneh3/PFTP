"""Docker installation detection and guidance"""

import shutil
import docker
from docker.errors import DockerException


def is_docker_installed() -> bool:
    """Check if Docker CLI is installed

    Returns:
        True if docker command exists in PATH
    """
    return shutil.which("docker") is not None


def is_docker_running() -> bool:
    """Check if Docker daemon is accessible

    Returns:
        True if can connect to Docker daemon
    """
    try:
        client = docker.from_env()
        client.ping()
        return True
    except DockerException:
        return False


def get_install_instructions() -> str:
    """Get Docker installation instructions

    Returns:
        Formatted installation guide (Debian-focused with fallback)
    """
    return """Docker is not installed!

For Debian/Ubuntu/Kali Linux, run:

  sudo apt-get update
  sudo apt-get install -y docker.io
  sudo systemctl start docker
  sudo systemctl enable docker
  sudo usermod -aG docker $USER

Then logout and login (or run: newgrp docker) and retry: pftp install

For other platforms, see: https://docs.docker.com/get-docker/"""
