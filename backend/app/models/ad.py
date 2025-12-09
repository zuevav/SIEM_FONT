"""
SQLAlchemy models for Active Directory integration and Software Installation Requests
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ADUser(Base):
    """Active Directory User model - ad.Users table"""

    __tablename__ = "Users"
    __table_args__ = {'schema': 'ad'}

    ADUserId = Column(BigInteger, primary_key=True, autoincrement=True)
    ObjectGUID = Column(String(36), unique=True, index=True)  # AD Object GUID
    SID = Column(String(100), unique=True, index=True)  # Security Identifier

    # Basic Info
    SamAccountName = Column(String(256), nullable=False, index=True)  # Login name
    UserPrincipalName = Column(String(512), index=True)  # user@domain.com
    DisplayName = Column(String(256))
    FirstName = Column(String(100))
    LastName = Column(String(100))
    Email = Column(String(256))
    Phone = Column(String(50))
    Mobile = Column(String(50))

    # Organization
    Department = Column(String(256))
    Title = Column(String(256))  # Job title
    Manager = Column(String(256))  # Manager DN
    ManagerDisplayName = Column(String(256))
    Company = Column(String(256))
    Office = Column(String(256))

    # AD Location
    DistinguishedName = Column(String(1000), index=True)  # Full DN path
    OrganizationalUnit = Column(String(500))
    Domain = Column(String(256), index=True)

    # Account Status
    IsEnabled = Column(Boolean, default=True, index=True)
    IsLocked = Column(Boolean, default=False, index=True)
    PasswordExpired = Column(Boolean, default=False)
    PasswordNeverExpires = Column(Boolean, default=False)
    PasswordLastSet = Column(DateTime)
    LastLogon = Column(DateTime)
    LastLogonTimestamp = Column(DateTime)
    AccountExpires = Column(DateTime)
    BadPasswordCount = Column(Integer, default=0)

    # Groups (JSON array of group names)
    MemberOf = Column(Text)  # JSON array

    # Sync metadata
    CreatedAt = Column(DateTime)  # AD creation date
    ModifiedAt = Column(DateTime)  # AD modification date
    SyncedAt = Column(DateTime, server_default=func.getutcdate())

    # SIEM metadata
    RiskScore = Column(Integer, default=0)  # 0-100
    Notes = Column(Text)
    Tags = Column(String(500))  # JSON

    # Relationships
    software_requests = relationship("SoftwareInstallRequest", back_populates="ad_user")

    def __repr__(self):
        return f"<ADUser(id={self.ADUserId}, sam='{self.SamAccountName}', name='{self.DisplayName}')>"


class ADComputer(Base):
    """Active Directory Computer model - ad.Computers table"""

    __tablename__ = "Computers"
    __table_args__ = {'schema': 'ad'}

    ADComputerId = Column(BigInteger, primary_key=True, autoincrement=True)
    ObjectGUID = Column(String(36), unique=True, index=True)
    SID = Column(String(100), unique=True, index=True)

    # Basic Info
    Name = Column(String(256), nullable=False, index=True)
    DNSHostName = Column(String(512), index=True)
    Description = Column(String(500))

    # Network
    IPv4Address = Column(String(45))
    IPv6Address = Column(String(45))

    # System Info
    OperatingSystem = Column(String(256))
    OperatingSystemVersion = Column(String(100))
    OperatingSystemServicePack = Column(String(100))

    # AD Location
    DistinguishedName = Column(String(1000), index=True)
    OrganizationalUnit = Column(String(500))
    Domain = Column(String(256), index=True)

    # Status
    IsEnabled = Column(Boolean, default=True, index=True)
    LastLogon = Column(DateTime)
    LastLogonTimestamp = Column(DateTime)
    WhenCreated = Column(DateTime)
    WhenChanged = Column(DateTime)

    # Groups
    MemberOf = Column(Text)  # JSON array

    # Agent link
    AgentId = Column(String(36), ForeignKey('assets.Agents.AgentId'), nullable=True)

    # Sync metadata
    SyncedAt = Column(DateTime, server_default=func.getutcdate())

    # SIEM metadata
    CriticalityLevel = Column(String(20), default='medium')
    Notes = Column(Text)
    Tags = Column(String(500))

    def __repr__(self):
        return f"<ADComputer(id={self.ADComputerId}, name='{self.Name}', os='{self.OperatingSystem}')>"


class SoftwareInstallRequest(Base):
    """Software Installation Request model - assets.SoftwareInstallRequests table

    Workflow:
    1. User wants to install software on their computer
    2. Agent intercepts the installation attempt
    3. Agent creates a request in SIEM with software details and user comment
    4. Administrator receives notification
    5. Administrator approves or denies in SIEM interface
    6. Agent receives decision and allows/blocks installation
    """

    __tablename__ = "SoftwareInstallRequests"
    __table_args__ = {'schema': 'assets'}

    RequestId = Column(BigInteger, primary_key=True, autoincrement=True)

    # Request source
    AgentId = Column(String(36), ForeignKey('assets.Agents.AgentId'), nullable=False, index=True)
    ComputerName = Column(String(256), index=True)

    # User info
    ADUserId = Column(BigInteger, ForeignKey('ad.Users.ADUserId'), nullable=True)
    UserName = Column(String(256), nullable=False, index=True)  # DOMAIN\user
    UserDisplayName = Column(String(256))
    UserDepartment = Column(String(256))
    UserEmail = Column(String(256))

    # Software details
    SoftwareName = Column(String(500), nullable=False)
    SoftwareVersion = Column(String(100))
    SoftwarePublisher = Column(String(256))
    InstallerPath = Column(String(1000))  # Path to installer
    InstallerHash = Column(String(128))  # SHA256 hash
    InstallerSize = Column(BigInteger)  # Size in bytes

    # Threat Intelligence (auto-filled)
    VirusTotalDetections = Column(Integer, default=0)
    VirusTotalLink = Column(String(500))
    ThreatIntelScore = Column(Integer, default=0)  # 0-100

    # User's request
    UserComment = Column(Text)  # Why user needs this software
    BusinessJustification = Column(Text)
    RequestedAt = Column(DateTime, server_default=func.getutcdate(), index=True)

    # Status
    Status = Column(String(20), default='pending', index=True)
    # pending, approved, denied, expired, cancelled

    # Admin decision
    ReviewedBy = Column(Integer, ForeignKey('security.Users.UserId'), nullable=True)
    ReviewedAt = Column(DateTime)
    AdminComment = Column(Text)  # Admin's reason for decision

    # Installation tracking
    ApprovedUntil = Column(DateTime)  # Approval expiration
    InstalledAt = Column(DateTime)  # When user actually installed
    InstallationConfirmed = Column(Boolean, default=False)

    # Notification tracking
    NotificationSent = Column(Boolean, default=False)
    NotificationSentAt = Column(DateTime)

    # Relationships
    ad_user = relationship("ADUser", back_populates="software_requests")
    reviewer = relationship("User", foreign_keys=[ReviewedBy])

    def __repr__(self):
        return f"<SoftwareInstallRequest(id={self.RequestId}, software='{self.SoftwareName}', user='{self.UserName}', status='{self.Status}')>"


class ADGroup(Base):
    """Active Directory Group model - ad.Groups table"""

    __tablename__ = "Groups"
    __table_args__ = {'schema': 'ad'}

    ADGroupId = Column(BigInteger, primary_key=True, autoincrement=True)
    ObjectGUID = Column(String(36), unique=True, index=True)
    SID = Column(String(100), unique=True, index=True)

    # Basic Info
    Name = Column(String(256), nullable=False, index=True)
    SamAccountName = Column(String(256), index=True)
    Description = Column(String(500))

    # Group type
    GroupCategory = Column(String(50))  # Security, Distribution
    GroupScope = Column(String(50))  # DomainLocal, Global, Universal

    # AD Location
    DistinguishedName = Column(String(1000), index=True)
    Domain = Column(String(256), index=True)

    # Membership
    MemberCount = Column(Integer, default=0)
    Members = Column(Text)  # JSON array of DNs
    MemberOf = Column(Text)  # JSON array (nested groups)

    # Metadata
    WhenCreated = Column(DateTime)
    WhenChanged = Column(DateTime)
    SyncedAt = Column(DateTime, server_default=func.getutcdate())

    # SIEM metadata
    IsPrivileged = Column(Boolean, default=False, index=True)  # Admin groups
    Notes = Column(Text)

    def __repr__(self):
        return f"<ADGroup(id={self.ADGroupId}, name='{self.Name}', members={self.MemberCount})>"


class ADSyncLog(Base):
    """AD Synchronization Log - ad.SyncLogs table"""

    __tablename__ = "SyncLogs"
    __table_args__ = {'schema': 'ad'}

    LogId = Column(BigInteger, primary_key=True, autoincrement=True)

    SyncType = Column(String(50), nullable=False)  # full, incremental, users, computers, groups
    Status = Column(String(20), default='running')  # running, completed, failed

    StartedAt = Column(DateTime, server_default=func.getutcdate())
    CompletedAt = Column(DateTime)

    # Statistics
    UsersAdded = Column(Integer, default=0)
    UsersUpdated = Column(Integer, default=0)
    UsersDisabled = Column(Integer, default=0)
    ComputersAdded = Column(Integer, default=0)
    ComputersUpdated = Column(Integer, default=0)
    GroupsAdded = Column(Integer, default=0)
    GroupsUpdated = Column(Integer, default=0)

    # Errors
    ErrorCount = Column(Integer, default=0)
    ErrorDetails = Column(Text)  # JSON

    def __repr__(self):
        return f"<ADSyncLog(id={self.LogId}, type='{self.SyncType}', status='{self.Status}')>"


class RemoteSession(Base):
    """Remote Desktop Session for IT support - assets.RemoteSessions table

    Workflow:
    1. User calls IT support requesting help
    2. Admin finds user in SIEM and clicks "Remote Connect"
    3. SIEM creates session record and sends command to agent
    4. Agent shows popup to user asking for consent
    5. User accepts - agent starts Remote Assistance
    6. Admin connects using provided connection info
    7. Session ends - admin or user terminates
    """

    __tablename__ = "RemoteSessions"
    __table_args__ = {'schema': 'assets'}

    SessionId = Column(BigInteger, primary_key=True, autoincrement=True)
    SessionGUID = Column(String(36), unique=True, index=True, nullable=False)

    # Target (where to connect)
    AgentId = Column(String(36), ForeignKey('assets.Agents.AgentId'), nullable=False, index=True)
    ComputerName = Column(String(256), index=True)
    ComputerIP = Column(String(45))

    # Target user
    TargetUserName = Column(String(256), index=True)
    TargetUserDisplayName = Column(String(256))
    ADUserId = Column(BigInteger, ForeignKey('ad.Users.ADUserId'), nullable=True)

    # Admin (who connects)
    InitiatedBy = Column(Integer, ForeignKey('security.Users.UserId'), nullable=False)
    InitiatedByName = Column(String(256))

    # Session type
    SessionType = Column(String(50), default='remote_assistance')
    # remote_assistance - Windows Remote Assistance (msra)
    # shadow - RDP Shadow session
    # vnc - VNC connection
    # screen_share - Screen share only (view)

    # Session details
    Reason = Column(String(500))  # Why admin needs to connect
    TicketNumber = Column(String(100))  # Related support ticket

    # Status workflow
    Status = Column(String(30), default='pending', index=True)
    # pending - waiting for user consent
    # user_declined - user rejected
    # connecting - establishing connection
    # active - session in progress
    # completed - ended normally
    # timeout - user didn't respond
    # failed - connection error
    # cancelled - admin cancelled

    # Timestamps
    RequestedAt = Column(DateTime, server_default=func.getutcdate(), index=True)
    UserRespondedAt = Column(DateTime)
    ConnectedAt = Column(DateTime)
    EndedAt = Column(DateTime)

    # Connection info (for admin to connect)
    ConnectionString = Column(String(1000))  # Invitation file content or connection URL
    ConnectionPassword = Column(String(100))  # One-time password if needed
    Port = Column(Integer)  # Port for connection

    # User consent
    UserConsented = Column(Boolean, default=False)
    UserConsentMessage = Column(String(500))

    # Session recording
    RecordSession = Column(Boolean, default=False)
    RecordingPath = Column(String(500))

    # Duration
    DurationSeconds = Column(Integer)

    # Notes
    Notes = Column(Text)

    # Relationships
    initiator = relationship("User", foreign_keys=[InitiatedBy])
    ad_user = relationship("ADUser", foreign_keys=[ADUserId])

    def __repr__(self):
        return f"<RemoteSession(id={self.SessionId}, target='{self.ComputerName}', status='{self.Status}')>"


class PeerHelpSession(Base):
    """Peer-to-Peer Help Session - users helping each other

    Workflow:
    1. User A clicks "Help me" button on desktop
    2. Agent generates unique token and sends to SIEM
    3. SIEM creates session and returns shareable link
    4. User A sends link to User B via messenger (Yandex, Telegram, etc.)
    5. User B opens link in browser
    6. Agent on User A's computer shows consent dialog
    7. User A confirms - screen sharing starts
    8. Both users can see screen and interact
    """

    __tablename__ = "PeerHelpSessions"
    __table_args__ = {'schema': 'assets'}

    SessionId = Column(BigInteger, primary_key=True, autoincrement=True)
    SessionToken = Column(String(64), unique=True, index=True, nullable=False)  # Short token for URL

    # Requester (who needs help)
    RequesterAgentId = Column(String(36), ForeignKey('assets.Agents.AgentId'), nullable=False, index=True)
    RequesterComputerName = Column(String(256))
    RequesterIP = Column(String(45))
    RequesterUserName = Column(String(256))
    RequesterDisplayName = Column(String(256))

    # Helper (who provides help) - filled when helper joins
    HelperName = Column(String(256))
    HelperIP = Column(String(45))
    HelperUserAgent = Column(String(500))

    # Session details
    Description = Column(String(500))  # What help is needed
    ShareableLink = Column(String(500))  # Full URL to share

    # Status
    Status = Column(String(30), default='waiting', index=True)
    # waiting - waiting for helper to join
    # helper_joined - helper opened the link
    # pending_consent - waiting for requester to confirm
    # active - session in progress
    # completed - ended normally
    # expired - link expired
    # declined - requester declined
    # cancelled - requester cancelled

    # Timestamps
    CreatedAt = Column(DateTime, server_default=func.getutcdate(), index=True)
    ExpiresAt = Column(DateTime)  # Link expiration
    HelperJoinedAt = Column(DateTime)
    ConsentGivenAt = Column(DateTime)
    EndedAt = Column(DateTime)

    # Connection info
    ConnectionPassword = Column(String(100))
    Port = Column(Integer)

    # Duration
    DurationSeconds = Column(Integer)

    def __repr__(self):
        return f"<PeerHelpSession(id={self.SessionId}, requester='{self.RequesterUserName}', status='{self.Status}')>"
