# Quick Installation Guide

## 🚀 Click-to-Run Installation

SIEM System now supports fully automated installation with zero manual configuration!

---

## Linux/Unix Installation (Recommended)

### One-Line Install (Internet Connection Required)

```bash
curl -sSL https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh | sudo bash
```

Or with wget:

```bash
wget -qO- https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh | sudo bash
```

### Manual Download and Install

```bash
# Download installer
wget https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh

# Make executable
chmod +x install.sh

# Run installer
sudo ./install.sh
```

### What the Installer Does

1. ✅ Checks your OS (Ubuntu, Debian, CentOS, RHEL, Fedora)
2. ✅ Installs dependencies (Docker, Docker Compose, Git, curl)
3. ✅ Downloads latest SIEM from GitHub
4. ✅ Interactive configuration wizard
5. ✅ Generates secure passwords
6. ✅ Builds and starts Docker containers
7. ✅ Health checks
8. ✅ Creates systemd service for auto-start
9. ✅ Prints access URLs and credentials

### Installation Time

- ⚡ **Fresh install**: 5-10 minutes (depending on internet speed)
- ⚡ **Update existing**: 1-2 minutes

---

## Windows Installation

### Requirements

- Windows 10/11 or Windows Server 2019/2022
- Administrator privileges
- Docker Desktop for Windows (installer will guide you)

### Steps

1. **Download PowerShell Installer**

   Open PowerShell as Administrator and run:

   ```powershell
   Invoke-WebRequest -Uri https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.ps1 -OutFile install.ps1
   ```

2. **Run Installer**

   ```powershell
   PowerShell -ExecutionPolicy Bypass -File install.ps1
   ```

3. **Follow Wizard**

   The installer will:
   - Check/install Docker Desktop
   - Download SIEM from GitHub
   - Configure system interactively
   - Start all services
   - Create scheduled task for auto-start

### Installation Time

- ⚡ **With Docker Desktop already installed**: 10-15 minutes
- ⚡ **First time (need Docker Desktop)**: 20-30 minutes

---

## Configuration Wizard

During installation, you'll be asked:

### 1. Admin User
- **Username** (default: `admin`)
- **Password** (default: `admin123`)

> ⚠️ **Security**: Change default password after first login!

### 2. Network Ports
- **API Port** (default: `8000`)
- **Frontend Port** (default: `3000`)

### 3. AI Provider
Choose one:
- **DeepSeek** (free, recommended) - Optional API key
- **Yandex GPT** - Requires API key + Folder ID
- **None** - Skip AI features

---

## Post-Installation

### Access URLs

After installation completes:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Web interface |
| **API** | http://localhost:8000 | REST API |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Redoc** | http://localhost:8000/redoc | Alternative docs |

### Default Credentials

- **Username**: `admin` (or custom if changed)
- **Password**: `admin123` (or custom if changed)

> 🔐 **First Login**: Go to Settings → Change Password

### Install Location

- **Linux**: `/opt/siem/`
- **Windows**: `C:\SIEM\`

### Configuration File

- **Linux**: `/opt/siem/.env`
- **Windows**: `C:\SIEM\.env`

---

## Management Commands

### Linux (systemd)

```bash
# Check status
sudo systemctl status siem

# Start SIEM
sudo systemctl start siem

# Stop SIEM
sudo systemctl stop siem

# Restart SIEM
sudo systemctl restart siem

# View logs
cd /opt/siem && docker-compose logs -f

# Update SIEM
cd /opt/siem && git pull && docker-compose up -d --build
```

### Windows (Docker Compose)

```powershell
# Navigate to install directory
cd C:\SIEM

# Check status
docker-compose ps

# Start SIEM
docker-compose start

# Stop SIEM
docker-compose stop

# Restart SIEM
docker-compose restart

# View logs
docker-compose logs -f

# Update SIEM
git pull
docker-compose up -d --build
```

---

## Troubleshooting

### Installation Failed

**Linux:**
```bash
# View installer logs
cat /var/log/siem-install.log

# Check Docker service
sudo systemctl status docker

# Manual cleanup
cd /opt/siem && sudo docker-compose down
sudo rm -rf /opt/siem
```

**Windows:**
```powershell
# Check Docker Desktop
docker version

# View compose logs
cd C:\SIEM
docker-compose logs

# Manual cleanup
docker-compose down
Remove-Item -Recurse -Force C:\SIEM
```

### Services Not Starting

```bash
# Check container status
docker-compose ps

# View specific service logs
docker-compose logs backend
docker-compose logs db
docker-compose logs frontend

# Restart problematic service
docker-compose restart backend
```

### Can't Access Frontend

1. Check if container is running:
   ```bash
   docker-compose ps frontend
   ```

2. Check port binding:
   ```bash
   netstat -tuln | grep 3000  # Linux
   netstat -ano | findstr 3000  # Windows
   ```

3. Check firewall:
   ```bash
   # Linux (Ubuntu)
   sudo ufw allow 3000

   # Windows
   New-NetFirewallRule -DisplayName "SIEM Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
   ```

### Database Connection Issues

```bash
# Check database logs
docker-compose logs db

# Verify database is ready
docker-compose exec db psql -U siem -d siem_db -c "SELECT 1;"

# Reinitialize database
docker-compose down -v
docker-compose up -d
```

### AI Analysis Not Working

1. Check AI provider configuration in `.env`:
   ```bash
   cat .env | grep AI_PROVIDER
   ```

2. Verify API key is set:
   ```bash
   cat .env | grep DEEPSEEK_API_KEY
   # or
   cat .env | grep YANDEX_GPT_API_KEY
   ```

3. Test AI service:
   ```bash
   curl http://localhost:8000/api/v1/ai/health
   ```

---

## Updating SIEM

### Automatic Update

**Linux:**
```bash
cd /opt/siem
git pull origin main
docker-compose pull
docker-compose up -d --build
```

**Windows:**
```powershell
cd C:\SIEM
git pull origin main
docker-compose pull
docker-compose up -d --build
```

### Update Frequency

- **Stable releases**: Monthly
- **Security patches**: As needed
- **Feature updates**: Bi-weekly

### Backup Before Update

```bash
# Backup database
docker-compose exec db pg_dump -U siem siem_db > backup_$(date +%Y%m%d).sql

# Backup configuration
cp .env .env.backup

# Backup detection rules
docker-compose exec db psql -U siem -d siem_db -c "COPY detection_rules TO STDOUT CSV HEADER" > rules_backup.csv
```

---

## Uninstallation

### Linux

```bash
# Stop services
cd /opt/siem
sudo docker-compose down -v

# Remove systemd service
sudo systemctl stop siem
sudo systemctl disable siem
sudo rm /etc/systemd/system/siem.service
sudo systemctl daemon-reload

# Remove files
sudo rm -rf /opt/siem
```

### Windows

```powershell
# Stop services
cd C:\SIEM
docker-compose down -v

# Remove scheduled task
Unregister-ScheduledTask -TaskName "SIEM System" -Confirm:$false

# Remove files
Remove-Item -Recurse -Force C:\SIEM
```

---

## Advanced Installation Options

### Custom Install Directory

**Linux:**
```bash
# Download installer
wget https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh
chmod +x install.sh

# Edit INSTALL_DIR variable
nano install.sh
# Change: INSTALL_DIR="/your/custom/path"

# Run
sudo ./install.sh
```

**Windows:**
```powershell
.\install.ps1 -InstallPath "D:\MyCustomPath\SIEM"
```

### Silent Installation (No Prompts)

Create `.env` file before running installer:

```bash
# Create pre-configured .env
cat > /opt/siem/.env << EOF
POSTGRES_PASSWORD=your_secure_password
JWT_SECRET=your_jwt_secret
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=secure_password
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key
API_PORT=8000
FRONTEND_PORT=3000
EOF

# Run installer (will detect existing .env)
sudo ./install.sh
```

### Air-Gapped Installation

For environments without internet:

1. **Download all files on internet-connected machine:**
   ```bash
   git clone https://github.com/zuevav/SIEM_FONT.git
   cd SIEM_FONT
   
   # Pull Docker images
   docker-compose pull
   docker save -o siem-images.tar \
     postgres:15-alpine \
     $(docker-compose config | grep 'image:' | awk '{print $2}')
   ```

2. **Transfer to air-gapped machine:**
   - SIEM_FONT directory
   - siem-images.tar

3. **Load on air-gapped machine:**
   ```bash
   docker load -i siem-images.tar
   cd SIEM_FONT
   docker-compose up -d
   ```

---

## Security Hardening

### After Installation

1. **Change default password** (via UI or API)

2. **Configure firewall:**
   ```bash
   # Linux (ufw)
   sudo ufw allow from YOUR_ADMIN_IP to any port 3000
   sudo ufw allow from YOUR_ADMIN_IP to any port 8000
   
   # Windows
   # Use Windows Defender Firewall GUI or PowerShell
   ```

3. **Enable HTTPS** (see docs/HTTPS_SETUP.md)

4. **Review .env file permissions:**
   ```bash
   # Linux
   chmod 600 /opt/siem/.env
   
   # Windows
   icacls C:\SIEM\.env /inheritance:r /grant:r Administrators:F
   ```

5. **Enable audit logging:**
   Edit `.env`:
   ```
   LOG_LEVEL=INFO
   AUDIT_ENABLED=true
   ```

---

## Getting Help

### Documentation

- [Phase 1 Setup Guide](PHASE1_SETUP.md) - Email, FreeScout, Threat Intelligence configuration
- [FreeScout Integration](FREESCOUT_INTEGRATION.md) - Detailed helpdesk integration guide
- [Market Analysis](MARKET_ANALYSIS.md) - Feature comparison with commercial SIEM solutions

### Support Channels

- **GitHub Issues**: https://github.com/zuevav/SIEM_FONT/issues
- **Documentation**: `/opt/siem/docs/` or `C:\SIEM\docs\`
- **Community**: [Coming soon]

### Logs Location

- **Linux**: `/opt/siem/logs/` (inside containers)
- **Windows**: `C:\SIEM\logs\` (inside containers)

View with:
```bash
docker-compose logs -f --tail=100 backend
```

---

## Next Steps

After successful installation:

1. ✅ **Login to Web Interface** - http://localhost:3000
2. ✅ **Change Default Password** - Settings → Security
3. ✅ **Configure Phase 1 Features** - See [Phase 1 Setup Guide](PHASE1_SETUP.md)
4. ✅ **Install Windows Agent** - See `agent/README.md`
5. ✅ **Review Detection Rules** - 10 pre-installed rules
6. ✅ **Configure AI Provider** - Settings → AI Configuration
7. ✅ **Monitor Dashboard** - Real-time event visualization
8. ✅ **Set Up Integrations** - Email, FreeScout, Threat Intelligence (see [Phase 1 Setup](PHASE1_SETUP.md))

---

**Installation Completed Successfully!** 🎉

For questions or issues, create a GitHub issue: https://github.com/zuevav/SIEM_FONT/issues
