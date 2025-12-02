"""
SQLAlchemy models for Agents and Assets
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Agent(Base):
    """Agent model - assets.Agents table"""

    __tablename__ = "Agents"
    __table_args__ = {'schema': 'assets'}

    AgentId = Column(String(36), primary_key=True)  # GUID
    Hostname = Column(String(255), nullable=False, unique=True, index=True)
    FQDN = Column(String(500))
    IPAddress = Column(String(45), index=True)
    MACAddress = Column(String(17))

    # System Info
    OSVersion = Column(String(100))
    OSBuild = Column(String(50))
    OSArchitecture = Column(String(10))  # x64, x86

    # Active Directory
    Domain = Column(String(255), index=True)
    OrganizationalUnit = Column(String(500))

    # Hardware
    Manufacturer = Column(String(100))
    Model = Column(String(100))
    SerialNumber = Column(String(100))
    CPUModel = Column(String(200))
    CPUCores = Column(Integer)
    TotalRAM_MB = Column(BigInteger)
    TotalDisk_GB = Column(BigInteger)

    # Agent Status
    AgentVersion = Column(String(20))
    Status = Column(String(20), default='offline', index=True)  # online, offline, error
    LastSeen = Column(DateTime, default=func.getutcdate(), index=True)
    LastInventory = Column(DateTime)
    LastReboot = Column(DateTime)

    # Metadata
    RegisteredAt = Column(DateTime, server_default=func.getutcdate())
    Configuration = Column(Text)  # JSON
    Tags = Column(String(500))  # JSON
    Location = Column(String(200))
    Owner = Column(String(200))
    CriticalityLevel = Column(String(20), default='medium')  # critical, high, medium, low

    # Relationships
    events = relationship("Event", back_populates="agent")
    installed_software = relationship("InstalledSoftware", back_populates="agent")
    services = relationship("WindowsService", back_populates="agent")
    alerts = relationship("Alert", back_populates="agent")

    def __repr__(self):
        return f"<Agent(id='{self.AgentId}', hostname='{self.Hostname}', status='{self.Status}')>"

    @property
    def is_online(self) -> bool:
        """Check if agent is online"""
        return self.Status == 'online'


class SoftwareCategory(Base):
    """Software Category model - assets.SoftwareCategories table"""

    __tablename__ = "SoftwareCategories"
    __table_args__ = {'schema': 'assets'}

    CategoryId = Column(Integer, primary_key=True, autoincrement=True)
    CategoryName = Column(String(50), nullable=False, unique=True)
    Description = Column(String(500))
    DefaultRiskLevel = Column(String(20), default='low')
    RequiresLicense = Column(Boolean, default=False)
    RequiresApproval = Column(Boolean, default=False)

    # Relationships
    software = relationship("SoftwareRegistry", back_populates="category")

    def __repr__(self):
        return f"<SoftwareCategory(id={self.CategoryId}, name='{self.CategoryName}')>"


class SoftwareRegistry(Base):
    """Software Registry model - assets.SoftwareRegistry table"""

    __tablename__ = "SoftwareRegistry"
    __table_args__ = {'schema': 'assets'}

    SoftwareId = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(255), nullable=False, index=True)
    NormalizedName = Column(String(255), index=True)
    Publisher = Column(String(255))
    CategoryId = Column(Integer, ForeignKey('assets.SoftwareCategories.CategoryId'))

    # Classification
    IsAllowed = Column(Boolean, default=True)
    IsForbidden = Column(Boolean, default=False, index=True)
    RequiresLicense = Column(Boolean, default=False)
    RiskLevel = Column(String(20), default='low')

    # MITRE ATT&CK
    MitreRelevant = Column(Boolean, default=False)
    MitreTechniques = Column(String(500))  # JSON

    # Metadata
    FirstSeenAt = Column(DateTime, server_default=func.getutcdate())
    LastSeenAt = Column(DateTime, server_default=func.getutcdate())
    Notes = Column(Text)

    # Relationships
    category = relationship("SoftwareCategory", back_populates="software")
    installations = relationship("InstalledSoftware", back_populates="software")

    def __repr__(self):
        return f"<SoftwareRegistry(id={self.SoftwareId}, name='{self.Name}')>"


class InstalledSoftware(Base):
    """Installed Software model - assets.InstalledSoftware table"""

    __tablename__ = "InstalledSoftware"
    __table_args__ = {'schema': 'assets'}

    InstallId = Column(BigInteger, primary_key=True, autoincrement=True)
    AgentId = Column(String(36), ForeignKey('assets.Agents.AgentId'), nullable=False, index=True)
    SoftwareId = Column(Integer, ForeignKey('assets.SoftwareRegistry.SoftwareId'))

    # Installation Info
    Name = Column(String(255), nullable=False)
    Version = Column(String(100))
    Publisher = Column(String(255))
    InstallDate = Column(Date)
    InstallLocation = Column(String(1000))
    UninstallString = Column(String(1000))
    EstimatedSize_KB = Column(BigInteger)

    # Status
    IsActive = Column(Boolean, default=True, index=True)
    FirstSeenAt = Column(DateTime, server_default=func.getutcdate())
    LastSeenAt = Column(DateTime, server_default=func.getutcdate())
    RemovedAt = Column(DateTime)

    # Relationships
    agent = relationship("Agent", back_populates="installed_software")
    software = relationship("SoftwareRegistry", back_populates="installations")

    def __repr__(self):
        return f"<InstalledSoftware(id={self.InstallId}, name='{self.Name}', version='{self.Version}')>"


class WindowsService(Base):
    """Windows Service model - assets.WindowsServices table"""

    __tablename__ = "WindowsServices"
    __table_args__ = {'schema': 'assets'}

    ServiceId = Column(BigInteger, primary_key=True, autoincrement=True)
    AgentId = Column(String(36), ForeignKey('assets.Agents.AgentId'), nullable=False, index=True)

    ServiceName = Column(String(255), nullable=False)
    DisplayName = Column(String(500))
    Status = Column(String(20))  # running, stopped, paused
    StartType = Column(String(20))  # auto, manual, disabled
    ServiceAccount = Column(String(255))
    ExecutablePath = Column(String(1000))

    IsActive = Column(Boolean, default=True)
    FirstSeenAt = Column(DateTime, server_default=func.getutcdate())
    LastSeenAt = Column(DateTime, server_default=func.getutcdate())

    # Relationships
    agent = relationship("Agent", back_populates="services")

    def __repr__(self):
        return f"<WindowsService(id={self.ServiceId}, name='{self.ServiceName}', status='{self.Status}')>"


class AssetChange(Base):
    """Asset Change model - assets.AssetChanges table"""

    __tablename__ = "AssetChanges"
    __table_args__ = {'schema': 'assets'}

    ChangeId = Column(BigInteger, primary_key=True, autoincrement=True)
    AgentId = Column(String(36), ForeignKey('assets.Agents.AgentId'), nullable=False, index=True)
    ChangeType = Column(String(50), nullable=False, index=True)
    ChangeDetails = Column(Text)  # JSON
    DetectedAt = Column(DateTime, server_default=func.getutcdate(), index=True)
    Severity = Column(Integer, default=0, index=True)

    def __repr__(self):
        return f"<AssetChange(id={self.ChangeId}, type='{self.ChangeType}', severity={self.Severity})>"
