# Horizontal Document Decision Platform

**A workflow-first, agent-assisted decision system for document-driven business processes**

> Version: 1.0.0  
> Status: MVP Development  
> License: Proprietary

---

## 🎯 What Is This?

This is **not** a document processing pipeline. This is **not** an OCR tool with AI features.

This is a **decision governance platform** that standardizes how document-driven decisions are made, reviewed, and audited across business verticals like KYC, Insurance Claims, and Procurement.

### Core Principles

1. **AI Recommends, Workflow Decides** - Agents never directly change system state
2. **Audit-First** - Every decision is explainable and replayable
3. **Vendor-Agnostic** - All inputs abstracted from specific providers
4. **Policy-Driven** - Compliance officers configure rules without code
5. **Human-Centric** - Mandatory oversight for uncertain/high-risk decisions

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│           VERTICAL USE CASES (Business Rules)                │
│        KYC Policies | Insurance Policies | Procurement       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              HORIZONTAL DECISION PLATFORM                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Evidence Abstraction (OCR, APIs → Normalized Data)  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Multi-Agent Analysis (Identity, Fraud, Compliance)  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Workflow Engine (Policy Rules → State Transitions)  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Human Review Queue (SLA, Skill Routing, Override)   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Audit Trail (Immutable Log → Decision Replay)       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│         INPUTS (Documents, APIs, Humans, External Data)      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 8GB RAM minimum (16GB recommended)
- Ports available: 3000, 5432, 6379, 8000, 9000, 9001

### 1. Clone and Start

```bash
git clone <repository-url>
cd decision-platform

# Start core services (API, DB, Redis, MinIO)
docker-compose up -d

# Start with Elasticsearch and Kibana (optional)
docker-compose --profile full up -d
```

### 2. Verify Services

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"2026-02-01T10:00:00","version":"1.0.0"}
```

### 3. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:8000 | N/A |
| **API Docs** | http://localhost:8000/docs | N/A |
| **Frontend** | http://localhost:3000 | N/A |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **Kibana** | http://localhost:5601 | N/A |

---

## 📋 Usage Guide

### Example: KYC Individual Verification

#### 1. Create a Case

```bash
curl -X POST http://localhost:8000/v1/cases \
  -H "Content-Type: application/json" \
  -d '{
    "vertical": "kyc",
    "priority": "normal",
    "customer_id": "cust_12345",
    "metadata": {
      "source": "web_app",
      "ip_address": "192.168.1.1"
    }
  }'

# Response:
{
  "case_id": "case_abc123def456",
  "vertical": "kyc",
  "status": "draft",
  "priority": "normal",
  "policy_version": "pol_kyc_v1",
  "created_at": "2026-02-01T10:00:00",
  ...
}
```

#### 2. Upload Documents

```bash
# Upload driver's license
curl -X POST http://localhost:8000/v1/cases/case_abc123def456/documents \
  -F "file=@drivers_license.pdf" \
  -F "document_type=government_id" \
  -F "document_subtype=drivers_license"
```

#### 3. Submit for Processing

```bash
curl -X POST http://localhost:8000/v1/cases/case_abc123def456/submit

# This triggers:
# 1. OCR extraction
# 2. Multi-agent analysis (4 agents run in parallel)
# 3. Ensemble voting (based on policy strategy)
# 4. Policy rule evaluation
# 5. Auto-decision OR routing to human review queue
```

#### 4. Check Case Status

```bash
curl http://localhost:8000/v1/cases/case_abc123def456

# Response includes:
{
  "case": {...},
  "ensemble": {
    "ensemble_id": "ens_xyz789",
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
      "reasoning": "...",
      "risk_score": 45
    }
  },
  "documents": [...],
  "evidence": [...]
}
```

#### 5. Human Review (if routed to queue)

```bash
# Get cases in my queue
curl http://localhost:8000/v1/queues/kyc_analyst

# Submit review decision
curl -X POST http://localhost:8000/v1/cases/case_abc123def456/review \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "reasoning": {
      "decision": "approve",
      "rationale": "Identity verified via government ID. Address confirmed through utility bill. No sanctions hits.",
      "structured_checks": {
        "identity_verified": true,
        "address_verified": true,
        "sanctions_clear": true,
        "risk_acceptable": true
      },
      "reviewer_notes": "Called customer to confirm current address."
    }
  }'
```

#### 6. View Audit Trail

```bash
curl http://localhost:8000/v1/cases/case_abc123def456/history

# Returns complete audit trail:
[
  {
    "event_id": "evt_001",
    "event_type": "case.created",
    "actor": {"type": "api"},
    "timestamp": "2026-02-01T10:00:00"
  },
  {
    "event_id": "evt_002",
    "event_type": "state_transition",
    "actor": {"type": "system"},
    "transition": {"from_state": "draft", "to_state": "submitted"},
    "timestamp": "2026-02-01T10:01:00"
  },
  ...
]
```

---

## 🧠 Multi-Agent System

### Agents

| Agent | Purpose | Output |
|-------|---------|--------|
| **Identity Agent** | Validates identity data completeness, format, expiry | action, confidence, risk_score |
| **Fraud Agent** | Detects document tampering, fraud patterns | action, confidence, fraud_flags |
| **Compliance Agent** | Sanctions screening, PEP checks, regulatory compliance | action, confidence, compliance_status |
| **Risk Agent** | Calculates overall risk score based on all factors | action, confidence, risk_score |

### Voting Strategies (Configurable per Policy)

#### 1. Weighted Voting
Each agent has a weight. Final decision = weighted average.

```json
{
  "agent_weights": {
    "compliance_agent": 2.0,
    "identity_agent": 1.0,
    "fraud_agent": 1.0,
    "risk_agent": 1.5
  }
}
```

#### 2. Conservative Voting
Most restrictive recommendation wins.
Priority: reject > escalate > manual_review > approve

#### 3. Risk-Weighted Voting (Default for KYC)
- **High risk (>70):** Requires unanimous approval
- **Medium risk (30-70):** Weighted voting
- **Low risk (<30):** Majority vote

---

## 📐 Policy Configuration

Policies are defined in YAML/JSON and control all decision logic.

### Example Policy

```json
{
  "policy_name": "KYC Individual Verification",
  "version": "1.0",
  "vertical": "kyc",
  "voting_strategy": {
    "type": "risk_weighted",
    "config": {...}
  },
  "rules": [
    {
      "priority": 1,
      "name": "Sanctions Hit",
      "condition": "compliance.sanctions_screening.status == 'hit'",
      "action": "escalate",
      "assignee_role": "senior_compliance_officer",
      "sla_hours": 2
    },
    {
      "priority": 2,
      "name": "High Confidence Auto-Approve",
      "condition": "ensemble.confidence > 0.95 AND ensemble.risk_score < 20",
      "action": "auto_approve"
    },
    {
      "priority": 99,
      "name": "Default Manual Review",
      "condition": "*",
      "action": "manual_review",
      "assignee_role": "kyc_analyst",
      "sla_hours": 24
    }
  ]
}
```

### Rule Evaluation

Rules are evaluated in priority order. First matching rule determines the action.

**Condition DSL supports:**
- Property access: `ensemble.confidence > 0.95`
- Comparisons: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Boolean ops: `AND`, `OR`
- Functions: `.contains()`, `.empty()`
- Wildcards: `*` (default rule)

---

## 📊 Analytics & Metrics

### Agent Accuracy

```bash
curl http://localhost:8000/v1/analytics/agent-accuracy

# Shows how often each agent agrees with human decisions
[
  {
    "agent_name": "identity_agent",
    "total_recommendations": 1000,
    "agreements": 920,
    "accuracy_pct": 92.0,
    "avg_confidence": 0.89
  },
  ...
]
```

### Automation Rate

```bash
curl http://localhost:8000/v1/analytics/automation-rate

# Shows % of cases auto-decided vs manual review
[
  {
    "date": "2026-02-01",
    "total_cases": 1000,
    "auto_decided": 650,
    "automation_rate_pct": 65.0
  }
]
```

### Case Volume

```bash
curl http://localhost:8000/v1/analytics/case-volume

# Shows throughput and SLA compliance
[
  {
    "date": "2026-02-01",
    "vertical": "kyc",
    "total_cases": 1000,
    "auto_approved": 600,
    "auto_rejected": 50,
    "manual_review": 350,
    "sla_breaches": 12
  }
]
```

---

## 🔐 Security & Compliance

### Data Protection

- **Encryption at Rest:** All documents encrypted in S3 (AES-256)
- **Encryption in Transit:** TLS 1.3 for all API communication
- **PII Masking:** Sensitive fields masked in logs

### Access Control

- **RBAC:** Role-based access control
- **JWT Authentication:** Token-based API access
- **Audit Logging:** All access logged with user context

### Compliance

- **GDPR:** Right to access, deletion, data portability
- **SOC2:** Audit logs, access controls, encryption
- **Data Residency:** Configurable per customer

---

## 🛠️ Development

### Project Structure

```
decision-platform/
├── backend/
│   ├── app/
│   │   ├── agents/           # Agent implementations
│   │   ├── api/              # API routes
│   │   ├── core/             # Core utilities
│   │   ├── models/           # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   └── main.py           # FastAPI app
│   ├── db/
│   │   └── schema.sql        # Database schema
│   ├── tests/                # Pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Next.js pages
│   │   └── lib/              # Utilities
│   └── package.json
├── docs/
│   └── ARCHITECTURE.md       # Detailed architecture
├── docker-compose.yml
└── README.md
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 📈 Scaling & Performance

### Current Capacity (Single Instance)

- **Throughput:** 1,000 cases/day
- **Agent SLA:** <30 seconds per recommendation
- **API Latency:** <200ms (p95)

### Scaling Strategy

**Horizontal Scaling:**
- API: Add more FastAPI instances behind load balancer
- Workers: Add more Celery workers for parallel processing
- Database: Read replicas for analytics queries

**Vertical Scaling:**
- PostgreSQL: Increase connection pool
- Redis: Increase memory for caching
- Agents: Use GPU for LLM inference

**Production Architecture:**
```
┌─────────────────────────────────────┐
│     Application Load Balancer       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   ECS Cluster (Auto-scaling 2-10)   │
│   - API Service (Fargate)           │
│   - Worker Service (Fargate)        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   RDS PostgreSQL Multi-AZ           │
│   ElastiCache Redis Cluster         │
│   S3 (documents, versioned)         │
└─────────────────────────────────────┘
```

---

## 🤝 Contributing

### Adding a New Agent

1. Create agent class in `backend/app/agents/`
2. Inherit from `BaseAgent`
3. Implement `analyze()` method
4. Register in `AgentOrchestrator`

```python
class CustomAgent(BaseAgent):
    async def analyze(self, evidence):
        # Your logic here
        return schemas.AgentRecommendationData(
            action=ActionType.APPROVE,
            confidence=0.95,
            reasoning="...",
            risk_score=10
        )
```

### Adding a New Vertical

1. Define policies in `backend/db/policies/`
2. Create evidence extractors for vertical-specific documents
3. Update state machine if needed
4. Add frontend components for review interface

---

## 📞 Support

### Documentation
- Architecture: `docs/ARCHITECTURE.md`
- API Reference: http://localhost:8000/docs
- Database Schema: `backend/db/schema.sql`

### Troubleshooting

**API won't start:**
```bash
# Check logs
docker-compose logs api

# Common issues:
# - Database not ready: wait for health check
# - Port conflict: change port in docker-compose.yml
```

**Workers not processing:**
```bash
# Check worker logs
docker-compose logs worker

# Verify Redis connection
docker-compose exec redis redis-cli ping
```

**Database migration errors:**
```bash
# Reset database (DEV ONLY)
docker-compose down -v
docker-compose up -d db
```

---

## 📄 License

Proprietary - All Rights Reserved

---

## 🎉 What's Next?

**Immediate Priorities:**
1. ✅ Core platform MVP
2. ⏳ Frontend review interface
3. ⏳ OCR integration (AWS Textract)
4. ⏳ Sanctions API integration
5. ⏳ Production deployment (AWS ECS)

**Future Enhancements:**
- Multi-vertical support (Insurance, Procurement)
- Advanced analytics dashboard
- Agent training pipeline (learn from corrections)
- Customer self-service portal
- Integration marketplace (Salesforce, HubSpot)

---

**Built with ❤️ for compliance officers who deserve better tools.**
