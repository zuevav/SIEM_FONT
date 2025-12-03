#!/bin/bash
# =====================================================================
# SIEM Network Monitor - Installation Script
# =====================================================================
# Usage: sudo ./install.sh
# =====================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/siem/network_monitor"
LOG_DIR="/var/log/siem"
DATA_DIR="/var/lib/siem/network_monitor"
SERVICE_FILE="siem-network-monitor.service"
USER="siem"
GROUP="siem"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SIEM Network Monitor - Installation${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (sudo ./install.sh)${NC}"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo -e "${RED}Error: Cannot detect OS${NC}"
    exit 1
fi

echo -e "${YELLOW}Detected OS: $OS $VER${NC}"

# Install dependencies
echo -e "${YELLOW}Installing system dependencies...${NC}"

if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
    apt-get update
    apt-get install -y python3.11 python3.11-venv python3-pip \
        snmp libsnmp-dev gcc python3-dev

elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]] || [[ "$OS" == "fedora" ]]; then
    dnf install -y python3.11 python3-pip gcc python3-devel \
        net-snmp net-snmp-devel

else
    echo -e "${YELLOW}Warning: Unknown OS, please install Python 3.11+ manually${NC}"
fi

# Create user and group
echo -e "${YELLOW}Creating user and group...${NC}"
if ! id -u $USER > /dev/null 2>&1; then
    useradd -r -s /bin/false $USER
    echo -e "${GREEN}User '$USER' created${NC}"
else
    echo -e "${YELLOW}User '$USER' already exists${NC}"
fi

# Create directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p $INSTALL_DIR
mkdir -p $LOG_DIR
mkdir -p $DATA_DIR

# Copy files
echo -e "${YELLOW}Copying files...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp -r $SCRIPT_DIR/* $INSTALL_DIR/

# Create Python virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
cd $INSTALL_DIR
python3.11 -m venv venv

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
$INSTALL_DIR/venv/bin/pip install --upgrade pip
$INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt

# Create config from example if not exists
if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
    echo -e "${YELLOW}Creating default configuration...${NC}"
    cp $INSTALL_DIR/config.yaml.example $INSTALL_DIR/config.yaml
    echo -e "${YELLOW}Please edit $INSTALL_DIR/config.yaml before starting the service${NC}"
fi

# Set permissions
echo -e "${YELLOW}Setting permissions...${NC}"
chown -R $USER:$GROUP $INSTALL_DIR
chown -R $USER:$GROUP $LOG_DIR
chown -R $USER:$GROUP $DATA_DIR

chmod 600 $INSTALL_DIR/config.yaml
chmod +x $INSTALL_DIR/main.py

# Install systemd service
echo -e "${YELLOW}Installing systemd service...${NC}"
cp $INSTALL_DIR/$SERVICE_FILE /etc/systemd/system/
systemctl daemon-reload
systemctl enable $SERVICE_FILE

# Configure firewall (if firewalld is installed)
if command -v firewall-cmd &> /dev/null; then
    echo -e "${YELLOW}Configuring firewall...${NC}"
    firewall-cmd --permanent --add-port=514/udp || true
    firewall-cmd --permanent --add-port=514/tcp || true
    firewall-cmd --reload || true
fi

# Configure UFW (if installed)
if command -v ufw &> /dev/null; then
    echo -e "${YELLOW}Configuring UFW...${NC}"
    ufw allow 514/udp || true
    ufw allow 514/tcp || true
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Edit configuration: ${YELLOW}$INSTALL_DIR/config.yaml${NC}"
echo -e "2. Start the service:  ${YELLOW}systemctl start $SERVICE_FILE${NC}"
echo -e "3. Check status:       ${YELLOW}systemctl status $SERVICE_FILE${NC}"
echo -e "4. View logs:          ${YELLOW}journalctl -u $SERVICE_FILE -f${NC}"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo -e "- Configure SIEM server URL and API key in config.yaml"
echo -e "- Add your network devices to the SNMP devices list"
echo -e "- Configure syslog on your network devices to send logs to this server"
echo ""
