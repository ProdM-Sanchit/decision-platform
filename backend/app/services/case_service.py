"""
Case Management Service - Production Implementation
Handles case lifecycle, state transitions, and orchestration.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

from app.models import schemas
from app.models.schemas import CaseStatus, CasePriority, ActorType
from app.db import models as db_models
from app.services.policy_engine import PolicyEngine
from app.services.evidence_service import EvidenceService
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.audit_service import AuditService


class CaseService:
    """Service for managing cases"""
    
    def __init__(
        self,
        db: AsyncSession,
        policy_engine: PolicyEngine,
        evidence_service: EvidenceService,
        agent_orchestrator: AgentOrchestrator,
        audit_service: AuditService
    ):
        self.db = db
        self.policy_engine = policy_engine
        self.evidence_service = evidence_service
        self.agent_orchestrator = agent_orchestrator
        self.audit_service = audit_service
    
    async def create_case(
        self,
        case_data: schemas.CaseCreate,
        actor: schemas.Actor
    ) -> schemas.Case:
        """Create a new case in draft state"""
        # Get active policy for vertical
        policy = await self.policy_engine.get_active_policy(case_data.vertical)
        
        # Generate case ID
        case_id = f"case_{str(uuid.uuid4())[:12]}"
        
        # Create database model
        db_case = db_models.Case(
            case_id=case_id,
            vertical=case_data.vertical,
            status=CaseStatus.DRAFT.value,
            priority=case_data.priority.value,
            policy_version=policy.policy_id,
            customer_id=case_data.customer_id,
            metadata=case_data.metadata.dict() if case_data.metadata else {}
        )
        
        self.db.add(db_case)
        await self.db.flush()
        
        # Create audit event
        await self.audit_service.log_event(
            case_id=case_id,
            event_type="case.created",
            actor=actor,
            metadata={"vertical": case_data.vertical}
        )
        
        await self.db.commit()
        
        return self._db_case_to_schema(db_case)
    
    async def submit_case(
        self,
        case_id: str,
        actor: schemas.Actor
    ) -> schemas.Case:
        """Submit a case for processing"""
        case = await self.get_case(case_id)
        
        # Validate transition
        await self._validate_transition(
            case=case,
            to_status=CaseStatus.SUBMITTED,
            actor=actor
        )
        
        # Update case status
        case = await self._transition_case(
            case=case,
            to_status=CaseStatus.SUBMITTED,
            actor=actor
        )
        
        # Trigger async processing (in production, this would be a Celery task)
        # For now, process synchronously
        await self.process_case(case_id)
        
        return case
    
    async def process_case(self, case_id: str) -> schemas.Case:
        """Process a submitted case through the full workflow"""
        case = await self.get_case(case_id)
        
        system_actor = schemas.Actor(type=ActorType.SYSTEM)
        case = await self._transition_case(
            case=case,
            to_status=CaseStatus.PROCESSING,
            actor=system_actor
        )
        
        try:
            # Step 1: Extract evidence
            evidence = await self.evidence_service.extract_all_evidence(case_id)
            
            # Step 2: Run all agents
            agent_recommendations = await self.agent_orchestrator.run_all_agents(
                case_id=case_id,
                evidence=evidence
            )
            
            # Step 3: Synthesize ensemble recommendation
            ensemble = await self.agent_orchestrator.synthesize_ensemble(
                case_id=case_id,
                agent_recommendations=agent_recommendations,
                policy_version=case.policy_version
            )
            
            # Step 4: Apply policy rules
            policy = await self.policy_engine.get_policy(case.policy_version)
            rule_match = await self.policy_engine.evaluate_rules(
                policy=policy,
                case=case,
                ensemble=ensemble
            )
            
            # Step 5: Execute decision
            case = await self._execute_decision(
                case=case,
                rule_match=rule_match,
                ensemble=ensemble
            )
            
        except Exception as e:
            # Log error and move to manual review
            await self.audit_service.log_event(
                case_id=case_id,
                event_type="case.processing_failed",
                actor=system_actor,
                metadata={"error": str(e)}
            )
            case = await self._transition_case(
                case=case,
                to_status=CaseStatus.UNDER_REVIEW_MANUAL,
                actor=system_actor
            )
        
        return case
    
    async def review_case(
        self,
        case_id: str,
        decision: schemas.ReviewDecision,
        reviewer: schemas.Actor
    ) -> schemas.Case:
        """Human review of a case"""
        case = await self.get_case(case_id)
        
        # Map action to status
        status_map = {
            schemas.ActionType.APPROVE: CaseStatus.APPROVED,
            schemas.ActionType.REJECT: CaseStatus.REJECTED,
            schemas.ActionType.REQUEST_MORE_INFO: CaseStatus.NEEDS_MORE_INFO,
        }
        
        to_status = status_map.get(decision.action)
        if not to_status:
            raise ValueError(f"Invalid review action: {decision.action}")
        
        # Validate transition
        await self._validate_transition(case, to_status, reviewer)
        
        # Get evidence snapshot for audit
        evidence = await self.evidence_service.get_evidence_snapshot(case_id)
        
        # Get agent recommendation for comparison
        ensemble = await self.agent_orchestrator.get_ensemble(case_id)
        
        # Transition case
        case = await self._transition_case(
            case=case,
            to_status=to_status,
            actor=reviewer,
            reasoning=decision.reasoning,
            evidence_snapshot=evidence,
            agent_recommendation=ensemble.dict() if ensemble else None
        )
        
        return case
    
    async def get_case(self, case_id: str) -> schemas.Case:
        """Get case by ID"""
        result = await self.db.execute(
            select(db_models.Case).where(db_models.Case.case_id == case_id)
        )
        db_case = result.scalar_one_or_none()
        
        if not db_case:
            raise ValueError(f"Case not found: {case_id}")
        
        return self._db_case_to_schema(db_case)
    
    async def get_case_with_details(
        self,
        case_id: str
    ) -> schemas.CaseWithRecommendation:
        """Get case with all related data"""
        case = await self.get_case(case_id)
        documents = await self._get_case_documents(case_id)
        evidence = await self.evidence_service.get_all_evidence(case_id)
        ensemble = await self.agent_orchestrator.get_ensemble(case_id)
        
        return schemas.CaseWithRecommendation(
            case=case,
            documents=documents,
            evidence=evidence,
            ensemble=ensemble
        )
    
    async def list_cases(
        self,
        status: Optional[CaseStatus] = None,
        vertical: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[schemas.Case]:
        """List cases with filters"""
        query = select(db_models.Case)
        
        if status:
            query = query.where(db_models.Case.status == status.value)
        if vertical:
            query = query.where(db_models.Case.vertical == vertical)
        
        query = query.order_by(db_models.Case.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        db_cases = result.scalars().all()
        
        return [self._db_case_to_schema(db_case) for db_case in db_cases]
    
    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================
    
    async def _validate_transition(
        self,
        case: schemas.Case,
        to_status: CaseStatus,
        actor: schemas.Actor
    ) -> None:
        """Validate state transition is allowed"""
        policy = await self.policy_engine.get_policy(case.policy_version)
        
        is_allowed = await self.policy_engine.is_transition_allowed(
            state_machine=policy.state_machine,
            from_state=case.status,
            to_state=to_status,
            actor=actor
        )
        
        if not is_allowed:
            raise ValueError(
                f"Transition {case.status} → {to_status} not allowed for {actor.type}"
            )
    
    async def _transition_case(
        self,
        case: schemas.Case,
        to_status: CaseStatus,
        actor: schemas.Actor,
        reasoning: Optional[schemas.Reasoning] = None,
        evidence_snapshot: Optional[dict] = None,
        agent_recommendation: Optional[dict] = None
    ) -> schemas.Case:
        """Execute state transition with audit logging"""
        from_status = case.status
        
        # Create audit event BEFORE changing state
        await self.audit_service.log_event(
            case_id=case.case_id,
            event_type="state_transition",
            actor=actor,
            transition=schemas.StateTransition(
                from_state=from_status,
                to_state=to_status
            ),
            reasoning=reasoning,
            evidence_snapshot=evidence_snapshot,
            agent_recommendation=agent_recommendation,
            policy_version=case.policy_version
        )
        
        # Update case in database
        result = await self.db.execute(
            select(db_models.Case).where(db_models.Case.case_id == case.case_id)
        )
        db_case = result.scalar_one()
        
        db_case.status = to_status.value
        db_case.updated_at = datetime.utcnow()
        
        # If moving to terminal state, clear SLA
        if to_status in [CaseStatus.APPROVED, CaseStatus.REJECTED, CaseStatus.EXPIRED]:
            db_case.sla_deadline = None
        
        await self.db.commit()
        await self.db.refresh(db_case)
        
        return self._db_case_to_schema(db_case)
    
    async def _execute_decision(
        self,
        case: schemas.Case,
        rule_match: "RuleMatch",
        ensemble: schemas.EnsembleDecision
    ) -> schemas.Case:
        """Execute the decision based on policy rule match"""
        system_actor = schemas.Actor(type=ActorType.SYSTEM)
        
        if rule_match.action == schemas.ActionType.APPROVE:
            case = await self._transition_case(
                case=case,
                to_status=CaseStatus.APPROVED,
                actor=system_actor,
                agent_recommendation=ensemble.dict()
            )
            
        elif rule_match.action == schemas.ActionType.REJECT:
            case = await self._transition_case(
                case=case,
                to_status=CaseStatus.REJECTED,
                actor=system_actor,
                agent_recommendation=ensemble.dict()
            )
            
        elif rule_match.action in [
            schemas.ActionType.MANUAL_REVIEW,
            schemas.ActionType.ESCALATE
        ]:
            case = await self._transition_case(
                case=case,
                to_status=CaseStatus.UNDER_REVIEW_MANUAL,
                actor=system_actor,
                agent_recommendation=ensemble.dict()
            )
            
            # Create queue assignment
            await self._create_queue_assignment(case, rule_match)
        
        return case
    
    async def _create_queue_assignment(
        self,
        case: schemas.Case,
        rule_match: "RuleMatch"
    ) -> None:
        """Create queue assignment for human review"""
        sla_deadline = None
        if rule_match.sla_hours:
            sla_deadline = datetime.utcnow() + timedelta(hours=rule_match.sla_hours)
        
        db_assignment = db_models.QueueAssignment(
            assignment_id=f"asn_{str(uuid.uuid4())[:12]}",
            case_id=case.case_id,
            queue=f"queue_{rule_match.assignee_role}",
            assigned_role=rule_match.assignee_role,
            sla_deadline=sla_deadline,
            priority=self._calculate_priority(case)
        )
        
        self.db.add(db_assignment)
        await self.db.flush()
    
    def _calculate_priority(self, case: schemas.Case) -> int:
        """Calculate numeric priority for queue ordering"""
        priority_map = {
            CasePriority.URGENT: 100,
            CasePriority.HIGH: 75,
            CasePriority.NORMAL: 50,
            CasePriority.LOW: 25
        }
        return priority_map.get(case.priority, 50)
    
    async def _get_case_documents(self, case_id: str) -> List[schemas.Document]:
        """Get all documents for a case"""
        result = await self.db.execute(
            select(db_models.Document).where(db_models.Document.case_id == case_id)
        )
        db_documents = result.scalars().all()
        
        return [
            schemas.Document(
                document_id=doc.document_id,
                case_id=doc.case_id,
                document_type=doc.document_type,
                document_subtype=doc.document_subtype,
                file_path=doc.file_path,
                file_size_bytes=doc.file_size_bytes,
                mime_type=doc.mime_type,
                uploaded_at=doc.uploaded_at,
                ocr_status=schemas.OCRStatus(doc.ocr_status),
                metadata=doc.metadata or {}
            )
            for doc in db_documents
        ]
    
    def _db_case_to_schema(self, db_case: db_models.Case) -> schemas.Case:
        """Convert database model to Pydantic schema"""
        return schemas.Case(
            case_id=db_case.case_id,
            vertical=db_case.vertical,
            status=CaseStatus(db_case.status),
            priority=CasePriority(db_case.priority),
            policy_version=db_case.policy_version,
            customer_id=db_case.customer_id,
            created_at=db_case.created_at,
            updated_at=db_case.updated_at,
            sla_deadline=db_case.sla_deadline,
            metadata=schemas.CaseMetadata(**db_case.metadata) if db_case.metadata else schemas.CaseMetadata()
        )


class RuleMatch:
    """Result of policy rule evaluation"""
    
    def __init__(
        self,
        rule: schemas.PolicyRule,
        action: schemas.ActionType,
        assignee_role: Optional[str] = None,
        sla_hours: Optional[int] = None
    ):
        self.rule = rule
        self.action = action
        self.assignee_role = assignee_role
        self.sla_hours = sla_hours
