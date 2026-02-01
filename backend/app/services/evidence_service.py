"""
Evidence Service
Handles evidence extraction and management.
"""

from typing import List, Dict, Any, Optional
from app.models import schemas


class EvidenceService:
    """Service for managing evidence"""
    
    def __init__(self, db):
        self.db = db
    
    async def extract_all_evidence(
        self,
        case_id: str
    ) -> List[schemas.Evidence]:
        """
        Extract evidence from all documents for a case.
        
        This orchestrates:
        1. OCR extraction from documents
        2. API calls to external services
        3. Data normalization
        4. Evidence persistence
        """
        # In production, this would:
        # 1. Get all documents for case
        # 2. Run OCR on each document
        # 3. Call external APIs (sanctions, address validation, etc.)
        # 4. Normalize all data into Evidence objects
        # 5. Save to database
        
        # Placeholder - return mock evidence
        return [
            self._create_mock_identity_evidence(case_id),
            self._create_mock_address_evidence(case_id),
            self._create_mock_compliance_evidence(case_id),
            self._create_mock_risk_evidence(case_id)
        ]
    
    async def get_all_evidence(
        self,
        case_id: str
    ) -> List[schemas.Evidence]:
        """Get all evidence for a case"""
        # Query from database
        return []
    
    async def get_evidence_snapshot(
        self,
        case_id: str
    ) -> Dict[str, Any]:
        """Get evidence snapshot for audit trail"""
        evidence = await self.get_all_evidence(case_id)
        snapshot = {}
        for evd in evidence:
            snapshot[evd.evidence_type] = evd.data
        return snapshot
    
    def _create_mock_identity_evidence(self, case_id: str) -> schemas.Evidence:
        """Create mock identity evidence for development"""
        from datetime import datetime
        return schemas.Evidence(
            evidence_id=f"evd_identity_{case_id[:8]}",
            case_id=case_id,
            evidence_type="identity",
            version=1,
            created_at=datetime.utcnow(),
            data={
                "verified": True,
                "confidence": 0.94,
                "extracted_fields": {
                    "full_name": "John Doe",
                    "date_of_birth": "1985-03-15",
                    "id_number": "D1234567",
                    "expiry_date": "2028-03-15",
                    "issuing_country": "US",
                    "issuing_state": "MA"
                },
                "sources": [
                    {
                        "type": "ocr",
                        "provider": "textract",
                        "document_id": "doc_001",
                        "page": 1,
                        "confidence": 0.97
                    }
                ],
                "validation_checks": {
                    "format_valid": True,
                    "expiry_check": "valid",
                    "checksum_valid": True
                }
            }
        )
    
    def _create_mock_address_evidence(self, case_id: str) -> schemas.Evidence:
        """Create mock address evidence"""
        from datetime import datetime
        return schemas.Evidence(
            evidence_id=f"evd_address_{case_id[:8]}",
            case_id=case_id,
            evidence_type="address",
            version=1,
            created_at=datetime.utcnow(),
            data={
                "verified": False,
                "confidence": 0.67,
                "extracted_data": {
                    "street": "123 Main St",
                    "city": "Boston",
                    "state": "MA",
                    "zip": "02101"
                },
                "sources": [{"type": "ocr", "document_id": "doc_001"}],
                "validation_attempts": [
                    {"service": "usps", "status": "failed"}
                ]
            }
        )
    
    def _create_mock_compliance_evidence(self, case_id: str) -> schemas.Evidence:
        """Create mock compliance evidence"""
        from datetime import datetime
        return schemas.Evidence(
            evidence_id=f"evd_compliance_{case_id[:8]}",
            case_id=case_id,
            evidence_type="compliance",
            version=1,
            created_at=datetime.utcnow(),
            data={
                "sanctions_screening": {
                    "status": "clear",
                    "checked_lists": ["OFAC", "UN", "EU"],
                    "timestamp": datetime.utcnow().isoformat()
                },
                "pep_screening": {
                    "status": "clear"
                }
            }
        )
    
    def _create_mock_risk_evidence(self, case_id: str) -> schemas.Evidence:
        """Create mock risk evidence"""
        from datetime import datetime
        return schemas.Evidence(
            evidence_id=f"evd_risk_{case_id[:8]}",
            case_id=case_id,
            evidence_type="risk_assessment",
            version=1,
            created_at=datetime.utcnow(),
            data={
                "risk_score": 23,
                "risk_flags": ["address_unverified"],
                "risk_factors": {
                    "document_quality": "high",
                    "country_risk": "low",
                    "data_completeness": 0.95
                }
            }
        )


"""
Audit Service
Handles audit logging and decision replay.
"""


class AuditService:
    """Service for audit logging"""
    
    def __init__(self, db):
        self.db = db
    
    async def log_event(
        self,
        case_id: str,
        event_type: str,
        actor: schemas.Actor,
        transition: Optional[schemas.StateTransition] = None,
        reasoning: Optional[schemas.Reasoning] = None,
        evidence_snapshot: Optional[Dict[str, Any]] = None,
        agent_recommendation: Optional[Dict[str, Any]] = None,
        policy_version: Optional[str] = None,
        policy_rule_matched: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> schemas.AuditEvent:
        """
        Log an audit event.
        All state changes MUST flow through this service.
        """
        from datetime import datetime
        
        event = schemas.AuditEvent(
            event_id=f"evt_{self._generate_id()}",
            case_id=case_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            actor=actor,
            transition=transition,
            reasoning=reasoning,
            evidence_snapshot=evidence_snapshot,
            agent_recommendation=agent_recommendation,
            policy_version=policy_version,
            policy_rule_matched=policy_rule_matched,
            metadata=metadata or {}
        )
        
        # Persist to database (append-only)
        await self._save_event(event)
        
        return event
    
    async def get_case_history(
        self,
        case_id: str
    ) -> List[schemas.AuditEvent]:
        """Get complete audit trail for a case"""
        # Query from database
        # SELECT * FROM audit_events WHERE case_id = ? ORDER BY timestamp
        return []
    
    async def replay_case(
        self,
        case_id: str,
        up_to_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Replay case history to reconstruct state at any point.
        Used for compliance audits and debugging.
        """
        events = await self.get_case_history(case_id)
        
        # Reconstruct state by replaying events
        # This is the "event sourcing" pattern
        
        return {
            "case_id": case_id,
            "reconstructed_state": {},
            "event_count": len(events)
        }
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        return str(uuid.uuid4())[:12]
    
    async def _save_event(self, event: schemas.AuditEvent) -> None:
        """Persist event to append-only log"""
        # In production: INSERT INTO audit_events
        pass
