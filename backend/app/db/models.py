"""
SQLAlchemy ORM Models
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, TIMESTAMP, Text, 
    ForeignKey, CheckConstraint, Index, Float, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Case(Base):
    __tablename__ = "cases"
    
    case_id = Column(String(50), primary_key=True)
    vertical = Column(String(50), nullable=False)
    status = Column(String(100), nullable=False)
    priority = Column(String(20), nullable=False, default='normal')
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    sla_deadline = Column(TIMESTAMP, nullable=True)
    policy_version = Column(String(50), nullable=False)
    customer_id = Column(String(50), nullable=True)
    metadata = Column(JSONB, default={})
    
    # Relationships
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    agent_recommendations = relationship("AgentRecommendation", back_populates="case", cascade="all, delete-orphan")
    ensemble_decision = relationship("EnsembleDecision", back_populates="case", uselist=False, cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="case", cascade="all, delete-orphan")
    queue_assignments = relationship("QueueAssignment", back_populates="case", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')"),
        Index('idx_cases_status', 'status'),
        Index('idx_cases_created_at', 'created_at'),
        Index('idx_cases_customer_id', 'customer_id'),
    )


class Document(Base):
    __tablename__ = "documents"
    
    document_id = Column(String(50), primary_key=True)
    case_id = Column(String(50), ForeignKey('cases.case_id', ondelete='CASCADE'), nullable=False)
    document_type = Column(String(50), nullable=False)
    document_subtype = Column(String(50), nullable=True)
    uploaded_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    ocr_status = Column(String(20), default='pending')
    metadata = Column(JSONB, default={})
    
    # Relationships
    case = relationship("Case", back_populates="documents")
    
    __table_args__ = (
        Index('idx_documents_case_id', 'case_id'),
        CheckConstraint("ocr_status IN ('pending', 'processing', 'completed', 'failed')"),
    )


class Evidence(Base):
    __tablename__ = "evidence"
    
    evidence_id = Column(String(50), primary_key=True)
    case_id = Column(String(50), ForeignKey('cases.case_id', ondelete='CASCADE'), nullable=False)
    evidence_type = Column(String(50), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    data = Column(JSONB, nullable=False)
    
    # Relationships
    case = relationship("Case", back_populates="evidence")
    
    __table_args__ = (
        Index('idx_evidence_case_id', 'case_id'),
        Index('idx_evidence_type', 'evidence_type'),
    )


class AgentRecommendation(Base):
    __tablename__ = "agent_recommendations"
    
    recommendation_id = Column(String(50), primary_key=True)
    case_id = Column(String(50), ForeignKey('cases.case_id', ondelete='CASCADE'), nullable=False)
    agent_name = Column(String(50), nullable=False)
    agent_version = Column(String(20), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    recommendation = Column(JSONB, nullable=False)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    case = relationship("Case", back_populates="agent_recommendations")
    
    __table_args__ = (
        Index('idx_agent_recs_case_id', 'case_id'),
        Index('idx_agent_recs_agent_name', 'agent_name'),
    )


class EnsembleDecision(Base):
    __tablename__ = "ensemble_decisions"
    
    ensemble_id = Column(String(50), primary_key=True)
    case_id = Column(String(50), ForeignKey('cases.case_id', ondelete='CASCADE'), nullable=False, unique=True)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    voting_strategy = Column(String(50), nullable=False)
    agent_recommendations = Column(JSONB, nullable=False)
    final_recommendation = Column(JSONB, nullable=False)
    
    # Relationships
    case = relationship("Case", back_populates="ensemble_decision")
    
    __table_args__ = (
        Index('idx_ensemble_case_id', 'case_id'),
    )


class Policy(Base):
    __tablename__ = "policies"
    
    policy_id = Column(String(50), primary_key=True)
    policy_name = Column(String(200), nullable=False)
    version = Column(String(20), nullable=False)
    vertical = Column(String(50), nullable=False)
    active = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    created_by = Column(String(50), nullable=False)
    voting_strategy = Column(JSONB, nullable=False)
    rules = Column(JSONB, nullable=False)
    state_machine = Column(JSONB, nullable=False)
    
    __table_args__ = (
        Index('idx_policies_vertical', 'vertical'),
        Index('idx_policies_active', 'active'),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    event_id = Column(String(50), primary_key=True)
    case_id = Column(String(50), ForeignKey('cases.case_id', ondelete='CASCADE'), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    event_type = Column(String(50), nullable=False)
    actor = Column(JSONB, nullable=False)
    transition = Column(JSONB, nullable=True)
    reasoning = Column(JSONB, nullable=True)
    evidence_snapshot = Column(JSONB, nullable=True)
    agent_recommendation = Column(JSONB, nullable=True)
    policy_version = Column(String(50), nullable=True)
    policy_rule_matched = Column(String(200), nullable=True)
    metadata = Column(JSONB, default={})
    
    # Relationships
    case = relationship("Case", back_populates="audit_events")
    
    __table_args__ = (
        Index('idx_audit_case_id', 'case_id'),
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_event_type', 'event_type'),
    )


class QueueAssignment(Base):
    __tablename__ = "queue_assignments"
    
    assignment_id = Column(String(50), primary_key=True)
    case_id = Column(String(50), ForeignKey('cases.case_id', ondelete='CASCADE'), nullable=False)
    queue = Column(String(100), nullable=False)
    assigned_role = Column(String(50), nullable=False)
    assigned_to_user = Column(String(50), nullable=True)
    claimed_at = Column(TIMESTAMP, nullable=True)
    sla_deadline = Column(TIMESTAMP, nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    case = relationship("Case", back_populates="queue_assignments")
    
    __table_args__ = (
        Index('idx_queue_assignments_queue', 'queue'),
        Index('idx_queue_assignments_user', 'assigned_to_user'),
    )


class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(50), primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    role = Column(String(50), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    last_login = Column(TIMESTAMP, nullable=True)
    metadata = Column(JSONB, default={})
    
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
    )
