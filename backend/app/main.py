"""
Main FastAPI Application
Entry point for the Decision Platform API.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime

from app.models import schemas
from app.services.case_service import CaseService
from app.services.policy_engine import PolicyEngine
from app.services.evidence_service import EvidenceService
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.audit_service import AuditService

# Initialize FastAPI app
app = FastAPI(
    title="Horizontal Decision Platform",
    description="AI-powered document decision platform with human oversight",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_db():
    """Get database session"""
    # In production, yield async database session
    # For now, return None
    return None


def get_case_service(db=Depends(get_db)) -> CaseService:
    """Get case service instance"""
    policy_engine = PolicyEngine(db)
    evidence_service = EvidenceService(db)
    agent_orchestrator = AgentOrchestrator(db)
    audit_service = AuditService(db)
    
    return CaseService(
        db=db,
        policy_engine=policy_engine,
        evidence_service=evidence_service,
        agent_orchestrator=agent_orchestrator,
        audit_service=audit_service
    )


def get_policy_engine(db=Depends(get_db)) -> PolicyEngine:
    """Get policy engine instance"""
    return PolicyEngine(db)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# ============================================================================
# CASE MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/v1/cases", response_model=schemas.Case, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: schemas.CaseCreate,
    case_service: CaseService = Depends(get_case_service)
):
    """
    Create a new case in draft state.
    
    The case will be created with the active policy for the specified vertical.
    Documents can be uploaded after case creation.
    """
    # Create actor (in production, extract from JWT token)
    actor = schemas.Actor(
        type=schemas.ActorType.API,
        user_id="api_user"
    )
    
    try:
        case = await case_service.create_case(case_data, actor)
        return case
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/v1/cases/{case_id}", response_model=schemas.CaseWithRecommendation)
async def get_case(
    case_id: str,
    case_service: CaseService = Depends(get_case_service)
):
    """
    Get case details with all related data.
    
    Returns:
    - Case metadata
    - All uploaded documents
    - Extracted evidence
    - Agent recommendations (if available)
    - Ensemble decision (if available)
    """
    try:
        case_with_details = await case_service.get_case_with_details(case_id)
        return case_with_details
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )


@app.post("/v1/cases/{case_id}/submit", response_model=schemas.Case)
async def submit_case(
    case_id: str,
    case_service: CaseService = Depends(get_case_service)
):
    """
    Submit a case for processing.
    
    This triggers:
    1. Evidence extraction from documents
    2. Multi-agent analysis
    3. Ensemble decision synthesis
    4. Policy rule evaluation
    5. Auto-decision or routing to human review
    """
    actor = schemas.Actor(
        type=schemas.ActorType.API,
        user_id="api_user"
    )
    
    try:
        case = await case_service.submit_case(case_id, actor)
        return case
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/v1/cases/{case_id}/review", response_model=schemas.Case)
async def review_case(
    case_id: str,
    decision: schemas.ReviewDecision,
    case_service: CaseService = Depends(get_case_service)
):
    """
    Submit a human review decision for a case.
    
    Requires:
    - Action (approve/reject/request_more_info)
    - Reasoning (free-text + structured checks)
    
    The decision will be logged in the audit trail with:
    - Reviewer identity
    - Timestamp
    - Evidence snapshot
    - Agent recommendation comparison
    """
    # In production, extract reviewer from JWT
    reviewer = schemas.Actor(
        type=schemas.ActorType.HUMAN,
        user_id="reviewer_123",
        role="kyc_analyst"
    )
    
    try:
        case = await case_service.review_case(case_id, decision, reviewer)
        return case
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/v1/cases/{case_id}/history", response_model=List[schemas.AuditEvent])
async def get_case_history(
    case_id: str,
    case_service: CaseService = Depends(get_case_service)
):
    """
    Get complete audit trail for a case.
    
    Returns all events in chronological order:
    - State transitions
    - Actor information
    - Reasoning
    - Evidence snapshots
    """
    audit_service = AuditService(None)
    history = await audit_service.get_case_history(case_id)
    return history


# ============================================================================
# QUEUE MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/v1/queues/{role}", response_model=List[schemas.Case])
async def get_queue(
    role: str,
    limit: int = 50,
    case_service: CaseService = Depends(get_case_service)
):
    """
    Get cases in queue for a specific role.
    
    Returns cases assigned to the role, ordered by:
    1. Priority (urgent > high > normal > low)
    2. SLA deadline (closest first)
    3. Created date (oldest first)
    """
    # In production, query queue_assignments table
    return []


@app.post("/v1/queues/{role}/claim", response_model=schemas.QueueAssignment)
async def claim_case(
    role: str,
    case_id: str,
    case_service: CaseService = Depends(get_case_service)
):
    """
    Claim a case from the queue for review.
    
    Assigns the case to the current user and removes it from
    the general queue (but keeps it in the user's personal queue).
    """
    # In production, extract user from JWT
    # Update queue_assignment: set assigned_to_user and claimed_at
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Queue claiming not yet implemented"
    )


@app.get("/v1/queues/stats", response_model=List[schemas.QueueStats])
async def get_queue_stats():
    """
    Get statistics for all queues.
    
    Returns:
    - Total cases per queue
    - Claimed vs unclaimed
    - SLA breaches
    - Average wait time
    """
    # In production, query v_queue_dashboard view
    return []


# ============================================================================
# POLICY MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/v1/policies", response_model=List[schemas.Policy])
async def list_policies(
    vertical: Optional[str] = None,
    active_only: bool = False,
    policy_engine: PolicyEngine = Depends(get_policy_engine)
):
    """
    List all policies.
    
    Filters:
    - vertical: Filter by business vertical
    - active_only: Only return active policies
    """
    # In production, query policies table
    return []


@app.get("/v1/policies/{policy_id}", response_model=schemas.Policy)
async def get_policy(
    policy_id: str,
    policy_engine: PolicyEngine = Depends(get_policy_engine)
):
    """Get policy details by ID"""
    try:
        policy = await policy_engine.get_policy(policy_id)
        return policy
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy not found: {policy_id}"
        )


@app.post("/v1/policies/{policy_id}/simulate", response_model=schemas.PolicySimulation)
async def simulate_policy(
    policy_id: str,
    case_id: str,
    policy_engine: PolicyEngine = Depends(get_policy_engine)
):
    """
    Simulate what would happen if a different policy was applied to a case.
    
    Useful for:
    - Testing new policies before activation
    - Compliance audits ("what if we had different rules?")
    - Policy optimization
    """
    try:
        simulation = await policy_engine.simulate_policy(case_id, policy_id)
        return simulation
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/v1/analytics/agent-accuracy", response_model=List[schemas.AgentAccuracy])
async def get_agent_accuracy():
    """
    Get agent accuracy metrics.
    
    Shows how often each agent's recommendation matches
    the final human decision.
    """
    # In production, query v_agent_accuracy view
    return []


@app.get("/v1/analytics/automation-rate", response_model=List[schemas.AutomationRate])
async def get_automation_rate(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get automation rate over time.
    
    Shows percentage of cases that were auto-decided vs
    requiring human review.
    """
    # In production, query case_metrics table
    return []


@app.get("/v1/analytics/case-volume", response_model=List[schemas.CaseVolumeMetrics])
async def get_case_volume(
    vertical: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get case volume metrics.
    
    Shows:
    - Total cases
    - Auto-approved
    - Auto-rejected
    - Manual review
    - SLA breaches
    """
    # In production, query case_metrics table
    return []


# ============================================================================
# DOCUMENT UPLOAD (Simplified)
# ============================================================================

@app.post("/v1/cases/{case_id}/documents")
async def upload_document(
    case_id: str,
    # In production: file: UploadFile = File(...)
):
    """
    Upload a document to a case.
    
    Steps:
    1. Upload file to S3
    2. Create document record
    3. Trigger OCR processing (async)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document upload not yet implemented. Use S3 directly for V1."
    )


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Decision Platform API starting...")
    print("📊 Version: 1.0.0")
    print("🔧 Environment: development")
    # In production:
    # - Initialize database connection pool
    # - Connect to Redis
    # - Initialize S3 client
    # - Start background workers


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 Decision Platform API shutting down...")
    # In production:
    # - Close database connections
    # - Close Redis connections
    # - Cleanup resources


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Only for development
    )
