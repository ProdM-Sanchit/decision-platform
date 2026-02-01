"""
Core domain models for the Decision Platform.
These are Pydantic models used for API validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, EmailStr, validator


# ============================================================================
# ENUMS
# ============================================================================

class CaseStatus(str, Enum):
    """Valid case statuses"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    UNDER_REVIEW = "under_review"
    UNDER_REVIEW_IDENTITY = "under_review.identity_check"
    UNDER_REVIEW_FRAUD = "under_review.fraud_check"
    UNDER_REVIEW_COMPLIANCE = "under_review.compliance_check"
    UNDER_REVIEW_MANUAL = "under_review.manual_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MORE_INFO = "needs_more_info"
    EXPIRED = "expired"


class CasePriority(str, Enum):
    """Case priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ActionType(str, Enum):
    """Possible recommendation actions"""
    APPROVE = "approve"
    REJECT = "reject"
    MANUAL_REVIEW = "manual_review"
    ESCALATE = "escalate"
    REQUEST_MORE_INFO = "request_more_info"


class ActorType(str, Enum):
    """Types of actors in the system"""
    SYSTEM = "system"
    HUMAN = "human"
    API = "api"


class OCRStatus(str, Enum):
    """OCR processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# CASE MODELS
# ============================================================================

class CaseMetadata(BaseModel):
    """Additional metadata for a case"""
    source: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class CaseBase(BaseModel):
    """Base case model"""
    vertical: str
    priority: CasePriority = CasePriority.NORMAL
    customer_id: Optional[str] = None
    metadata: CaseMetadata = Field(default_factory=CaseMetadata)


class CaseCreate(CaseBase):
    """Model for creating a new case"""
    pass


class Case(CaseBase):
    """Full case model"""
    case_id: str
    status: CaseStatus
    policy_version: str
    created_at: datetime
    updated_at: datetime
    sla_deadline: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# DOCUMENT MODELS
# ============================================================================

class DocumentMetadata(BaseModel):
    """Document metadata"""
    page_count: Optional[int] = None
    language: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class DocumentBase(BaseModel):
    """Base document model"""
    document_type: str
    document_subtype: Optional[str] = None
    mime_type: str
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)


class DocumentCreate(DocumentBase):
    """Model for uploading a document"""
    file_path: str
    file_size_bytes: int


class Document(DocumentBase):
    """Full document model"""
    document_id: str
    case_id: str
    file_path: str
    file_size_bytes: int
    uploaded_at: datetime
    ocr_status: OCRStatus
    
    class Config:
        from_attributes = True


# ============================================================================
# EVIDENCE MODELS
# ============================================================================

class EvidenceSource(BaseModel):
    """Source of evidence data"""
    type: Literal["ocr", "api", "manual", "calculated"]
    provider: Optional[str] = None
    document_id: Optional[str] = None
    page: Optional[int] = None
    confidence: Optional[float] = None


class IdentityEvidence(BaseModel):
    """Identity verification evidence"""
    verified: bool
    confidence: float
    extracted_fields: Dict[str, Any]
    sources: List[EvidenceSource]
    validation_checks: Dict[str, Any]


class AddressEvidence(BaseModel):
    """Address verification evidence"""
    verified: bool
    confidence: float
    extracted_data: Dict[str, str]
    sources: List[EvidenceSource]
    validation_attempts: List[Dict[str, Any]]


class ComplianceEvidence(BaseModel):
    """Compliance screening evidence"""
    sanctions_screening: Dict[str, Any]
    pep_screening: Optional[Dict[str, Any]] = None
    adverse_media: Optional[Dict[str, Any]] = None


class RiskAssessment(BaseModel):
    """Risk assessment evidence"""
    risk_score: int = Field(ge=0, le=100)
    risk_flags: List[str]
    risk_factors: Dict[str, Any]


class EvidenceData(BaseModel):
    """Container for all evidence types"""
    identity: Optional[IdentityEvidence] = None
    address: Optional[AddressEvidence] = None
    compliance: Optional[ComplianceEvidence] = None
    risk_assessment: Optional[RiskAssessment] = None
    custom: Dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    """Full evidence model"""
    evidence_id: str
    case_id: str
    evidence_type: str
    version: int
    created_at: datetime
    data: Dict[str, Any]  # Flexible JSONB storage
    
    class Config:
        from_attributes = True


# ============================================================================
# AGENT MODELS
# ============================================================================

class ConfidenceBreakdown(BaseModel):
    """Detailed confidence scores"""
    overall: float = Field(ge=0, le=1)
    components: Dict[str, float] = Field(default_factory=dict)


class AgentRecommendationData(BaseModel):
    """Agent recommendation details"""
    action: ActionType
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    risk_score: Optional[int] = Field(None, ge=0, le=100)
    risk_flags: List[str] = Field(default_factory=list)
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    required_actions: List[str] = Field(default_factory=list)


class AgentRecommendation(BaseModel):
    """Full agent recommendation model"""
    recommendation_id: str
    case_id: str
    agent_name: str
    agent_version: str
    timestamp: datetime
    recommendation: AgentRecommendationData
    processing_time_ms: Optional[int] = None
    
    class Config:
        from_attributes = True


class VotingDetails(BaseModel):
    """Details about ensemble voting"""
    approve_votes: int = 0
    reject_votes: int = 0
    manual_review_votes: int = 0
    escalate_votes: int = 0
    weighted_confidence: float
    consensus_level: str  # "unanimous", "majority", "divided"


class EnsembleRecommendation(BaseModel):
    """Final ensemble recommendation"""
    action: ActionType
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    risk_score: int = Field(ge=0, le=100)
    risk_flags: List[str]
    voting_details: VotingDetails


class AgentVote(BaseModel):
    """Individual agent vote in ensemble"""
    agent: str
    action: ActionType
    confidence: float
    weight: float


class EnsembleDecision(BaseModel):
    """Full ensemble decision model"""
    ensemble_id: str
    case_id: str
    timestamp: datetime
    voting_strategy: str
    agent_recommendations: List[AgentVote]
    final_recommendation: EnsembleRecommendation
    
    class Config:
        from_attributes = True


# ============================================================================
# POLICY MODELS
# ============================================================================

class VotingStrategyConfig(BaseModel):
    """Configuration for voting strategy"""
    type: Literal["weighted", "conservative", "risk_weighted"]
    config: Dict[str, Any]


class PolicyRule(BaseModel):
    """Individual policy rule"""
    priority: int
    name: str
    condition: str  # Expression DSL
    action: ActionType
    assignee_role: Optional[str] = None
    sla_hours: Optional[int] = None
    mandatory_reasoning: bool = False


class StateMachine(BaseModel):
    """State machine configuration"""
    states: List[str]
    transitions: Dict[str, Dict[str, List[str]]]
    terminal_states: List[str]


class Policy(BaseModel):
    """Full policy model"""
    policy_id: str
    policy_name: str
    version: str
    vertical: str
    active: bool
    created_at: datetime
    created_by: str
    voting_strategy: VotingStrategyConfig
    rules: List[PolicyRule]
    state_machine: StateMachine
    
    class Config:
        from_attributes = True


# ============================================================================
# AUDIT MODELS
# ============================================================================

class Actor(BaseModel):
    """Actor who performed an action"""
    type: ActorType
    user_id: Optional[str] = None
    role: Optional[str] = None
    ip_address: Optional[str] = None


class StateTransition(BaseModel):
    """State transition details"""
    from_state: CaseStatus
    to_state: CaseStatus


class StructuredReasoning(BaseModel):
    """Structured reasoning fields"""
    identity_verified: Optional[bool] = None
    address_verified: Optional[bool] = None
    sanctions_clear: Optional[bool] = None
    risk_acceptable: Optional[bool] = None
    custom_checks: Dict[str, bool] = Field(default_factory=dict)


class Reasoning(BaseModel):
    """Human decision reasoning"""
    decision: ActionType
    rationale: str = Field(min_length=50)
    structured_checks: Optional[StructuredReasoning] = None
    reviewer_notes: Optional[str] = None


class AuditEvent(BaseModel):
    """Full audit event model"""
    event_id: str
    case_id: str
    timestamp: datetime
    event_type: str
    actor: Actor
    transition: Optional[StateTransition] = None
    reasoning: Optional[Reasoning] = None
    evidence_snapshot: Optional[Dict[str, Any]] = None
    agent_recommendation: Optional[Dict[str, Any]] = None
    policy_version: Optional[str] = None
    policy_rule_matched: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


# ============================================================================
# QUEUE MODELS
# ============================================================================

class QueueAssignment(BaseModel):
    """Queue assignment model"""
    assignment_id: str
    case_id: str
    queue: str
    assigned_role: str
    assigned_to_user: Optional[str] = None
    claimed_at: Optional[datetime] = None
    sla_deadline: Optional[datetime] = None
    priority: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class QueueStats(BaseModel):
    """Queue statistics"""
    queue: str
    assigned_role: str
    total_cases: int
    claimed_cases: int
    unclaimed_cases: int
    sla_breached: int
    avg_wait_time_seconds: float


# ============================================================================
# USER MODELS
# ============================================================================

class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    full_name: Optional[str] = None
    role: str


class UserCreate(UserBase):
    """Model for creating a user"""
    password: str = Field(min_length=8)


class User(UserBase):
    """Full user model"""
    user_id: str
    active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class ReviewDecision(BaseModel):
    """Review decision submission"""
    action: ActionType
    reasoning: Reasoning


class CaseWithRecommendation(BaseModel):
    """Case with ensemble recommendation"""
    case: Case
    ensemble: Optional[EnsembleDecision] = None
    documents: List[Document] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)


class PolicySimulation(BaseModel):
    """Policy simulation result"""
    case_id: str
    original_decision: ActionType
    simulated_decision: ActionType
    policy_diff: Dict[str, Any]
    rule_matched: str


# ============================================================================
# ANALYTICS MODELS
# ============================================================================

class AgentAccuracy(BaseModel):
    """Agent accuracy metrics"""
    agent_name: str
    total_recommendations: int
    agreements: int
    accuracy_pct: float
    avg_confidence: float


class AutomationRate(BaseModel):
    """Automation rate metrics"""
    date: datetime
    total_cases: int
    auto_decided: int
    automation_rate_pct: float


class CaseVolumeMetrics(BaseModel):
    """Case volume metrics"""
    date: datetime
    vertical: str
    total_cases: int
    auto_approved: int
    auto_rejected: int
    manual_review: int
    avg_processing_time_seconds: int
    sla_breaches: int
