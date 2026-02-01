# Horizontal Document Decision Platform - System Architecture

**Version:** 1.0  
**Last Updated:** 2026-02-01  
**Status:** Initial Design

---

## 1. System Overview

### 1.1 Purpose
A workflow-first, agent-assisted decision platform that standardizes how document-driven decisions are made, reviewed, and audited across multiple business verticals (KYC, Insurance, Procurement).

### 1.2 Core Principles
- **AI Recommends, Workflow Decides:** Agents never change system state
- **Audit-First:** Every decision is explainable and replayable
- **Vendor-Agnostic:** All inputs abstracted from specific providers
- **Policy-Driven:** Compliance officers configure rules without code
- **Human-Centric:** Mandatory oversight for uncertain/high-risk decisions

### 1.3 MVP Scope
- **Single Vertical:** KYC (Individual Identity Verification)
- **Target Volume:** 1,000 cases/day
- **Agent SLA:** <30 seconds per recommendation
- **Multi-Agent:** Ensemble voting with configurable strategies

---

## 2. System Architecture

### 2.1 High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                         │
│  REST API • GraphQL • Webhooks • Real-time WS               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Application Service Layer                   │
├─────────────────────────────────────────────────────────────┤
│  Case Management • Policy Engine • Queue Management         │
│  User Management • Analytics • Notifications                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Evidence & Signal Abstraction Layer             │
├─────────────────────────────────────────────────────────────┤
│  Document Processor • OCR Abstraction • API Integrations    │
│  Signal Normalizer • Data Enrichment                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Agent Recommendation Engine                     │
├─────────────────────────────────────────────────────────────┤
│  Identity Agent • Fraud Agent • Compliance Agent            │
│  Risk Agent • Ensemble Orchestrator • LLM Provider          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Decision Gate & Workflow Engine                 │
├─────────────────────────────────────────────────────────────┤
│  State Machine • Rule Evaluator • Transition Controller     │
│  SLA Monitor • Auto-Decision Logic                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           Human-in-the-Loop Orchestration                    │
├─────────────────────────────────────────────────────────────┤
│  Queue Router • Review Interface • Override Handler         │
│  Dual-Approval Logic • Reasoning Validator                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Audit & Decision Replay Layer                   │
├─────────────────────────────────────────────────────────────┤
│  Event Store • Decision Logger • Replay Engine              │
│  Compliance Reports • Policy Simulation                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Persistence Layer                    │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL (Cases, Policies, Audit)                        │
│  S3 (Documents, Binaries)                                   │
│  Redis (Cache, Sessions, Real-time)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Data Models

### 3.1 Core Entities

#### Case
The single source of truth for a decision process.

```json
{
  "case_id": "case_abc123",
  "vertical": "kyc",
  "status": "under_review.fraud_check",
  "priority": "normal",
  "created_at": "2026-02-01T10:00:00Z",
  "updated_at": "2026-02-01T10:05:00Z",
  "sla_deadline": "2026-02-01T14:00:00Z",
  "policy_version": "kyc_v2.3",
  "customer_id": "cust_xyz789",
  "metadata": {
    "source": "api",
    "ip_address": "192.168.1.1",
    "user_agent": "MobileApp/1.2.3"
  }
}
```

#### Evidence
Vendor-agnostic representation of extracted information.

```json
{
  "case_id": "case_abc123",
  "evidence_type": "identity",
  "version": 1,
  "created_at": "2026-02-01T10:01:00Z",
  "data": {
    "verified": true,
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
      "format_valid": true,
      "expiry_check": "valid",
      "checksum_valid": true
    }
  }
}
```

#### Agent Recommendation
Output from a single agent.

```json
{
  "recommendation_id": "rec_def456",
  "case_id": "case_abc123",
  "agent_name": "fraud_agent",
  "agent_version": "v1.2.0",
  "timestamp": "2026-02-01T10:03:00Z",
  "recommendation": {
    "action": "approve",
    "confidence": 0.89,
    "reasoning": "Document authenticity checks passed. No tampering detected. Security features validated. Font consistency verified.",
    "risk_score": 15,
    "risk_flags": [],
    "confidence_breakdown": {
      "document_quality": 0.95,
      "authenticity_score": 0.92,
      "tampering_score": 0.85
    },
    "required_actions": []
  },
  "processing_time_ms": 2340
}
```

#### Ensemble Decision
Synthesized output from all agents.

```json
{
  "ensemble_id": "ens_ghi789",
  "case_id": "case_abc123",
  "timestamp": "2026-02-01T10:04:00Z",
  "voting_strategy": "risk_weighted",
  "agent_recommendations": [
    {"agent": "identity_agent", "action": "approve", "confidence": 0.95, "weight": 1.0},
    {"agent": "fraud_agent", "action": "approve", "confidence": 0.89, "weight": 1.0},
    {"agent": "compliance_agent", "action": "approve", "confidence": 0.98, "weight": 2.0},
    {"agent": "risk_agent", "action": "manual_review", "confidence": 0.72, "weight": 1.5}
  ],
  "final_recommendation": {
    "action": "manual_review",
    "confidence": 0.88,
    "reasoning": "While identity and fraud checks passed with high confidence, risk agent flagged unverified address requiring manual review.",
    "risk_score": 45,
    "risk_flags": ["address_unverified"],
    "voting_details": {
      "approve_votes": 3,
      "manual_review_votes": 1,
      "weighted_confidence": 0.88,
      "consensus_level": "majority"
    }
  }
}
```

#### Policy
Configuration that drives decision logic.

```json
{
  "policy_id": "pol_kyc_v2.3",
  "policy_name": "KYC Individual Verification",
  "version": "2.3",
  "vertical": "kyc",
  "active": true,
  "created_at": "2026-01-15T08:00:00Z",
  "created_by": "compliance_officer_123",
  "voting_strategy": {
    "type": "risk_weighted",
    "config": {
      "high_risk_threshold": 70,
      "high_risk_consensus_required": "unanimous",
      "low_risk_threshold": 30,
      "low_risk_consensus_required": "majority",
      "agent_weights": {
        "compliance_agent": 2.0,
        "identity_agent": 1.0,
        "fraud_agent": 1.0,
        "risk_agent": 1.5
      }
    }
  },
  "rules": [
    {
      "priority": 1,
      "name": "Sanctions Hit - Immediate Escalation",
      "condition": "compliance.sanctions_screening.status == 'hit'",
      "action": "escalate",
      "assignee_role": "senior_compliance_officer",
      "sla_hours": 2,
      "mandatory_reasoning": true
    },
    {
      "priority": 2,
      "name": "High Confidence Auto-Approve",
      "condition": "ensemble.confidence > 0.95 AND ensemble.risk_score < 20 AND ensemble.risk_flags.empty()",
      "action": "auto_approve",
      "sla_hours": null
    },
    {
      "priority": 3,
      "name": "Low Confidence Manual Review",
      "condition": "ensemble.confidence < 0.70",
      "action": "manual_review",
      "assignee_role": "kyc_analyst",
      "sla_hours": 24
    },
    {
      "priority": 99,
      "name": "Default Manual Review",
      "condition": "*",
      "action": "manual_review",
      "assignee_role": "kyc_analyst",
      "sla_hours": 24
    }
  ],
  "state_machine": {
    "states": [
      "draft",
      "submitted",
      "processing",
      "under_review",
      "under_review.identity_check",
      "under_review.fraud_check",
      "under_review.compliance_check",
      "under_review.manual_review",
      "approved",
      "rejected",
      "needs_more_info",
      "expired"
    ],
    "transitions": {
      "draft → submitted": {"allowed_actors": ["customer", "api"]},
      "submitted → processing": {"allowed_actors": ["system"]},
      "processing → under_review.*": {"allowed_actors": ["system", "workflow_engine"]},
      "under_review.* → approved": {"allowed_actors": ["workflow_engine", "reviewer"]},
      "under_review.* → rejected": {"allowed_actors": ["workflow_engine", "reviewer"]},
      "under_review.* → needs_more_info": {"allowed_actors": ["reviewer"]},
      "needs_more_info → submitted": {"allowed_actors": ["customer"]},
      "* → expired": {"allowed_actors": ["system"]}
    },
    "terminal_states": ["approved", "rejected", "expired"]
  }
}
```

#### Audit Event
Immutable log of all state changes and decisions.

```json
{
  "event_id": "evt_jkl012",
  "case_id": "case_abc123",
  "timestamp": "2026-02-01T10:10:00Z",
  "event_type": "state_transition",
  "actor": {
    "type": "human",
    "user_id": "reviewer_456",
    "role": "kyc_analyst",
    "ip_address": "10.0.1.50"
  },
  "transition": {
    "from_state": "under_review.manual_review",
    "to_state": "approved"
  },
  "reasoning": {
    "decision": "approve",
    "rationale": "Identity verified via government ID. Address confirmed through utility bill cross-reference. No sanctions hits. Customer history clean.",
    "structured_checks": {
      "identity_verified": true,
      "address_verified": true,
      "sanctions_clear": true,
      "risk_acceptable": true
    },
    "reviewer_notes": "Called customer to confirm current address. Matches utility bill from last month."
  },
  "evidence_snapshot": {
    "identity": {...},
    "address": {...},
    "compliance": {...}
  },
  "agent_recommendation": {
    "ensemble_id": "ens_ghi789",
    "action": "manual_review",
    "confidence": 0.88
  },
  "policy_version": "kyc_v2.3",
  "policy_rule_matched": "Default Manual Review",
  "metadata": {
    "session_id": "sess_xyz",
    "review_duration_seconds": 180
  }
}
```

---

## 4. Component Specifications

### 4.1 Evidence & Signal Abstraction Layer

**Purpose:** Normalize all inputs into vendor-agnostic evidence objects.

**Responsibilities:**
- Document ingestion (upload, API, email)
- OCR orchestration (Textract, Document AI, Tesseract)
- Data extraction and normalization
- API integration (sanctions, credit, address validation)
- Signal versioning and timestamping

**Key Interfaces:**

```python
class EvidenceExtractor(ABC):
    @abstractmethod
    async def extract(self, document: Document) -> Evidence:
        """Extract evidence from document"""
        pass

class OCRProvider(ABC):
    @abstractmethod
    async def extract_text(self, document: Document) -> OCRResult:
        """Extract text from document"""
        pass

class SignalNormalizer:
    def normalize(self, raw_data: Dict, schema: Schema) -> Evidence:
        """Normalize extracted data into standard evidence format"""
        pass
```

**Supported Extractors (V1):**
- Government ID (driver's license, passport)
- Utility bills (address verification)
- Bank statements (financial verification)

**Supported OCR Providers:**
- AWS Textract (wrapper)
- Google Document AI (wrapper)
- Azure Form Recognizer (wrapper)
- Tesseract (fallback)

---

### 4.2 Agent Recommendation Engine

**Purpose:** Multi-agent analysis with ensemble voting.

**Agent Types:**

1. **Identity Agent**
   - Validates identity data completeness
   - Checks ID expiry dates
   - Validates format (e.g., SSN format, ID number patterns)
   - Cross-references data consistency across documents

2. **Fraud Agent**
   - Document authenticity checks
   - Tampering detection
   - Pattern matching against known fraud signatures
   - Image quality assessment

3. **Compliance Agent**
   - Sanctions screening (OFAC, UN, EU)
   - PEP (Politically Exposed Person) checks
   - Adverse media screening
   - Regulatory requirement validation

4. **Risk Agent**
   - Risk score calculation (0-100)
   - Country risk assessment
   - Data quality scoring
   - Historical pattern analysis

**Voting Strategies:**

```python
class VotingStrategy(ABC):
    @abstractmethod
    def synthesize(
        self, 
        recommendations: List[AgentRecommendation],
        case_context: CaseContext
    ) -> EnsembleDecision:
        pass

class WeightedVoting(VotingStrategy):
    """Weighted average of agent recommendations"""
    pass

class ConservativeVoting(VotingStrategy):
    """Most restrictive recommendation wins"""
    pass

class RiskWeightedVoting(VotingStrategy):
    """High-risk requires unanimous approval, low-risk uses majority"""
    pass
```

**LLM Integration:**

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate_recommendation(
        self,
        prompt: str,
        evidence: Evidence,
        context: Dict
    ) -> AgentRecommendation:
        pass

# Supported providers
class OpenAIProvider(LLMProvider): pass
class AnthropicProvider(LLMProvider): pass
class CustomModelProvider(LLMProvider): pass
```

---

### 4.3 Decision Gate & Workflow Engine

**Purpose:** Enforce policy-driven state transitions.

**State Machine:**

```
draft 
  → submitted 
  → processing 
  → under_review.[identity_check | fraud_check | compliance_check | manual_review]
  → [approved | rejected | needs_more_info]
  
needs_more_info → submitted (customer resubmits)
* → expired (SLA breach or timeout)
```

**Rule Evaluation Engine:**

```python
class RuleEvaluator:
    def evaluate(
        self,
        policy: Policy,
        case: Case,
        ensemble: EnsembleDecision
    ) -> RuleMatch:
        """
        Evaluate rules in priority order.
        Return first matching rule.
        """
        for rule in sorted(policy.rules, key=lambda r: r.priority):
            if self._condition_matches(rule.condition, case, ensemble):
                return RuleMatch(
                    rule=rule,
                    action=rule.action,
                    assignee_role=rule.assignee_role,
                    sla_hours=rule.sla_hours
                )
        raise NoRuleMatchError()
    
    def _condition_matches(
        self,
        condition: str,
        case: Case,
        ensemble: EnsembleDecision
    ) -> bool:
        """Evaluate condition expression against case data"""
        # Parse condition DSL and evaluate
        pass
```

**Transition Controller:**

```python
class TransitionController:
    async def transition(
        self,
        case: Case,
        to_state: str,
        actor: Actor,
        reasoning: Optional[Reasoning] = None
    ) -> Case:
        """
        Execute state transition with validation.
        Enforces state machine rules and audit logging.
        """
        # Validate transition allowed
        if not self._is_transition_allowed(case.status, to_state, actor):
            raise InvalidTransitionError()
        
        # Create audit event
        event = AuditEvent(
            case_id=case.case_id,
            from_state=case.status,
            to_state=to_state,
            actor=actor,
            reasoning=reasoning,
            timestamp=datetime.utcnow()
        )
        
        # Update case state
        case.status = to_state
        case.updated_at = datetime.utcnow()
        
        # Persist atomically
        async with transaction():
            await self.db.save_case(case)
            await self.db.save_audit_event(event)
        
        # Emit event for downstream systems
        await self.event_bus.publish(event)
        
        return case
```

---

### 4.4 Human-in-the-Loop Orchestration

**Purpose:** Route cases to human reviewers and capture decisions.

**Queue Router:**

```python
class QueueRouter:
    async def route_case(
        self,
        case: Case,
        rule_match: RuleMatch
    ) -> Assignment:
        """
        Route case to appropriate reviewer queue.
        Supports skill-based routing and SLA enforcement.
        """
        if rule_match.assignee_role == "senior_compliance_officer":
            queue = self._get_priority_queue()
        else:
            queue = self._get_standard_queue(rule_match.assignee_role)
        
        assignment = Assignment(
            case_id=case.case_id,
            queue=queue,
            assigned_role=rule_match.assignee_role,
            sla_deadline=self._calculate_sla(case, rule_match.sla_hours),
            priority=self._calculate_priority(case, rule_match)
        )
        
        await self.db.save_assignment(assignment)
        await self.notification_service.notify_queue(queue, assignment)
        
        return assignment
```

**Review Interface Requirements:**

1. **Document Viewer**
   - Side-by-side: original document + extracted data
   - Highlight extraction confidence (color-coded)
   - Zoom, rotate, multi-page support

2. **Agent Reasoning Display**
   - All agent recommendations with confidence scores
   - Ensemble synthesis explanation
   - Risk flags and scores

3. **Evidence Summary**
   - All extracted signals grouped by type
   - Data source attribution
   - Validation status indicators

4. **Decision Form**
   - Action buttons: Approve, Reject, Request More Info, Escalate
   - Mandatory reasoning fields:
     - Free-text explanation (min 50 chars)
     - Structured checkboxes (identity verified, address verified, etc.)
   - Rejection reasons (dropdown + free text)

5. **Case History**
   - Timeline of all events
   - Previous reviewer notes
   - Similar case comparisons

---

### 4.5 Audit & Decision Replay Layer

**Purpose:** Ensure every decision is explainable and replayable.

**Event Store:**

```python
class EventStore:
    async def append(self, event: AuditEvent) -> None:
        """Append event to immutable log"""
        await self.db.insert_audit_event(event)
        await self.search_index.index_event(event)
    
    async def get_case_history(self, case_id: str) -> List[AuditEvent]:
        """Retrieve complete case history"""
        return await self.db.query_events(case_id=case_id)
    
    async def replay(self, case_id: str) -> CaseReplay:
        """Reconstruct case state at any point in time"""
        events = await self.get_case_history(case_id)
        return self._reconstruct_state(events)
```

**Replay Engine:**

```python
class ReplayEngine:
    async def simulate_with_new_policy(
        self,
        case_id: str,
        new_policy_version: str
    ) -> SimulationResult:
        """
        Re-run decision with different policy.
        Shows what would have happened.
        """
        # Get original case evidence snapshot
        original_events = await self.event_store.get_case_history(case_id)
        evidence_snapshot = self._extract_evidence(original_events)
        
        # Re-run agent recommendations (use cached if available)
        ensemble = await self.agent_engine.get_ensemble(case_id)
        
        # Apply new policy
        new_policy = await self.policy_service.get_policy(new_policy_version)
        new_rule_match = self.rule_evaluator.evaluate(
            policy=new_policy,
            case=self._reconstruct_case(original_events),
            ensemble=ensemble
        )
        
        return SimulationResult(
            original_decision=self._get_original_decision(original_events),
            simulated_decision=new_rule_match.action,
            policy_diff=self._compare_policies(original_policy, new_policy),
            rule_matched=new_rule_match.rule.name
        )
```

**Compliance Reports:**

```sql
-- Agent accuracy: % agreement with human decisions
SELECT 
    agent_name,
    COUNT(*) as total_cases,
    SUM(CASE WHEN agent_action = final_human_action THEN 1 ELSE 0 END) as agreements,
    ROUND(100.0 * SUM(CASE WHEN agent_action = final_human_action THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy_pct
FROM agent_recommendations ar
JOIN audit_events ae ON ar.case_id = ae.case_id
WHERE ae.actor.type = 'human' 
  AND ae.to_state IN ('approved', 'rejected')
GROUP BY agent_name;

-- Automation rate: % cases auto-decided
SELECT 
    DATE_TRUNC('day', timestamp) as date,
    COUNT(*) as total_cases,
    SUM(CASE WHEN actor.type = 'system' THEN 1 ELSE 0 END) as auto_decided,
    ROUND(100.0 * SUM(CASE WHEN actor.type = 'system' THEN 1 ELSE 0 END) / COUNT(*), 2) as automation_rate_pct
FROM audit_events
WHERE to_state IN ('approved', 'rejected')
GROUP BY DATE_TRUNC('day', timestamp)
ORDER BY date DESC;
```

---

## 5. API Design

### 5.1 REST API Endpoints

**Case Management:**

```
POST   /v1/cases                    # Create new case
GET    /v1/cases/:id                # Get case details
PATCH  /v1/cases/:id                # Update case metadata
POST   /v1/cases/:id/documents      # Upload document
GET    /v1/cases/:id/evidence       # Get extracted evidence
GET    /v1/cases/:id/recommendations # Get agent recommendations
POST   /v1/cases/:id/transitions    # Execute state transition
GET    /v1/cases/:id/history        # Get audit trail
```

**Review Queue:**

```
GET    /v1/queues/:role             # Get cases in queue
POST   /v1/queues/:role/claim       # Claim case for review
POST   /v1/reviews                  # Submit review decision
GET    /v1/reviews/:id              # Get review details
```

**Policy Management:**

```
GET    /v1/policies                 # List policies
POST   /v1/policies                 # Create policy
GET    /v1/policies/:id             # Get policy details
PUT    /v1/policies/:id             # Update policy
POST   /v1/policies/:id/activate    # Activate policy version
POST   /v1/policies/:id/simulate    # Simulate policy on case
```

**Analytics:**

```
GET    /v1/analytics/agent-accuracy
GET    /v1/analytics/automation-rate
GET    /v1/analytics/sla-performance
GET    /v1/analytics/case-volume
```

### 5.2 GraphQL Schema (Optional for V2)

```graphql
type Case {
  id: ID!
  vertical: String!
  status: CaseStatus!
  priority: Priority!
  createdAt: DateTime!
  updatedAt: DateTime!
  slaDeadline: DateTime
  policyVersion: String!
  customer: Customer!
  documents: [Document!]!
  evidence: [Evidence!]!
  recommendations: [AgentRecommendation!]!
  ensembleDecision: EnsembleDecision
  auditTrail: [AuditEvent!]!
}

type Query {
  case(id: ID!): Case
  cases(filter: CaseFilter, pagination: Pagination): CasePage!
  queue(role: Role!): [Case!]!
  policy(id: ID!): Policy
}

type Mutation {
  createCase(input: CreateCaseInput!): Case!
  uploadDocument(caseId: ID!, file: Upload!): Document!
  submitReview(input: ReviewInput!): Case!
  transitionCase(caseId: ID!, toState: CaseStatus!, reasoning: ReasoningInput): Case!
}
```

### 5.3 Webhooks

**Supported Events:**

```
case.created
case.submitted
case.processing_started
case.agent_recommendations_completed
case.assigned_to_queue
case.claimed_by_reviewer
case.approved
case.rejected
case.needs_more_info
case.sla_breach
case.expired
```

**Webhook Payload:**

```json
{
  "event_id": "evt_webhook_123",
  "event_type": "case.approved",
  "timestamp": "2026-02-01T10:15:00Z",
  "data": {
    "case_id": "case_abc123",
    "customer_id": "cust_xyz789",
    "final_status": "approved",
    "decision_actor": "reviewer_456",
    "policy_version": "kyc_v2.3"
  },
  "signature": "sha256_hmac_signature_here"
}
```

---

## 6. Technology Stack

### 6.1 Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI (async, high-performance)
- **Task Queue:** Celery + Redis
- **Caching:** Redis
- **Search:** Elasticsearch (for audit logs and case search)

### 6.2 Database
- **Primary:** PostgreSQL 15+
  - Cases, policies, audit events, users
  - JSONB for flexible evidence storage
  - Full-text search for reasoning/notes
- **Object Storage:** AWS S3 (or MinIO for local dev)
  - Original documents
  - OCR outputs
  - Evidence snapshots
- **Cache:** Redis 7+
  - Session management
  - Real-time queue counts
  - Agent recommendation caching

### 6.3 Frontend
- **Framework:** Next.js 14+ (React 18+)
- **UI Library:** Tailwind CSS + shadcn/ui
- **State Management:** Zustand or TanStack Query
- **Document Viewer:** PDF.js
- **Charts:** Recharts or Chart.js

### 6.4 AI/ML
- **LLM Providers:** 
  - OpenAI (GPT-4)
  - Anthropic (Claude)
  - Custom model support via API abstraction
- **OCR:**
  - AWS Textract (primary)
  - Google Document AI (fallback)
  - Tesseract (offline/free tier)

### 6.5 Infrastructure
- **Containerization:** Docker + Docker Compose
- **Orchestration:** Kubernetes (AWS EKS) for production
- **CI/CD:** GitHub Actions
- **Monitoring:** Prometheus + Grafana
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana)
- **APM:** Sentry for error tracking

---

## 7. Database Schema

### 7.1 Core Tables

```sql
-- Cases
CREATE TABLE cases (
    case_id VARCHAR(50) PRIMARY KEY,
    vertical VARCHAR(50) NOT NULL,
    status VARCHAR(100) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    sla_deadline TIMESTAMP,
    policy_version VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50),
    metadata JSONB,
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_sla_deadline (sla_deadline)
);

-- Documents
CREATE TABLE documents (
    document_id VARCHAR(50) PRIMARY KEY,
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id),
    document_type VARCHAR(50) NOT NULL,
    document_subtype VARCHAR(50),
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    ocr_status VARCHAR(20),
    metadata JSONB,
    INDEX idx_case_id (case_id)
);

-- Evidence
CREATE TABLE evidence (
    evidence_id VARCHAR(50) PRIMARY KEY,
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id),
    evidence_type VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    data JSONB NOT NULL,
    INDEX idx_case_id (case_id),
    INDEX idx_evidence_type (evidence_type)
);

-- Agent Recommendations
CREATE TABLE agent_recommendations (
    recommendation_id VARCHAR(50) PRIMARY KEY,
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id),
    agent_name VARCHAR(50) NOT NULL,
    agent_version VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    recommendation JSONB NOT NULL,
    processing_time_ms INTEGER,
    INDEX idx_case_id (case_id),
    INDEX idx_agent_name (agent_name)
);

-- Ensemble Decisions
CREATE TABLE ensemble_decisions (
    ensemble_id VARCHAR(50) PRIMARY KEY,
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    voting_strategy VARCHAR(50) NOT NULL,
    agent_recommendations JSONB NOT NULL,
    final_recommendation JSONB NOT NULL,
    INDEX idx_case_id (case_id)
);

-- Policies
CREATE TABLE policies (
    policy_id VARCHAR(50) PRIMARY KEY,
    policy_name VARCHAR(200) NOT NULL,
    version VARCHAR(20) NOT NULL,
    vertical VARCHAR(50) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(50) NOT NULL,
    voting_strategy JSONB NOT NULL,
    rules JSONB NOT NULL,
    state_machine JSONB NOT NULL,
    UNIQUE(vertical, version)
);

-- Audit Events (append-only)
CREATE TABLE audit_events (
    event_id VARCHAR(50) PRIMARY KEY,
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    actor JSONB NOT NULL,
    transition JSONB,
    reasoning JSONB,
    evidence_snapshot JSONB,
    agent_recommendation JSONB,
    policy_version VARCHAR(50),
    policy_rule_matched VARCHAR(200),
    metadata JSONB,
    INDEX idx_case_id (case_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_event_type (event_type)
);

-- Queue Assignments
CREATE TABLE queue_assignments (
    assignment_id VARCHAR(50) PRIMARY KEY,
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id),
    queue VARCHAR(100) NOT NULL,
    assigned_role VARCHAR(50) NOT NULL,
    assigned_to_user VARCHAR(50),
    claimed_at TIMESTAMP,
    sla_deadline TIMESTAMP,
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    INDEX idx_queue (queue),
    INDEX idx_assigned_to_user (assigned_to_user),
    INDEX idx_sla_deadline (sla_deadline)
);

-- Users
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(200),
    role VARCHAR(50) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP,
    metadata JSONB
);
```

---

## 8. Deployment Architecture

### 8.1 Development (Docker Compose)

```yaml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/decision_platform
      - REDIS_URL=redis://redis:6379
      - S3_ENDPOINT=http://minio:9000
  
  worker:
    build: ./backend
    command: celery -A app.worker worker
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/decision_platform
      - REDIS_URL=redis://redis:6379
  
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
  
  db:
    image: postgres:15
    volumes: ["./data/postgres:/var/lib/postgresql/data"]
  
  redis:
    image: redis:7-alpine
  
  minio:
    image: minio/minio
    command: server /data
    ports: ["9000:9000", "9001:9001"]
```

### 8.2 Production (AWS ECS)

```
┌─────────────────────────────────────────────────┐
│              Application Load Balancer           │
│         (SSL termination, WAF protection)        │
└─────────────────────────────────────────────────┘
                      ↓
        ┌─────────────────────────────┐
        │       ECS Cluster           │
        ├─────────────────────────────┤
        │  API Service (Fargate)      │ ← Auto-scaling 2-10 tasks
        │  Worker Service (Fargate)   │ ← Auto-scaling 2-20 tasks
        └─────────────────────────────┘
                      ↓
    ┌─────────────────────────────────────┐
    │    RDS PostgreSQL Multi-AZ          │
    │    ElastiCache Redis Cluster        │
    │    S3 (documents, versioned)        │
    │    CloudWatch (logs, metrics)       │
    └─────────────────────────────────────┘
```

---

## 9. Security & Compliance

### 9.1 Data Protection
- **Encryption at Rest:** All databases, S3 buckets encrypted (AES-256)
- **Encryption in Transit:** TLS 1.3 for all API communication
- **Document Encryption:** Separate encryption keys per customer (KMS)
- **PII Masking:** Sensitive fields masked in logs and non-production environments

### 9.2 Access Control
- **Authentication:** OAuth2 + JWT tokens
- **Authorization:** RBAC with fine-grained permissions
- **API Keys:** Scoped keys for external integrations
- **Audit:** All access logged with user context

### 9.3 Compliance
- **GDPR:** Right to access, deletion, data portability
- **SOC2:** Audit logs, access controls, encryption
- **Data Residency:** Configurable per customer (EU, US, etc.)
- **Retention:** Configurable per vertical (7 years default)

---

## 10. Monitoring & Observability

### 10.1 Metrics
- **System:** CPU, memory, disk, network
- **Application:** Request rate, latency (p50, p95, p99), error rate
- **Business:** 
  - Cases processed per hour
  - Agent accuracy by vertical
  - Automation rate (% auto-decided)
  - SLA compliance (% within deadline)
  - Queue depth and wait times

### 10.2 Alerts
- **Critical:** Database down, API error rate >5%, SLA breach >10%
- **Warning:** High queue depth, slow agent responses, low automation rate
- **Info:** New policy deployed, high case volume

### 10.3 Dashboards
- **Operations:** System health, API performance, error rates
- **Business:** Daily case volume, automation trends, agent performance
- **Compliance:** SLA compliance, policy changes, audit activity

---

## 11. Open Questions & Future Enhancements

### 11.1 V1 Scope Clarifications Needed
- [ ] Exact sanctions screening API provider (WorldCheck, ComplyAdvantage, etc.)
- [ ] Document retention policy (how long to keep originals?)
- [ ] Multi-language support requirements
- [ ] Mobile app for reviewers (iOS/Android native or PWA?)

### 11.2 V2 Roadmap
- [ ] Multi-vertical support (Insurance, Procurement)
- [ ] Advanced analytics (case similarity, fraud networks)
- [ ] Agent training pipeline (learn from human corrections)
- [ ] Batch processing mode (upload CSV of cases)
- [ ] Customer self-service portal (check case status)
- [ ] Integration marketplace (Salesforce, HubSpot, etc.)

---

**End of Architecture Document**
