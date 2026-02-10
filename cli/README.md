# PFTP - Pentest File Transfer Protocols

A lightweight, multi-protocol file transfer CLI tool for penetration testers, ethical hackers, and CTF players. PFTP manages a dockerized server that runs HTTP, FTP, and SMB simultaneously, making it easy to transfer tools and exfiltrate data during security assessments.

**Docker Image**: [ahmadalawneh3/pftp](https://hub.docker.com/r/ahmadalawneh3/pftp)  
**GitHub**: [github.com/AhmadAlawneh3/PFTP](https://github.com/AhmadAlawneh3/PFTP)

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Commands](#commands)
- [Requirements](#requirements)
- [License](#license)

## Features

- **Multi-Protocol Support**: HTTP, FTP, and SMB running simultaneously
- **Interactive Setup**: Wizard-based installation and configuration
- **Web UI**: Download command generation for PowerShell, wget, curl, bitsadmin, and base64
- **File Upload/Exfiltration**: Built-in support for receiving files
- **Optional Authentication**: Secure access across all protocols
- **Auto Network Detection**: Prioritizes VPN/tun interfaces
- **Live Activity Logs**: Real-time monitoring via SSE
- **Docker-Powered**: Isolated, reproducible environment with configurable restart policies

## Installation

**Recommended (with pipx):**
```bash
pipx install pftp
```

**With pip:**
```bash
pip install pftp
```

**Requirements:**
- Python 3.8+
- Docker

## Usage

### Initial Setup

Install and configure PFTP with the interactive wizard:

```bash
pftp install
```

The wizard will guide you through:
- Directory configuration
- Protocol selection (HTTP, FTP, SMB)
- Authentication settings
- Docker restart policy

### Starting the Server

```bash
pftp start
```

Output:
```
✓ Server started

Server URLs:
  • HTTP:  http://192.168.1.100:1234
  • FTP:   ftp://192.168.1.100:21
```

### Adding Tools

Add single files:
```bash
pftp add-tool /path/to/linpeas.sh
```

Add directories with categorization:
```bash
pftp add-tool /path/to/windows-tools/ --recursive --category windows
pftp add-tool /path/to/linux-tools/ --recursive --category linux
```

### Checking Status

```bash
pftp status
```

Shows running status, enabled protocols, URLs, and configuration.

### Managing the Server

```bash
# Stop the server
pftp stop

# Restart the server
pftp restart

# View live logs
pftp logs

# Reconfigure settings
pftp configure
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
| `pftp --help` | Show help for any command |

### Common Options

**Configuration flags** (for non-interactive setup):
```bash
pftp install --yes --http-port 8080 --enable-ftp --auth --auth-username admin
pftp configure --disable-smb --http-port 9000
```

**Add-tool options**:
```bash
pftp add-tool <file> [--category <name>] [--recursive]
```

**Logs options**:
```bash
pftp logs [--follow] [--lines <n>]
```

## Requirements

- **Python**: 3.8 or higher
- **Docker**: Running Docker daemon
- **Operating System**: Linux, macOS, or Windows with WSL2

## License

MIT License - See [LICENSE](../LICENSE) for details

---

**Author**: Ahmad Alawneh  
**Repository**: [github.com/AhmadAlawneh3/PFTP](https://github.com/AhmadAlawneh3/PFTP)
