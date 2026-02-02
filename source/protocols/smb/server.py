"""SMB server implementation using impacket"""

import os
from impacket import smbserver
from impacket.smbserver import SimpleSMBServer

from ..base_server import BaseServer


class SMBServer(BaseServer):
    """SMB server with two shares: tools (read-only) and uploads (read-write)"""

    def get_name(self) -> str:
        return "SMB"

    def get_port(self) -> int:
        return int(self.config.get('SMB_PORT', 445))

    def is_enabled(self) -> bool:
        return self.config.get('SMB_ENABLED', 'true').lower() == 'true'

    def start(self):
        """Start the SMB server with impacket"""
        try:
            # Get configuration
            host = self.config.get('HOST', '0.0.0.0')
            smb_port = self.get_port()
            netbios_port = int(self.config.get('SMB_NETBIOS_PORT', 139))

            # Use /app/data as SMB root (contains tools and uploads subdirectories)
            data_root = '/app/data'
            tools_dir = os.path.join(data_root, 'tools')
            uploads_dir = os.path.join(data_root, 'uploads')

            # Ensure directories exist
            os.makedirs(tools_dir, exist_ok=True)
            os.makedirs(uploads_dir, exist_ok=True)

            self.log_info(f"SMB tools directory: {tools_dir} (read-only)")
            self.log_info(f"SMB uploads directory: {uploads_dir} (read-write)")

            # Create SMB server
            server = SimpleSMBServer(listenAddress=host, listenPort=smb_port)

            # Check if authentication is enabled
            auth_enabled = self.config.get('AUTH_ENABLED', 'false').lower() == 'true'
            auth_username = self.config.get('AUTH_USERNAME')
            auth_password = self.config.get('AUTH_PASSWORD_HASH')

            if auth_enabled and auth_username and auth_password:
                # Add user authentication with NT/LM hashes
                # For SMB auth, we need to compute hashes from the password
                from impacket.ntlm import compute_lmhash, compute_nthash

                # Compute LM and NT hashes from the plaintext password
                lmhash = compute_lmhash(auth_password)
                nthash = compute_nthash(auth_password)

                # addCredential(name, uid, lmhash, nthash)
                server.addCredential(auth_username, 0, lmhash, nthash)
                self.log_info(f"SMB authentication ENABLED - user: {auth_username}")
            else:
                # Anonymous access - no authentication required
                self.log_info(f"SMB authentication DISABLED - anonymous access enabled")

            # Add shares
            # Tools share: read-only
            server.addShare('tools', tools_dir, 'Pentest Tools (Read-Only)', readOnly='yes')
            self.log_info(f"SMB share 'tools' added (read-only)")

            # Uploads share: read-write
            server.addShare('uploads', uploads_dir, 'Uploads (Read-Write)', readOnly='no')
            self.log_info(f"SMB share 'uploads' added (read-write)")

            # Set server name
            server.setSMB2Support(True)

            self.log_info(f"SMB server starting on {host}:{smb_port} (NetBIOS: {netbios_port})")
            self.log_info(f"SMB shares: \\\\<IP>\\tools (read-only), \\\\<IP>\\uploads (read-write)")

            # Start serving (blocking call)
            server.start()

        except Exception as e:
            self.log_error(f"Failed to start SMB server: {e}")
            import traceback
            traceback.print_exc()
            raise
