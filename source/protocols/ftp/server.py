"""FTP server implementation using pyftpdlib"""

import os
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer as PyFTPDServer

from ..base_server import BaseServer


class FTPServer(BaseServer):
    """FTP server with anonymous access and directory permissions"""

    def get_name(self) -> str:
        return "FTP"

    def get_port(self) -> int:
        return int(self.config.get('FTP_PORT', 21))

    def is_enabled(self) -> bool:
        return self.config.get('FTP_ENABLED', 'true').lower() == 'true'

    def start(self):
        """Start the FTP server with pyftpdlib"""
        try:
            # Get configuration
            host = self.config.get('HOST', '0.0.0.0')
            port = self.get_port()
            passive_start = int(self.config.get('FTP_PASSIVE_START', 60000))
            passive_end = int(self.config.get('FTP_PASSIVE_END', 60100))

            # Use /app/data as FTP root (contains tools and uploads subdirectories)
            ftp_root = '/app/data'
            tools_dir = os.path.join(ftp_root, 'tools')
            uploads_dir = os.path.join(ftp_root, 'uploads')

            # Ensure directories exist
            os.makedirs(tools_dir, exist_ok=True)
            os.makedirs(uploads_dir, exist_ok=True)

            self.log_info(f"FTP root directory: {ftp_root}")
            self.log_info(f"FTP tools directory: {tools_dir} (read-only)")
            self.log_info(f"FTP uploads directory: {uploads_dir} (read-write)")

            # Create authorizer with /app/data as home directory
            authorizer = DummyAuthorizer()

            # Check if authentication is enabled
            auth_enabled = self.config.get('AUTH_ENABLED', 'false').lower() == 'true'
            auth_username = self.config.get('AUTH_USERNAME')
            auth_password = self.config.get('AUTH_PASSWORD_HASH')  # For now, treat as plaintext password

            if auth_enabled and auth_username and auth_password:
                # Add authenticated user with read-only access by default
                # Permissions: e=CWD, l=LIST, r=RETRIEVE (read-only)
                authorizer.add_user(auth_username, auth_password, homedir=ftp_root, perm='elr')

                # Override uploads directory to read-write for authenticated user
                authorizer.override_perm(
                    username=auth_username,
                    directory=uploads_dir,
                    perm='elradfmw',
                    recursive=True
                )
                self.log_info(f"FTP authentication ENABLED - user: {auth_username}")
            else:
                # Add anonymous user with read-only access by default
                # Permissions: e=CWD, l=LIST, r=RETRIEVE (read-only)
                authorizer.add_anonymous(homedir=ftp_root, perm='elr')

                # Override uploads directory to read-write for anonymous
                authorizer.override_perm(
                    username='anonymous',
                    directory=uploads_dir,
                    perm='elradfmw',
                    recursive=True
                )
                self.log_info(f"FTP authentication DISABLED - anonymous access enabled")

            # Configure handler
            handler = FTPHandler
            handler.authorizer = authorizer

            # Set passive port range
            handler.passive_ports = range(passive_start, passive_end + 1)

            # Banner
            handler.banner = "PFTP Multi-Protocol Server - FTP Service"

            # Create FTP server
            server = PyFTPDServer((host, port), handler)

            # Set max connections
            server.max_cons = 256
            server.max_cons_per_ip = 10

            self.log_info(f"FTP server starting on {host}:{port}")
            self.log_info(f"FTP passive ports: {passive_start}-{passive_end}")
            self.log_info(f"FTP anonymous access enabled")
            self.log_info(f"FTP tools directory: READ-ONLY")
            self.log_info(f"FTP uploads directory: READ-WRITE")

            # Start serving (blocking call)
            server.serve_forever()

        except Exception as e:
            self.log_error(f"Failed to start FTP server: {e}")
            import traceback
            traceback.print_exc()
            raise
