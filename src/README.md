# Rlog Uploader - Deployment Guide

Complete guide for deploying the Comma 3X Rlog Auto-Uploader in production.

---

## Table of Contents
1. [Docker Deployment (Recommended)](#docker-deployment)
2. [Windows Service Deployment](#windows-service-deployment)
3. [Manual Deployment](#manual-deployment)
4. [Configuration](#configuration)
5. [Troubleshooting](#troubleshooting)

---

## Docker Deployment (Recommended)

Docker deployment provides the easiest and most reliable way to run in production with automatic restarts.

### Prerequisites
- Docker and Docker Compose installed
- SSH key for Comma 3X access in `~/.ssh/`

### Quick Start

1. **Build and start the container:**
   ```bash
   docker-compose up -d
   ```

2. **Access the web interface:**
   ```
   http://localhost:3445
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the container:**
   ```bash
   docker-compose down
   ```

### Docker Configuration

The container is configured to:
- ✅ Run on port **3445** (production)
- ✅ Auto-restart unless manually stopped
- ✅ Persist config files via volumes
- ✅ Health checks every 30 seconds
- ✅ Access your SSH keys (read-only)

### Customization

Edit `docker-compose.yml` to customize:

```yaml
ports:
  - "3445:3445"  # Change external port if needed

environment:
  - PORT=3445    # Change internal port

volumes:
  - ./config.json:/app/config.json                    # Config persistence
  - ./uploaded_logs.json:/app/uploaded_logs.json      # Tracking persistence
  - ./downloads:/app/downloads                        # Downloaded files
  - ~/.ssh:/root/.ssh:ro                              # SSH keys
```

### Production Best Practices

1. **Run on system startup:**
   ```bash
   # Add to systemd or crontab
   @reboot cd /path/to/rlogDownloader/src && docker-compose up -d
   ```

2. **Monitor health:**
   ```bash
   docker-compose ps  # Check container health
   ```

3. **Update the container:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

---

## Windows Service Deployment

Run the Rlog Uploader as a Windows service that starts automatically on boot.

### Method 1: NSSM Service (Recommended)

**Advantages:**
- True Windows service
- Better restart handling
- Logs to file automatically

**Installation:**

1. **Run as Administrator** (Right-click PowerShell → "Run as Administrator"):
   ```powershell
   cd C:\path\to\rlogDownloader\src
   .\install_windows_service.ps1
   ```

2. **Custom port (optional):**
   ```powershell
   .\install_windows_service.ps1 -Port 3445
   ```

**The script will:**
- ✅ Install Chocolatey (if needed)
- ✅ Install NSSM (if needed)
- ✅ Create Windows service
- ✅ Configure auto-start on boot
- ✅ Configure auto-restart on failure
- ✅ Start the service immediately

**Management:**

```powershell
# View status
Get-Service RlogUploader

# Stop service
nssm stop RlogUploader

# Start service
nssm start RlogUploader

# View logs
Get-Content service.log -Tail 50 -Wait

# Uninstall
.\uninstall_windows.ps1
```

### Method 2: Task Scheduler (Alternative)

**Advantages:**
- No additional software needed
- Built into Windows

**Installation:**

1. **Run as Administrator**:
   ```powershell
   cd C:\path\to\rlogDownloader\src
   .\install_windows_task.ps1
   ```

2. **Custom port (optional):**
   ```powershell
   .\install_windows_task.ps1 -Port 3445
   ```

**Management:**

```powershell
# View status
Get-ScheduledTask -TaskName RlogUploaderAutoStart

# Stop task
Stop-ScheduledTask -TaskName RlogUploaderAutoStart

# Start task
Start-ScheduledTask -TaskName RlogUploaderAutoStart

# Uninstall
.\uninstall_windows.ps1
```

---

## Manual Deployment

For Linux/macOS systems without Docker.

### Prerequisites

```bash
python3 --version  # Python 3.8+
pip3 install -r requirements.txt
```

### Setup

1. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Run on custom port:**
   ```bash
   PORT=3445 python3 extract_web_server_rlogs.py
   ```

### Systemd Service (Linux)

Create `/etc/systemd/system/rlog-uploader.service`:

```ini
[Unit]
Description=Comma 3X Rlog Auto-Uploader
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/rlogDownloader/src
Environment="PORT=3445"
ExecStart=/usr/bin/python3 /path/to/rlogDownloader/src/extract_web_server_rlogs.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable rlog-uploader
sudo systemctl start rlog-uploader
sudo systemctl status rlog-uploader
```

### Launch Agent (macOS)

Create `~/Library/LaunchAgents/com.rlog.uploader.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rlog.uploader</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/rlogDownloader/src/extract_web_server_rlogs.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/rlogDownloader/src</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PORT</key>
        <string>3445</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/rlog-uploader.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/rlog-uploader.log</string>
</dict>
</plist>
```

Load and start:

```bash
launchctl load ~/Library/LaunchAgents/com.rlog.uploader.plist
launchctl start com.rlog.uploader
```

---

## Configuration

### Port Configuration

The application supports port configuration via environment variable:

- **Development:** Port 3111 (default)
- **Production:** Port 3445 (recommended)

**Set port:**
```bash
# Linux/macOS
export PORT=3445
python3 extract_web_server_rlogs.py

# Windows PowerShell
$env:PORT = "3445"
python extract_web_server_rlogs.py

# Docker
# Edit docker-compose.yml environment section
```

### SSH Keys

Ensure your SSH public key is added to the Comma 3X:

```bash
ssh-copy-id comma@192.168.173.10
```

Or manually add to `/data/params/d/GithubSshKeys` on the Comma 3X.

### Web Interface Settings

Access the web interface to configure:

1. **Comma 3X IP:** Default 192.168.173.10
2. **FileBrowser URL:** Your server URL
3. **Upload Path:** Destination folder
4. **Credentials:** FileBrowser username/password
5. **Auto-start:** Enable to start monitoring on page load

All settings are saved to `config.json` and written directly to `rlog_downloader.py`.

---

## Troubleshooting

### Docker Issues

**Container won't start:**
```bash
docker-compose logs
docker-compose ps
```

**Permission denied accessing SSH keys:**
```bash
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

**Can't connect to web interface:**
```bash
# Check if port is already in use
netstat -tulpn | grep 3445

# Try different port
# Edit docker-compose.yml ports section
```

### Windows Service Issues

**Service won't start:**
1. Check `service.log` in the script directory
2. Verify Python path: `Get-Command python`
3. Run manually first to test: `python extract_web_server_rlogs.py`

**NSSM installation fails:**
- Install manually: https://nssm.cc/download
- Or use Task Scheduler method instead

### General Issues

**Can't connect to Comma 3X:**
```bash
# Test SSH connection
ssh comma@192.168.173.10

# Check if device is reachable
ping 192.168.173.10
```

**FileBrowser upload fails:**
- Verify URL is correct (include https://)
- Check username/password
- Test login manually in browser
- Check FileBrowser server logs

**Process keeps restarting:**
- Check logs for error messages
- Verify all dependencies are installed
- Test script manually first

### Logs Location

- **Docker:** `docker-compose logs -f`
- **NSSM Service:** `service.log` in script directory
- **Task Scheduler:** Check Task Scheduler history
- **Systemd:** `journalctl -u rlog-uploader -f`
- **Web Interface:** `rlog_monitor.log` in script directory

---

## Security Recommendations

1. **Use HTTPS:** Configure reverse proxy (nginx/Caddy) with SSL
2. **Firewall:** Restrict access to port 3445 to trusted networks
3. **SSH Keys:** Use key-based auth, not passwords for Comma 3X
4. **Updates:** Regularly update dependencies: `pip install -U -r requirements.txt`
5. **Monitoring:** Set up alerts for service failures

---

## Support

For issues or questions:
- Check logs first
- Verify configuration in web interface
- Test components individually (SSH, FileBrowser, web server)
- Review this documentation

---

**Happy uploading! 🚗📊**
