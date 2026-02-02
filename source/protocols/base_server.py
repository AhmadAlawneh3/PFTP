"""Base server class for all protocol implementations"""

from abc import ABC, abstractmethod
import logging
import os


class BaseServer(ABC):
    """Abstract base class for protocol servers"""

    def __init__(self, config: dict):
        """
        Initialize the server with configuration

        Args:
            config: Dictionary containing server configuration from environment
        """
        self.config = config
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logger for this server"""
        logger = logging.Logger(self.get_name())
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f'[{self.get_name()}] %(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this server (e.g., 'HTTP', 'FTP', 'SMB')"""
        pass

    @abstractmethod
    def get_port(self) -> int:
        """Get the port this server will listen on"""
        pass

    @abstractmethod
    def start(self):
        """Start the server (blocking call)"""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if this server is enabled in configuration"""
        pass

    def get_tools_dir(self) -> str:
        """Get the tools directory path"""
        return self.config.get('TOOLS_FOLDER', 'tools')

    def get_uploads_dir(self) -> str:
        """Get the uploads directory path"""
        return self.config.get('UPLOAD_FOLDER', 'uploads')

    def get_auth_config(self) -> dict:
        """Get authentication configuration"""
        return {
            'enabled': self.config.get('AUTH_ENABLED', 'false').lower() == 'true',
            'username': self.config.get('AUTH_USERNAME'),
            'password_hash': self.config.get('AUTH_PASSWORD_HASH')
        }

    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)

    def log_error(self, message: str):
        """Log error message"""
        self.logger.error(message)

    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
