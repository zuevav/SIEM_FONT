#!/bin/bash
# =====================================================================
# SIEM SYSTEM - AUTOMATED INSTALLER FOR LINUX
# =====================================================================
# Bash script for easy installation on Linux
# Run with sudo
# =====================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_step() { echo -e "\n${YELLOW}===> $1${NC}"; }

# Parse arguments
SKIP_DB=false
SKIP_BACKEND=false
SKIP_FRONTEND=false
SQL_SERVER="localhost"
SQL_USER=""
SQL_PASSWORD=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-db) SKIP_DB=true; shift ;;
        --skip-backend) SKIP_BACKEND=true; shift ;;
        --skip-frontend) SKIP_FRONTEND=true; shift ;;
        --sql-server) SQL_SERVER="$2"; shift 2 ;;
        --sql-user) SQL_USER="$2"; shift 2 ;;
        --sql-password) SQL_PASSWORD="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Banner
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║          SIEM SYSTEM - AUTOMATED INSTALLER               ║
║          Version 1.0.0                                    ║
╚═══════════════════════════════════════════════════════════╝
EOF

print_info "Starting installation process..."
print_info "Current directory: $(pwd)"

# =====================================================================
# STEP 1: CHECK PREREQUISITES
# =====================================================================

print_step "Step 1: Checking prerequisites"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi
print_success "Running as root"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
    print_success "Detected OS: $OS $VER"
else
    print_error "Cannot detect OS"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        print_success "Python version: $PYTHON_VERSION"
    else
        print_error "Python 3.11+ required. Current: $PYTHON_VERSION"
        print_info "Install with: sudo apt install python3.11 python3.11-venv python3-pip"
        exit 1
    fi
else
    print_error "Python 3 not found"
    exit 1
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    print_warning "pip3 not found, installing..."
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        apt-get update
        apt-get install -y python3-pip
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        yum install -y python3-pip
    fi
    print_success "pip3 installed"
else
    print_success "pip3 installed"
fi

# Check Node.js
if [ "$SKIP_FRONTEND" = false ]; then
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js version: $NODE_VERSION"
    else
        print_warning "Node.js not found. Frontend will be skipped."
        print_info "Install Node.js 18+ from: https://nodejs.org/"
        SKIP_FRONTEND=true
    fi
fi

# Install system dependencies
print_step "Installing system dependencies"

if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    print_info "Installing packages for Ubuntu/Debian..."
    apt-get update
    apt-get install -y \
        build-essential \
        libpq-dev \
        unixodbc-dev \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        curl \
        wget \
        git

    # Install MS SQL ODBC Driver
    if [ "$SKIP_DB" = false ]; then
        print_info "Installing MS SQL ODBC Driver..."
        if ! odbcinst -q -d -n "ODBC Driver 18 for SQL Server" &> /dev/null; then
            curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
            curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list > /etc/apt/sources.list.d/mssql-release.list
            apt-get update
            ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18
            echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc
            print_success "MS SQL ODBC Driver installed"
        else
            print_success "MS SQL ODBC Driver already installed"
        fi
    fi

elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    print_info "Installing packages for CentOS/RHEL..."
    yum install -y \
        gcc \
        gcc-c++ \
        make \
        postgresql-devel \
        unixODBC-devel \
        curl \
        wget \
        git

    if [ "$SKIP_DB" = false ]; then
        print_info "Installing MS SQL ODBC Driver..."
        curl https://packages.microsoft.com/config/rhel/8/prod.repo > /etc/yum.repos.d/mssql-release.repo
        yum remove -y unixODBC-utf16 unixODBC-utf16-devel
        ACCEPT_EULA=Y yum install -y msodbcsql18 mssql-tools18
        print_success "MS SQL ODBC Driver installed"
    fi
else
    print_warning "Unsupported OS: $OS. Some dependencies might be missing."
fi

print_success "System dependencies installed"

# =====================================================================
# STEP 2: CREATE ENVIRONMENT FILE
# =====================================================================

print_step "Step 2: Setting up environment configuration"

ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

if [ ! -f "$ENV_EXAMPLE" ]; then
    print_error "$ENV_EXAMPLE not found"
    exit 1
fi

if [ -f "$ENV_FILE" ]; then
    print_warning ".env file already exists"
    read -p "Overwrite? (y/N): " overwrite
    if [ "$overwrite" = "y" ] || [ "$overwrite" = "Y" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        print_success "Created .env from template"
    else
        print_info "Keeping existing .env file"
    fi
else
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    print_success "Created .env from template"
fi

# Update SQL Server settings
if [ "$SKIP_DB" = false ]; then
    print_info "Updating SQL Server connection settings in .env..."
    sed -i "s/^MSSQL_SERVER=.*/MSSQL_SERVER=$SQL_SERVER/" "$ENV_FILE"

    if [ -n "$SQL_USER" ]; then
        sed -i "s/^MSSQL_USER=.*/MSSQL_USER=$SQL_USER/" "$ENV_FILE"
        sed -i "s/^MSSQL_PASSWORD=.*/MSSQL_PASSWORD=$SQL_PASSWORD/" "$ENV_FILE"
    fi

    print_success "Updated .env with SQL Server settings"
fi

print_warning "IMPORTANT: Please edit .env file and configure:"
print_info "  - Yandex GPT API keys"
print_info "  - SMTP settings"
print_info "  - Organization info for CBR reports"
print_info "  - JWT_SECRET_KEY"

read -p "Press Enter to continue after editing .env, or type 'skip' to continue: " continue_install

# =====================================================================
# STEP 3: INSTALL DATABASE
# =====================================================================

if [ "$SKIP_DB" = false ]; then
    print_step "Step 3: Installing database schema"

    DB_SCRIPTS=(
        "database/schema.sql"
        "database/procedures.sql"
        "database/triggers.sql"
        "database/seed.sql"
        "database/jobs.sql"
    )

    for script in "${DB_SCRIPTS[@]}"; do
        if [ ! -f "$script" ]; then
            print_error "Script not found: $script"
            exit 1
        fi

        print_info "Executing $script..."

        if [ -n "$SQL_USER" ]; then
            /opt/mssql-tools18/bin/sqlcmd -S "$SQL_SERVER" -U "$SQL_USER" -P "$SQL_PASSWORD" -i "$script" -b
        else
            /opt/mssql-tools18/bin/sqlcmd -S "$SQL_SERVER" -E -i "$script" -b
        fi

        print_success "Executed $script"
    done

    print_success "Database installation completed!"

else
    print_warning "Skipping database installation"
fi

# =====================================================================
# STEP 4: INSTALL BACKEND
# =====================================================================

if [ "$SKIP_BACKEND" = false ]; then
    print_step "Step 4: Installing backend dependencies"

    cd backend

    # Create virtual environment
    print_info "Creating Python virtual environment..."
    python3 -m venv venv

    # Activate and install
    print_info "Installing Python packages..."
    source venv/bin/activate

    pip install --upgrade pip
    pip install -r requirements.txt

    deactivate
    cd ..

    print_success "Backend installation completed!"

else
    print_warning "Skipping backend installation"
fi

# =====================================================================
# STEP 5: INSTALL FRONTEND
# =====================================================================

if [ "$SKIP_FRONTEND" = false ]; then
    print_step "Step 5: Installing frontend dependencies"

    if [ -f "frontend/package.json" ]; then
        cd frontend
        print_info "Installing npm packages..."
        npm install
        cd ..
        print_success "Frontend dependencies installed"
    else
        print_warning "Frontend not found, skipping"
    fi
else
    print_warning "Skipping frontend installation"
fi

# =====================================================================
# STEP 6: INSTALL NETWORK MONITOR
# =====================================================================

print_step "Step 6: Installing Network Monitor (optional)"

if [ -d "network_monitor" ]; then
    read -p "Install Network Monitor for SNMP/Syslog/NetFlow monitoring? (y/N): " install_netmon

    if [ "$install_netmon" = "y" ] || [ "$install_netmon" = "Y" ]; then
        cd network_monitor

        # Create virtual environment
        print_info "Creating Python virtual environment for Network Monitor..."
        python3 -m venv venv

        # Activate and install
        print_info "Installing Network Monitor dependencies..."
        source venv/bin/activate

        pip install --upgrade pip
        pip install -r requirements.txt

        deactivate

        # Create config from template
        if [ ! -f "config.yaml" ]; then
            if [ -f "config.yaml.example" ]; then
                cp config.yaml.example config.yaml
                print_success "Created config.yaml from template"
                print_warning "Edit network_monitor/config.yaml before starting!"
            fi
        fi

        cd ..
        print_success "Network Monitor installed successfully!"
        print_info "Configure network_monitor/config.yaml with:"
        print_info "  - SIEM server URL and API key"
        print_info "  - SNMP devices list"
        print_info "  - Syslog and NetFlow settings"
        print_info "To install as systemd service: cd network_monitor && sudo ./install.sh"
    else
        print_info "Skipping Network Monitor installation"
    fi
else
    print_warning "Network Monitor directory not found, skipping"
fi

# =====================================================================
# STEP 7: CREATE HELPER SCRIPTS
# =====================================================================

print_step "Step 7: Creating helper scripts"

# Start backend script
cat > start_backend.sh << 'EOF'
#!/bin/bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
EOF

chmod +x start_backend.sh
print_success "Created start_backend.sh"

# Start frontend script
if [ "$SKIP_FRONTEND" = false ] && [ -d "frontend" ]; then
    cat > start_frontend.sh << 'EOF'
#!/bin/bash
cd frontend
npm run dev
EOF
    chmod +x start_frontend.sh
    print_success "Created start_frontend.sh"
fi

# Start network monitor script
if [ -d "network_monitor" ]; then
    cat > start_network_monitor.sh << 'EOF'
#!/bin/bash
cd network_monitor
source venv/bin/activate
python main.py
EOF
    chmod +x start_network_monitor.sh
    print_success "Created start_network_monitor.sh"
fi

# Stop all script
cat > stop_all.sh << 'EOF'
#!/bin/bash
echo "Stopping SIEM services..."
pkill -f "uvicorn app.main:app"
pkill -f "npm run dev"
echo "Done."
EOF

chmod +x stop_all.sh
print_success "Created stop_all.sh"

# Systemd service (optional)
if command -v systemctl &> /dev/null; then
    print_info "Creating systemd service..."

    cat > /etc/systemd/system/siem-backend.service << EOF
[Unit]
Description=SIEM Backend API
After=network.target

[Service]
Type=simple
User=$(logname)
WorkingDirectory=$(pwd)/backend
Environment="PATH=$(pwd)/backend/venv/bin"
ExecStart=$(pwd)/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    print_success "Created systemd service: siem-backend.service"
    print_info "Enable with: sudo systemctl enable siem-backend"
    print_info "Start with: sudo systemctl start siem-backend"
fi

# =====================================================================
# COMPLETION
# =====================================================================

cat << "EOF"

╔═══════════════════════════════════════════════════════════╗
║          INSTALLATION COMPLETED SUCCESSFULLY!             ║
╚═══════════════════════════════════════════════════════════╝

EOF

print_success "SIEM System has been installed!"

print_info "\nNext steps:"
echo "1. Edit .env file with your configuration"
echo "2. Start backend:  ./start_backend.sh"

if [ "$SKIP_FRONTEND" = false ]; then
    echo "3. Start frontend: ./start_frontend.sh"
fi

if [ -d "network_monitor" ] && [ "$install_netmon" = "y" ]; then
    echo "4. Configure network_monitor/config.yaml"
    echo "5. Start network monitor: ./start_network_monitor.sh"
    echo "   Or install as systemd service: cd network_monitor && sudo ./install.sh"
fi

echo -e "\n${CYAN}Access the system:${NC}"
echo "  Backend API:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"

if [ "$SKIP_FRONTEND" = false ]; then
    echo "  Frontend:     http://localhost:5173"
fi

echo -e "\n${CYAN}Default credentials:${NC}"
echo "  Username: admin"
echo "  Password: Admin123!"

print_warning "\n⚠ SECURITY:"
print_info "  - Change default passwords"
print_info "  - Configure JWT_SECRET_KEY in .env"
print_info "  - Set up Yandex GPT API keys"
print_info "  - Configure SMTP for notifications"

echo -e "\nFor help, see README.md"
