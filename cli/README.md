# PFTP CLI

CLI tool for managing the PFTP (Pentest File Transfer Protocols) server.

A lightweight, multi-protocol file transfer hub for penetration testers, ethical hackers, and CTF players. Supports HTTP, FTP, and SMB simultaneously.

**Docker Image**: [ahmadalawneh3/pftp](https://hub.docker.com/r/ahmadalawneh3/pftp)

## Installation

```bash
pipx install pftp
```

Or with pip:

```bash
pip install pftp
```

## Quick Start

```bash
# Install and configure (interactive wizard)
pftp install

# Start the server
pftp start

# Check status
pftp status

# Add tools
pftp add-tool /path/to/linpeas.sh
pftp add-tool /path/to/windows/ --recursive --category windows

# View logs
pftp logs

# Stop the server
pftp stop
```

## Commands

| Command | Description |
|---------|-------------|
| `pftp install` | Install and configure (interactive wizard) |
| `pftp configure` | Reconfigure settings (interactive or flags) |
| `pftp start` | Start the server |
| `pftp stop` | Stop the server |
| `pftp restart` | Restart the server |
| `pftp status` | Show status and configuration |
| `pftp logs` | View server logs |
| `pftp update` | Update to latest Docker image |
| `pftp remove` | Uninstall pftp |
| `pftp add-tool` | Add files to tools directory |
| `pftp version` | Show version |

## Features

- Multi-protocol: HTTP, FTP, and SMB running simultaneously
- Interactive setup wizard with `pftp install`
- Optional authentication across all protocols
- Configurable Docker restart policy
- Auto-detects network interfaces (prioritizes VPN/tun0)
- Web UI with download command generation (PowerShell, wget, curl, bitsadmin, base64)
- File upload/exfiltration support
- Live activity logs via SSE

## Requirements

- Python 3.8+
- Docker

## License

MIT
