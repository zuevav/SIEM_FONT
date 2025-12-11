"""
SQLAlchemy models for Agents and Assets
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Agent(Base):
    """Agent model - assets.agents table (PostgreSQL snake_case)"""

    __tablename__ = "agents"
    __table_args__ = {'schema': 'assets'}

    # Column names match PostgreSQL schema (snake_case)
    agent_id = Column('agent_id', UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    hostname = Column('hostname', String(255), nullable=False, unique=True, index=True)
    fqdn = Column('fqdn', String(500))
    ip_address = Column('ip_address', String(45), index=True)
    mac_address = Column('mac_address', String(17))

    # System Info
    os_version = Column('os_version', String(100))
    os_build = Column('os_build', String(50))
    os_architecture = Column('os_architecture', String(10))  # x64, x86

    # Active Directory
    domain = Column('domain', String(255), index=True)
    organizational_unit = Column('organizational_unit', String(500))

    # Hardware
    manufacturer = Column('manufacturer', String(100))
    model = Column('model', String(100))
    serial_number = Column('serial_number', String(100))
    cpu_model = Column('cpu_model', String(200))
    cpu_cores = Column('cpu_cores', Integer)
    total_ram_mb = Column('total_ram_mb', BigInteger)
    total_disk_gb = Column('total_disk_gb', BigInteger)

    # Agent Status
    agent_version = Column('agent_version', String(20))
    status = Column('status', String(20), default='offline', index=True)  # online, offline, error
    last_seen = Column('last_seen', DateTime, index=True)
    last_inventory = Column('last_inventory', DateTime)
    last_reboot = Column('last_reboot', DateTime)

    # Metadata
    registered_at = Column('registered_at', DateTime, server_default=func.now())
    configuration = Column('configuration', JSONB)
    tags = Column('tags', JSONB)
    location = Column('location', String(200))
    owner = Column('owner', String(200))
    criticality_level = Column('criticality_level', String(20), default='medium')  # critical, high, medium, low

    # Relationships
    events = relationship("Event", back_populates="agent")
    installed_software = relationship("InstalledSoftware", back_populates="agent")
    services = relationship("WindowsService", back_populates="agent")
    alerts = relationship("Alert", back_populates="agent")

    # PascalCase aliases for backward compatibility
    @property
    def AgentId(self):
        return self.agent_id

    @property
    def Hostname(self):
        return self.hostname

    @property
    def IPAddress(self):
        return self.ip_address

    @property
    def Status(self):
        return self.status

    @property
    def LastSeen(self):
        return self.last_seen

    def __repr__(self):
        return f"<Agent(id='{self.agent_id}', hostname='{self.hostname}', status='{self.status}')>"

    @property
    def is_online(self) -> bool:
        """Check if agent is online"""
        return self.status == 'online'


class SoftwareCategory(Base):
    """Software Category model - assets.software_categories table (PostgreSQL snake_case)"""

    __tablename__ = "software_categories"
    __table_args__ = {'schema': 'assets'}

    category_id = Column('category_id', Integer, primary_key=True, autoincrement=True)
    category_name = Column('category_name', String(50), nullable=False, unique=True)
    description = Column('description', String(500))
    default_risk_level = Column('default_risk_level', String(20), default='low')
    requires_license = Column('requires_license', Boolean, default=False)
    requires_approval = Column('requires_approval', Boolean, default=False)

    # Relationships
    software = relationship("SoftwareRegistry", back_populates="category")

    # PascalCase aliases for backward compatibility
    @property
    def CategoryId(self):
        return self.category_id

    @property
    def CategoryName(self):
        return self.category_name

    def __repr__(self):
        return f"<SoftwareCategory(id={self.category_id}, name='{self.category_name}')>"


class SoftwareRegistry(Base):
    """Software Registry model - assets.software_registry table (PostgreSQL snake_case)"""

    __tablename__ = "software_registry"
    __table_args__ = {'schema': 'assets'}

    software_id = Column('software_id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(255), nullable=False, index=True)
    normalized_name = Column('normalized_name', String(255), index=True)
    publisher = Column('publisher', String(255))
    category_id = Column('category_id', Integer, ForeignKey('assets.software_categories.category_id'))

    # Classification
    is_allowed = Column('is_allowed', Boolean, default=True)
    is_forbidden = Column('is_forbidden', Boolean, default=False, index=True)
    requires_license = Column('requires_license', Boolean, default=False)
    risk_level = Column('risk_level', String(20), default='low')

    # MITRE ATT&CK
    mitre_relevant = Column('mitre_relevant', Boolean, default=False)
    mitre_techniques = Column('mitre_techniques', JSONB)

    # Metadata
    first_seen_at = Column('first_seen_at', DateTime, server_default=func.now())
    last_seen_at = Column('last_seen_at', DateTime, server_default=func.now())
    notes = Column('notes', Text)

    # Relationships
    category = relationship("SoftwareCategory", back_populates="software")
    installations = relationship("InstalledSoftware", back_populates="software")

    # PascalCase aliases for backward compatibility
    @property
    def SoftwareId(self):
        return self.software_id

    @property
    def Name(self):
        return self.name

    def __repr__(self):
        return f"<SoftwareRegistry(id={self.software_id}, name='{self.name}')>"


class InstalledSoftware(Base):
    """Installed Software model - assets.installed_software table (PostgreSQL snake_case)"""

    __tablename__ = "installed_software"
    __table_args__ = {'schema': 'assets'}

    install_id = Column('install_id', BigInteger, primary_key=True, autoincrement=True)
    agent_id = Column('agent_id', UUID(as_uuid=True), ForeignKey('assets.agents.agent_id'), nullable=False, index=True)
    software_id = Column('software_id', Integer, ForeignKey('assets.software_registry.software_id'))

    # Installation Info
    name = Column('name', String(255), nullable=False)
    version = Column('version', String(100))
    publisher = Column('publisher', String(255))
    install_date = Column('install_date', Date)
    install_location = Column('install_location', String(1000))
    uninstall_string = Column('uninstall_string', String(1000))
    estimated_size_kb = Column('estimated_size_kb', BigInteger)

    # Status
    is_active = Column('is_active', Boolean, default=True, index=True)
    first_seen_at = Column('first_seen_at', DateTime, server_default=func.now())
    last_seen_at = Column('last_seen_at', DateTime, server_default=func.now())
    removed_at = Column('removed_at', DateTime)

    # Relationships
    agent = relationship("Agent", back_populates="installed_software")
    software = relationship("SoftwareRegistry", back_populates="installations")

    def __repr__(self):
        return f"<InstalledSoftware(id={self.install_id}, name='{self.name}', version='{self.version}')>"


class WindowsService(Base):
    """Windows Service model - assets.windows_services table (PostgreSQL snake_case)"""

    __tablename__ = "windows_services"
    __table_args__ = {'schema': 'assets'}

    service_id = Column('service_id', BigInteger, primary_key=True, autoincrement=True)
    agent_id = Column('agent_id', UUID(as_uuid=True), ForeignKey('assets.agents.agent_id'), nullable=False, index=True)

    service_name = Column('service_name', String(255), nullable=False)
    display_name = Column('display_name', String(500))
    status = Column('status', String(20))  # running, stopped, paused
    start_type = Column('start_type', String(20))  # auto, manual, disabled
    service_account = Column('service_account', String(255))
    executable_path = Column('executable_path', String(1000))

    is_active = Column('is_active', Boolean, default=True)
    first_seen_at = Column('first_seen_at', DateTime, server_default=func.now())
    last_seen_at = Column('last_seen_at', DateTime, server_default=func.now())

    # Relationships
    agent = relationship("Agent", back_populates="services")

    def __repr__(self):
        return f"<WindowsService(id={self.service_id}, name='{self.service_name}', status='{self.status}')>"


class AssetChange(Base):
    """Asset Change model - assets.asset_changes table (PostgreSQL snake_case)"""

    __tablename__ = "asset_changes"
    __table_args__ = {'schema': 'assets'}

    change_id = Column('change_id', BigInteger, primary_key=True, autoincrement=True)
    agent_id = Column('agent_id', UUID(as_uuid=True), ForeignKey('assets.agents.agent_id'), nullable=False, index=True)
    change_type = Column('change_type', String(50), nullable=False, index=True)
    change_details = Column('change_details', JSONB)
    detected_at = Column('detected_at', DateTime, server_default=func.now(), index=True)
    severity = Column('severity', Integer, default=0, index=True)

    def __repr__(self):
        return f"<AssetChange(id={self.change_id}, type='{self.change_type}', severity={self.severity})>"


# ============================================================================
# AGENT DEPLOYMENT MANAGEMENT
# ============================================================================

class AgentPackage(Base):
    """Agent Package model - stores uploaded agent installation packages"""

    __tablename__ = "AgentPackages"
    __table_args__ = {'schema': 'assets'}

    PackageId = Column(Integer, primary_key=True, autoincrement=True)
    Version = Column(String(20), nullable=False, index=True)
    FileName = Column(String(255), nullable=False)
    FileSize = Column(BigInteger)
    FileHash = Column(String(64))  # SHA256

    # Package details
    Platform = Column(String(20), default='windows')  # windows, linux
    Architecture = Column(String(10), default='x64')  # x64, x86
    Description = Column(Text)
    ReleaseNotes = Column(Text)

    # File storage
    StoragePath = Column(String(500))  # Path on server
    DownloadUrl = Column(String(500))  # URL for download

    # Status
    IsActive = Column(Boolean, default=True)
    IsLatest = Column(Boolean, default=False)
    UploadedBy = Column(String(100))
    UploadedAt = Column(DateTime, server_default=func.getutcdate())

    # Relationships
    deployments = relationship("AgentDeployment", back_populates="package")

    def __repr__(self):
        return f"<AgentPackage(id={self.PackageId}, version='{self.Version}')>"


class AgentDeployment(Base):
    """Agent Deployment configuration model"""

    __tablename__ = "AgentDeployments"
    __table_args__ = {'schema': 'assets'}

    DeploymentId = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(100), nullable=False)
    Description = Column(Text)

    # Package reference
    PackageId = Column(Integer, ForeignKey('assets.AgentPackages.PackageId'), nullable=False)

    # Deployment settings
    DeploymentMode = Column(String(20), default='selected')  # all, selected, ou
    TargetOU = Column(String(500))  # OU path for OU-based deployment
    ServerUrl = Column(String(500), nullable=False)  # SIEM server URL
    NetworkPath = Column(String(500))  # UNC path to NETLOGON folder

    # Protection settings
    EnableProtection = Column(Boolean, default=True)
    InstallWatchdog = Column(Boolean, default=True)

    # Status
    Status = Column(String(20), default='draft')  # draft, active, paused, completed
    CreatedBy = Column(String(100))
    CreatedAt = Column(DateTime, server_default=func.getutcdate())
    UpdatedAt = Column(DateTime, server_default=func.getutcdate(), onupdate=func.getutcdate())
    ActivatedAt = Column(DateTime)

    # Statistics
    TotalTargets = Column(Integer, default=0)
    DeployedCount = Column(Integer, default=0)
    FailedCount = Column(Integer, default=0)

    # Relationships
    package = relationship("AgentPackage", back_populates="deployments")
    targets = relationship("AgentDeploymentTarget", back_populates="deployment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AgentDeployment(id={self.DeploymentId}, name='{self.Name}', status='{self.Status}')>"


class AgentDeploymentTarget(Base):
    """Target computers for agent deployment"""

    __tablename__ = "AgentDeploymentTargets"
    __table_args__ = {'schema': 'assets'}

    TargetId = Column(Integer, primary_key=True, autoincrement=True)
    DeploymentId = Column(Integer, ForeignKey('assets.AgentDeployments.DeploymentId'), nullable=False)

    # Target computer info
    ComputerName = Column(String(255), nullable=False, index=True)
    ComputerDN = Column(String(500))  # Distinguished Name from AD
    IPAddress = Column(String(45))

    # Deployment status
    Status = Column(String(20), default='pending')  # pending, deploying, success, failed, skipped
    DeployedAt = Column(DateTime)
    DeployedVersion = Column(String(20))
    ErrorMessage = Column(Text)
    RetryCount = Column(Integer, default=0)

    # Relationships
    deployment = relationship("AgentDeployment", back_populates="targets")

    def __repr__(self):
        return f"<AgentDeploymentTarget(id={self.TargetId}, computer='{self.ComputerName}', status='{self.Status}')>"

