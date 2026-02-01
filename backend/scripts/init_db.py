"""
Initialization Script
Creates default admin user and sample policy
"""

import asyncio
import sys
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import User, Policy
from app.core.auth import get_password_hash
import uuid


async def create_admin_user():
    """Create default admin user"""
    async with AsyncSessionLocal() as db:
        # Check if admin already exists
        result = await db.execute(
            select(User).where(User.email == "admin@example.com")
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("✓ Admin user already exists")
            return
        
        # Create admin user
        admin = User(
            user_id=f"usr_{str(uuid.uuid4())[:12]}",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            role="admin",
            active=True
        )
        
        db.add(admin)
        await db.commit()
        
        print("✓ Created admin user")
        print("  Email: admin@example.com")
        print("  Password: admin123")
        print("  ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")


async def create_default_policy():
    """Create default KYC policy"""
    async with AsyncSessionLocal() as db:
        # Check if policy already exists
        result = await db.execute(
            select(Policy).where(Policy.vertical == "kyc").where(Policy.active == True)
        )
        existing_policy = result.scalar_one_or_none()
        
        if existing_policy:
            print("✓ Default policy already exists")
            return
        
        # Create default policy
        policy = Policy(
            policy_id=f"pol_kyc_v1",
            policy_name="KYC Individual Verification",
            version="1.0",
            vertical="kyc",
            active=True,
            created_by="system",
            voting_strategy={
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
            rules=[
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
                    "action": "auto_approve",
                    "sla_hours": None
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
            state_machine={
                "states": [
                    "draft", "submitted", "processing",
                    "under_review", "under_review.identity_check",
                    "under_review.fraud_check", "under_review.compliance_check",
                    "under_review.manual_review",
                    "approved", "rejected", "needs_more_info", "expired"
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
        )
        
        db.add(policy)
        await db.commit()
        
        print("✓ Created default KYC policy")


async def main():
    print("\n🚀 Initializing Decision Platform...\n")
    
    try:
        await create_admin_user()
        await create_default_policy()
        print("\n✅ Initialization complete!\n")
        return 0
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
