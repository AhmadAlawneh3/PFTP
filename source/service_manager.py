"""Service Manager - Orchestrates all protocol servers"""

import multiprocessing
import os
import signal
import sys
import time
from typing import Dict, List

from protocols.http import HTTPServer
from protocols.ftp import FTPServer
from protocols.smb import SMBServer


class ServiceManager:
    """Manages multiple protocol servers using multiprocessing"""

    def __init__(self):
        """Initialize the service manager"""
        self.config = self._load_config_from_env()
        self.processes: Dict[str, multiprocessing.Process] = {}
        self.shutdown_event = multiprocessing.Event()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _load_config_from_env(self) -> dict:
        """Load configuration from environment variables"""
        return {
            # General
            'HOST': os.getenv('HOST', '0.0.0.0'),
            'PROTOCOL': os.getenv('PROTOCOL', 'http'),
            'DEBUG': os.getenv('DEBUG', 'False'),
            'IGNORE_DIRS': os.getenv('IGNORE_DIRS', '.git,__pycache__,.vscode'),

            # Directories
            'TOOLS_FOLDER': os.getenv('TOOLS_FOLDER', 'tools'),
            'UPLOAD_FOLDER': os.getenv('UPLOAD_FOLDER', 'uploads'),

            # HTTP
            'HTTP_ENABLED': os.getenv('HTTP_ENABLED', 'true'),
            'HTTP_PORT': os.getenv('HTTP_PORT', '1234'),

            # FTP
            'FTP_ENABLED': os.getenv('FTP_ENABLED', 'true'),
            'FTP_PORT': os.getenv('FTP_PORT', '21'),
            'FTP_PASSIVE_START': os.getenv('FTP_PASSIVE_START', '60000'),
            'FTP_PASSIVE_END': os.getenv('FTP_PASSIVE_END', '60100'),

            # SMB
            'SMB_ENABLED': os.getenv('SMB_ENABLED', 'true'),
            'SMB_PORT': os.getenv('SMB_PORT', '445'),
            'SMB_NETBIOS_PORT': os.getenv('SMB_NETBIOS_PORT', '139'),

            # Authentication
            'AUTH_ENABLED': os.getenv('AUTH_ENABLED', 'false'),
            'AUTH_USERNAME': os.getenv('AUTH_USERNAME'),
            'AUTH_PASSWORD_HASH': os.getenv('AUTH_PASSWORD_HASH'),
        }

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n[ServiceManager] Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()
        self.stop_all()
        sys.exit(0)

    def _run_server(self, server_class, name: str):
        """Run a server in a subprocess"""
        # Reset signal handlers in child process to avoid conflicts
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        try:
            server = server_class(self.config)
            print(f"[ServiceManager] Starting {name} server on port {server.get_port()}")
            server.start()
        except Exception as e:
            print(f"[ServiceManager] Error in {name} server: {e}")
            import traceback
            traceback.print_exc()

    def start_http(self):
        """Start HTTP server in subprocess"""
        server = HTTPServer(self.config)
        if server.is_enabled():
            process = multiprocessing.Process(
                target=self._run_server,
                args=(HTTPServer, 'HTTP'),
                name='pftp-http'
            )
            process.start()
            self.processes['http'] = process
            return True
        return False

    def start_ftp(self):
        """Start FTP server in subprocess"""
        server = FTPServer(self.config)
        if server.is_enabled():
            process = multiprocessing.Process(
                target=self._run_server,
                args=(FTPServer, 'FTP'),
                name='pftp-ftp'
            )
            process.start()
            self.processes['ftp'] = process
            return True
        return False

    def start_smb(self):
        """Start SMB server in subprocess"""
        server = SMBServer(self.config)
        if server.is_enabled():
            process = multiprocessing.Process(
                target=self._run_server,
                args=(SMBServer, 'SMB'),
                name='pftp-smb'
            )
            process.start()
            self.processes['smb'] = process
            return True
        return False

    def start_all(self):
        """Start all enabled protocol servers"""
        print("[ServiceManager] PFTP Multi-Protocol Server Starting...")
        print("[ServiceManager] " + "=" * 60)

        enabled_protocols = []

        if self.start_http():
            enabled_protocols.append('HTTP')

        if self.start_ftp():
            enabled_protocols.append('FTP')

        if self.start_smb():
            enabled_protocols.append('SMB')

        print("[ServiceManager] " + "=" * 60)
        print(f"[ServiceManager] Active protocols: {', '.join(enabled_protocols)}")
        print(f"[ServiceManager] Total processes: {len(self.processes)}")
        print("[ServiceManager] " + "=" * 60)

        if not self.processes:
            print("[ServiceManager] WARNING: No protocols enabled!")
            return False

        return True

    def stop_all(self):
        """Stop all running servers gracefully"""
        print("[ServiceManager] Stopping all servers...")

        for name, process in self.processes.items():
            if process.is_alive():
                print(f"[ServiceManager] Terminating {name.upper()} server (PID: {process.pid})")
                process.terminate()

        # Wait for processes to terminate (max 5 seconds)
        deadline = time.time() + 5
        for name, process in self.processes.items():
            remaining = deadline - time.time()
            if remaining > 0 and process.is_alive():
                process.join(timeout=remaining)

        # Force kill any remaining processes
        for name, process in self.processes.items():
            if process.is_alive():
                print(f"[ServiceManager] Force killing {name.upper()} server (PID: {process.pid})")
                process.kill()
                process.join()

        self.processes.clear()
        print("[ServiceManager] All servers stopped")

    def monitor(self):
        """Monitor running servers and restart if they crash"""
        print("[ServiceManager] Monitoring started. Press Ctrl+C to stop.")

        try:
            while not self.shutdown_event.is_set():
                # Check if any process has died
                dead_processes = []
                for name, process in self.processes.items():
                    if not process.is_alive():
                        exit_code = process.exitcode
                        print(f"[ServiceManager] WARNING: {name.upper()} server died (exit code: {exit_code})")
                        dead_processes.append(name)

                # Remove dead processes
                for name in dead_processes:
                    del self.processes[name]

                # If all processes are dead, exit
                if not self.processes:
                    print("[ServiceManager] All servers have stopped. Exiting.")
                    break

                # Sleep for a bit before next check
                time.sleep(2)

        except KeyboardInterrupt:
            print("\n[ServiceManager] Keyboard interrupt received")
        finally:
            self.stop_all()


def main():
    """Main entry point"""
    # Create required directories
    tools_dir = os.getenv('TOOLS_FOLDER', 'tools')
    uploads_dir = os.getenv('UPLOAD_FOLDER', 'uploads')

    os.makedirs(tools_dir, exist_ok=True)
    os.makedirs(uploads_dir, exist_ok=True)

    # Start service manager
    manager = ServiceManager()

    if manager.start_all():
        manager.monitor()
    else:
        print("[ServiceManager] Failed to start any servers. Exiting.")
        sys.exit(1)


if __name__ == '__main__':
    main()
