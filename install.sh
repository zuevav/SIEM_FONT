#!/bin/bash

###############################################################################
# SIEM System - Automated Installer
# Click-to-run installation script
#
# Usage: curl -sSL https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh | bash
# Or: wget -qO- https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh | bash
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GITHUB_REPO="zuevav/SIEM_FONT"
GITHUB_BRANCH="main"
INSTALL_DIR="/opt/siem"
SERVICE_NAME="siem"
MIN_DOCKER_VERSION="20.10"
MIN_COMPOSE_VERSION="1.29"

###############################################################################
# Helper Functions
###############################################################################

print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
   _____ _____ ______ __  __   _____           _        _ _
  / ____|_   _|  ____|  \/  | |_   _|         | |      | | |
 | (___   | | | |__  | \  / |   | |  _ __  ___| |_ __ _| | | ___ _ __
  \___ \  | | |  __| | |\/| |   | | | '_ \/ __| __/ _` | | |/ _ \ '__|
  ____) |_| |_| |____| |  | |  _| |_| | | \__ \ || (_| | | |  __/ |
 |_____/|_____|______|_|  |_| |_____|_| |_|___/\__\__,_|_|_|\___|_|

EOF
    echo -e "${NC}"
    echo -e "${GREEN}Security Information and Event Management System${NC}"
    echo -e "${BLUE}Version: 1.0 | Automated Installer${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root or with sudo"
        log_info "Please run: sudo $0"
        exit 1
    fi
}

check_os() {
    log_info "Checking operating system..."

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        log_success "Detected: $PRETTY_NAME"
    else
        log_error "Cannot detect OS. Only Linux is supported."
        exit 1
    fi

    case "$OS" in
        ubuntu|debian)
            PACKAGE_MANAGER="apt-get"
            ;;
        centos|rhel|fedora|rocky|almalinux)
            PACKAGE_MANAGER="yum"
            ;;
        *)
            log_warning "Unsupported OS: $OS. Installation may fail."
            PACKAGE_MANAGER="apt-get"
            ;;
    esac
}

version_compare() {
    [ "$1" = "$2" ] && return 0
    local IFS=.
    local i ver1=($1) ver2=($2)
    for ((i=0; i<${#ver1[@]}; i++)); do
        if [[ -z ${ver2[i]} ]]; then
            return 0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]})); then
            return 0
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]})); then
            return 1
        fi
    done
    return 0
}

check_dependencies() {
    log_info "Checking dependencies..."

    local missing_deps=()

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not found"
        missing_deps+=("docker")
    else
        DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
        if version_compare "$DOCKER_VERSION" "$MIN_DOCKER_VERSION"; then
            log_success "Docker $DOCKER_VERSION installed"
        else
            log_warning "Docker $DOCKER_VERSION is too old (minimum: $MIN_DOCKER_VERSION)"
            missing_deps+=("docker")
        fi
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_warning "Docker Compose not found"
        missing_deps+=("docker-compose")
    else
        if docker compose version &> /dev/null; then
            COMPOSE_VERSION=$(docker compose version | grep -oP '\d+\.\d+\.\d+' | head -1)
            log_success "Docker Compose $COMPOSE_VERSION installed (v2)"
        else
            COMPOSE_VERSION=$(docker-compose --version | grep -oP '\d+\.\d+\.\d+')
            log_success "Docker Compose $COMPOSE_VERSION installed (v1)"
        fi
    fi

    # Check Git
    if ! command -v git &> /dev/null; then
        log_warning "Git not found"
        missing_deps+=("git")
    else
        log_success "Git installed"
    fi

    # Check curl
    if ! command -v curl &> /dev/null; then
        log_warning "curl not found"
        missing_deps+=("curl")
    else
        log_success "curl installed"
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_warning "Missing dependencies: ${missing_deps[*]}"
        read -p "Do you want to install missing dependencies? (y/N) " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_dependencies "${missing_deps[@]}"
        else
            log_error "Cannot continue without dependencies"
            exit 1
        fi
    else
        log_success "All dependencies satisfied"
    fi
}

install_dependencies() {
    log_info "Installing dependencies..."

    case "$PACKAGE_MANAGER" in
        apt-get)
            apt-get update -qq
            for dep in "$@"; do
                case "$dep" in
                    docker)
                        log_info "Installing Docker..."
                        curl -fsSL https://get.docker.com | sh
                        systemctl enable docker
                        systemctl start docker
                        usermod -aG docker $SUDO_USER 2>/dev/null || true
                        log_success "Docker installed"
                        ;;
                    docker-compose)
                        log_info "Installing Docker Compose..."
                        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
                        chmod +x /usr/local/bin/docker-compose
                        log_success "Docker Compose installed"
                        ;;
                    git)
                        apt-get install -y git
                        log_success "Git installed"
                        ;;
                    curl)
                        apt-get install -y curl
                        log_success "curl installed"
                        ;;
                esac
            done
            ;;
        yum)
            for dep in "$@"; do
                case "$dep" in
                    docker)
                        log_info "Installing Docker..."
                        yum install -y yum-utils
                        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
                        yum install -y docker-ce docker-ce-cli containerd.io
                        systemctl enable docker
                        systemctl start docker
                        usermod -aG docker $SUDO_USER 2>/dev/null || true
                        log_success "Docker installed"
                        ;;
                    docker-compose)
                        log_info "Installing Docker Compose..."
                        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
                        chmod +x /usr/local/bin/docker-compose
                        log_success "Docker Compose installed"
                        ;;
                    git)
                        yum install -y git
                        log_success "Git installed"
                        ;;
                    curl)
                        yum install -y curl
                        log_success "curl installed"
                        ;;
                esac
            done
            ;;
    esac
}

download_siem() {
    log_info "Downloading SIEM from GitHub..."

    # Create install directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    # Clone repository
    if [ -d "$INSTALL_DIR/.git" ]; then
        log_info "SIEM already exists, updating..."
        git pull origin "$GITHUB_BRANCH"
    else
        log_info "Cloning repository..."
        git clone -b "$GITHUB_BRANCH" "https://github.com/$GITHUB_REPO.git" .
    fi

    log_success "SIEM downloaded to $INSTALL_DIR"
}

configure_siem() {
    log_info "Starting configuration wizard..."
    echo ""

    cd "$INSTALL_DIR"

    # Check if .env already exists
    if [ -f ".env" ]; then
        log_warning "Configuration file (.env) already exists"
        read -p "Do you want to reconfigure? (y/N) " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing configuration"
            return
        fi
    fi

    # Create .env file
    log_info "Creating configuration file..."

    # Generate secure passwords
    DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
    JWT_SECRET=$(openssl rand -base64 64 | tr -dc 'a-zA-Z0-9' | head -c 64)

    # Get user input
    echo ""
    echo -e "${BLUE}=== Admin User ===${NC}"
    read -p "Admin username [admin]: " ADMIN_USER
    ADMIN_USER=${ADMIN_USER:-admin}
    read -p "Admin password [admin123]: " -s ADMIN_PASS
    echo ""
    ADMIN_PASS=${ADMIN_PASS:-admin123}

    echo ""
    echo -e "${BLUE}=== Network Configuration ===${NC}"
    read -p "API Port [8000]: " API_PORT
    API_PORT=${API_PORT:-8000}
    read -p "Frontend Port [3000]: " FRONTEND_PORT
    FRONTEND_PORT=${FRONTEND_PORT:-3000}

    echo ""
    echo -e "${BLUE}=== AI Configuration ===${NC}"
    echo "Choose AI provider:"
    echo "1) DeepSeek (free, recommended)"
    echo "2) Yandex GPT (requires API key)"
    echo "3) None (skip AI features)"
    read -p "Choice [1]: " AI_CHOICE
    AI_CHOICE=${AI_CHOICE:-1}

    AI_PROVIDER="none"
    AI_API_KEY=""

    case "$AI_CHOICE" in
        1)
            AI_PROVIDER="deepseek"
            read -p "DeepSeek API Key (or press Enter to skip): " AI_API_KEY
            ;;
        2)
            AI_PROVIDER="yandex_gpt"
            read -p "Yandex GPT API Key: " AI_API_KEY
            read -p "Yandex GPT Folder ID: " YANDEX_FOLDER_ID
            ;;
        3)
            AI_PROVIDER="none"
            ;;
    esac

    # Create .env file
    cat > .env << EOF
# SIEM Configuration File
# Generated: $(date)

# Database
POSTGRES_USER=siem
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_DB=siem_db
DATABASE_URL=postgresql://siem:$DB_PASSWORD@db:5432/siem_db

# Backend
JWT_SECRET=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_EXPIRATION=7200

# Admin User
DEFAULT_ADMIN_USERNAME=$ADMIN_USER
DEFAULT_ADMIN_PASSWORD=$ADMIN_PASS

# AI Configuration
AI_PROVIDER=$AI_PROVIDER
EOF

    if [ "$AI_PROVIDER" = "deepseek" ] && [ -n "$AI_API_KEY" ]; then
        echo "DEEPSEEK_API_KEY=$AI_API_KEY" >> .env
    fi

    if [ "$AI_PROVIDER" = "yandex_gpt" ]; then
        echo "YANDEX_GPT_API_KEY=$AI_API_KEY" >> .env
        echo "YANDEX_GPT_FOLDER_ID=$YANDEX_FOLDER_ID" >> .env
    fi

    cat >> .env << EOF

# Network
API_PORT=$API_PORT
FRONTEND_PORT=$FRONTEND_PORT

# Logging
LOG_LEVEL=INFO

# Security
CORS_ORIGINS=http://localhost:$FRONTEND_PORT,http://127.0.0.1:$FRONTEND_PORT
EOF

    chmod 600 .env
    log_success "Configuration saved to .env"
}

build_and_start() {
    log_info "Building and starting SIEM..."

    cd "$INSTALL_DIR"

    # Check docker-compose command
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi

    # Pull images
    log_info "Pulling Docker images..."
    $COMPOSE_CMD pull

    # Build custom images
    log_info "Building SIEM images..."
    $COMPOSE_CMD build

    # Start services
    log_info "Starting services..."
    $COMPOSE_CMD up -d

    log_success "SIEM started"
}

wait_for_services() {
    log_info "Waiting for services to be ready..."

    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:${API_PORT:-8000}/health > /dev/null 2>&1; then
            log_success "Backend is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    log_warning "Backend did not start in time. Check logs with: cd $INSTALL_DIR && docker-compose logs backend"
    echo ""
}

run_health_check() {
    log_info "Running health checks..."

    cd "$INSTALL_DIR"

    # Check docker-compose command
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi

    # Check containers
    local failed=0

    for service in db backend frontend; do
        if $COMPOSE_CMD ps | grep "$service" | grep -q "Up"; then
            log_success "$service is running"
        else
            log_error "$service is not running"
            failed=1
        fi
    done

    # Check API health
    if curl -s http://localhost:${API_PORT:-8000}/health | grep -q "healthy"; then
        log_success "API health check passed"
    else
        log_warning "API health check failed (service may still be starting)"
    fi

    return $failed
}

create_systemd_service() {
    log_info "Creating systemd service..."

    # Check docker-compose command
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="/usr/local/bin/docker-compose"
    else
        COMPOSE_CMD="/usr/bin/docker"
        COMPOSE_ARGS="compose"
    fi

    cat > /etc/systemd/system/siem.service << EOF
[Unit]
Description=SIEM System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=$COMPOSE_CMD ${COMPOSE_ARGS:-} up -d
ExecStop=$COMPOSE_CMD ${COMPOSE_ARGS:-} down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable siem.service

    log_success "Systemd service created and enabled"
}

print_summary() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║  ${BLUE}🎉 SIEM Installation Complete!${GREEN}                         ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Installation Directory:${NC} $INSTALL_DIR"
    echo -e "${BLUE}Configuration File:${NC} $INSTALL_DIR/.env"
    echo ""
    echo -e "${BLUE}Access URLs:${NC}"
    echo -e "  • Frontend: ${GREEN}http://localhost:${FRONTEND_PORT:-3000}${NC}"
    echo -e "  • API:      ${GREEN}http://localhost:${API_PORT:-8000}${NC}"
    echo -e "  • API Docs: ${GREEN}http://localhost:${API_PORT:-8000}/docs${NC}"
    echo ""
    echo -e "${BLUE}Default Credentials:${NC}"
    echo -e "  • Username: ${GREEN}$ADMIN_USER${NC}"
    echo -e "  • Password: ${GREEN}$ADMIN_PASS${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Change default password after first login!${NC}"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo -e "  • View logs:      ${GREEN}cd $INSTALL_DIR && docker-compose logs -f${NC}"
    echo -e "  • Stop SIEM:      ${GREEN}sudo systemctl stop siem${NC}"
    echo -e "  • Start SIEM:     ${GREEN}sudo systemctl start siem${NC}"
    echo -e "  • Restart SIEM:   ${GREEN}sudo systemctl restart siem${NC}"
    echo -e "  • SIEM status:    ${GREEN}sudo systemctl status siem${NC}"
    echo -e "  • Update SIEM:    ${GREEN}cd $INSTALL_DIR && git pull && docker-compose up -d --build${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Access the web interface at http://localhost:${FRONTEND_PORT:-3000}"
    echo "  2. Login with default credentials"
    echo "  3. Install Windows Agent on endpoints (see $INSTALL_DIR/agent/)"
    echo "  4. Configure detection rules (10 rules pre-installed)"
    echo "  5. Monitor Dashboard for events and alerts"
    echo ""
    echo -e "${GREEN}Documentation: $INSTALL_DIR/docs/${NC}"
    echo -e "${GREEN}Support: https://github.com/$GITHUB_REPO/issues${NC}"
    echo ""
}

cleanup_on_error() {
    log_error "Installation failed. Cleaning up..."

    if [ -d "$INSTALL_DIR" ]; then
        cd "$INSTALL_DIR"
        if command -v docker-compose &> /dev/null; then
            docker-compose down 2>/dev/null || true
        else
            docker compose down 2>/dev/null || true
        fi
    fi

    log_info "Check the error messages above and try again"
    exit 1
}

###############################################################################
# Main Installation Flow
###############################################################################

main() {
    # Set trap for errors
    trap cleanup_on_error ERR

    # Print banner
    print_banner

    # Check root
    check_root

    # Check OS
    check_os

    # Check dependencies
    check_dependencies

    # Download SIEM
    download_siem

    # Configure
    configure_siem

    # Build and start
    build_and_start

    # Wait for services
    wait_for_services

    # Health check
    if ! run_health_check; then
        log_warning "Some health checks failed. Check logs for details."
    fi

    # Create systemd service
    if command -v systemctl &> /dev/null; then
        create_systemd_service
    fi

    # Print summary
    print_summary

    log_success "Installation completed successfully!"
}

# Run main function
main "$@"
