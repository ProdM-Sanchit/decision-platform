"""
Individual Agent Implementations
"""

from typing import List
from app.agents.base_agent import BaseAgent
from app.models import schemas
from app.models.schemas import ActionType


class IdentityAgent(BaseAgent):
    """
    Identity Agent
    Validates identity data completeness, format, and expiry.
    """
    
    async def analyze(
        self,
        evidence: List[schemas.Evidence]
    ) -> schemas.AgentRecommendationData:
        """Analyze identity evidence"""
        identity_ev = self.get_evidence_by_type(evidence, "identity")
        
        if not identity_ev:
            return schemas.AgentRecommendationData(
                action=ActionType.MANUAL_REVIEW,
                confidence=0.0,
                reasoning="No identity evidence found. Manual review required.",
                risk_score=100,
                risk_flags=["missing_identity"]
            )
        
        # Extract identity data
        verified = self.extract_data_field(identity_ev, "verified", False)
        confidence = self.extract_data_field(identity_ev, "confidence", 0.0)
        extracted = self.extract_data_field(identity_ev, "extracted_fields", {})
        
        # Check required fields
        required_fields = ["full_name", "date_of_birth", "id_number"]
        missing_fields = [f for f in required_fields if f not in extracted]
        
        # Check expiry date
        expiry = extracted.get("expiry_date")
        is_expired = False
        if expiry:
            from datetime import datetime
            try:
                expiry_date = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                is_expired = expiry_date < datetime.now()
            except:
                pass
        
        # Calculate risk score and flags
        risk_score = 0
        risk_flags = []
        
        if missing_fields:
            risk_score += 30
            risk_flags.append("incomplete_identity_data")
        
        if not verified:
            risk_score += 40
            risk_flags.append("identity_not_verified")
        
        if is_expired:
            risk_score += 50
            risk_flags.append("id_expired")
        
        if confidence < 0.7:
            risk_score += 20
            risk_flags.append("low_extraction_confidence")
        
        # Determine action
        if is_expired:
            action = ActionType.REJECT
            reasoning = f"Identity document has expired (expiry: {expiry}). Cannot proceed."
        elif missing_fields:
            action = ActionType.REQUEST_MORE_INFO
            reasoning = f"Missing required identity fields: {', '.join(missing_fields)}. Additional documentation needed."
        elif verified and confidence > 0.9 and not risk_flags:
            action = ActionType.APPROVE
            reasoning = "Identity verified with high confidence. All required fields present and valid."
        elif confidence < 0.6:
            action = ActionType.MANUAL_REVIEW
            reasoning = f"Identity extraction confidence is low ({int(confidence*100)}%). Manual verification recommended."
        else:
            action = ActionType.APPROVE
            reasoning = f"Identity verified. Confidence: {int(confidence*100)}%."
        
        return schemas.AgentRecommendationData(
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            risk_score=min(risk_score, 100),
            risk_flags=risk_flags
        )


class FraudAgent(BaseAgent):
    """
    Fraud Agent
    Detects document tampering and fraud patterns.
    """
    
    async def analyze(
        self,
        evidence: List[schemas.Evidence]
    ) -> schemas.AgentRecommendationData:
        """Analyze for fraud indicators"""
        identity_ev = self.get_evidence_by_type(evidence, "identity")
        
        if not identity_ev:
            return schemas.AgentRecommendationData(
                action=ActionType.MANUAL_REVIEW,
                confidence=0.5,
                reasoning="No identity evidence available for fraud analysis.",
                risk_score=50,
                risk_flags=["no_fraud_analysis"]
            )
        
        # Extract validation checks
        validation = self.extract_data_field(identity_ev, "validation_checks", {})
        
        format_valid = validation.get("format_valid", True)
        checksum_valid = validation.get("checksum_valid", True)
        
        # Simulated fraud indicators (in production, use ML model or API)
        # This would check for:
        # - Font inconsistencies
        # - Image manipulation artifacts
        # - Pattern matching against known fraud databases
        # - Metadata anomalies
        
        fraud_indicators = []
        risk_score = 10  # Base risk
        
        if not format_valid:
            fraud_indicators.append("invalid_format")
            risk_score += 30
        
        if not checksum_valid:
            fraud_indicators.append("checksum_mismatch")
            risk_score += 40
        
        # Check image quality (placeholder)
        confidence = self.extract_data_field(identity_ev, "confidence", 0.9)
        if confidence < 0.6:
            fraud_indicators.append("poor_image_quality")
            risk_score += 20
        
        # Determine action
        if len(fraud_indicators) >= 2:
            action = ActionType.ESCALATE
            reasoning = f"Multiple fraud indicators detected: {', '.join(fraud_indicators)}. Escalation to fraud team required."
            final_confidence = 0.3
        elif len(fraud_indicators) == 1:
            action = ActionType.MANUAL_REVIEW
            reasoning = f"Potential fraud indicator: {fraud_indicators[0]}. Manual review recommended."
            final_confidence = 0.6
        else:
            action = ActionType.APPROVE
            reasoning = "No fraud indicators detected. Document appears authentic."
            final_confidence = 0.95
        
        return schemas.AgentRecommendationData(
            action=action,
            confidence=final_confidence,
            reasoning=reasoning,
            risk_score=min(risk_score, 100),
            risk_flags=fraud_indicators
        )


class ComplianceAgent(BaseAgent):
    """
    Compliance Agent
    Performs sanctions screening and regulatory checks.
    """
    
    async def analyze(
        self,
        evidence: List[schemas.Evidence]
    ) -> schemas.AgentRecommendationData:
        """Analyze compliance requirements"""
        compliance_ev = self.get_evidence_by_type(evidence, "compliance")
        
        if not compliance_ev:
            return schemas.AgentRecommendationData(
                action=ActionType.MANUAL_REVIEW,
                confidence=0.0,
                reasoning="No compliance screening performed. Manual review required.",
                risk_score=100,
                risk_flags=["no_compliance_check"]
            )
        
        # Extract compliance data
        sanctions = self.extract_data_field(compliance_ev, "sanctions_screening", {})
        pep = self.extract_data_field(compliance_ev, "pep_screening", {})
        
        sanctions_status = sanctions.get("status", "unknown")
        pep_status = pep.get("status", "clear") if pep else "clear"
        
        risk_flags = []
        risk_score = 0
        
        # Check sanctions
        if sanctions_status == "hit":
            risk_flags.append("sanctions_hit")
            risk_score = 100
            action = ActionType.ESCALATE
            reasoning = f"SANCTIONS HIT: Individual matches sanctioned entity. Lists checked: {', '.join(sanctions.get('checked_lists', []))}. Immediate escalation required."
            confidence = 0.99
        
        elif sanctions_status == "potential_match":
            risk_flags.append("potential_sanctions_match")
            risk_score = 70
            action = ActionType.MANUAL_REVIEW
            reasoning = "Potential sanctions match found. Manual review required to confirm or clear."
            confidence = 0.7
        
        elif pep_status == "hit":
            risk_flags.append("pep_match")
            risk_score = 60
            action = ActionType.MANUAL_REVIEW
            reasoning = "Individual identified as Politically Exposed Person (PEP). Enhanced due diligence required."
            confidence = 0.8
        
        elif sanctions_status == "clear":
            action = ActionType.APPROVE
            reasoning = f"Compliance screening passed. No sanctions or PEP matches found. Lists checked: {', '.join(sanctions.get('checked_lists', []))}."
            confidence = 0.98
        
        else:
            risk_flags.append("screening_incomplete")
            risk_score = 50
            action = ActionType.MANUAL_REVIEW
            reasoning = "Compliance screening status unclear. Manual review required."
            confidence = 0.5
        
        return schemas.AgentRecommendationData(
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            risk_score=risk_score,
            risk_flags=risk_flags,
            confidence_breakdown=schemas.ConfidenceBreakdown(
                overall=confidence,
                components={
                    "sanctions_screening": 1.0 if sanctions_status == "clear" else 0.0,
                    "pep_screening": 1.0 if pep_status == "clear" else 0.5
                }
            )
        )


class RiskAgent(BaseAgent):
    """
    Risk Agent
    Calculates overall risk score based on various factors.
    """
    
    async def analyze(
        self,
        evidence: List[schemas.Evidence]
    ) -> schemas.AgentRecommendationData:
        """Calculate risk score"""
        risk_ev = self.get_evidence_by_type(evidence, "risk_assessment")
        
        # Collect risk factors from all evidence
        risk_factors = {}
        total_risk = 0
        risk_flags = []
        
        # Identity risk
        identity_ev = self.get_evidence_by_type(evidence, "identity")
        if identity_ev:
            identity_conf = self.extract_data_field(identity_ev, "confidence", 0.5)
            if identity_conf < 0.7:
                risk_factors["low_identity_confidence"] = 20
                risk_flags.append("low_identity_confidence")
                total_risk += 20
        else:
            risk_factors["missing_identity"] = 50
            risk_flags.append("missing_identity")
            total_risk += 50
        
        # Address risk
        address_ev = self.get_evidence_by_type(evidence, "address")
        if address_ev:
            address_verified = self.extract_data_field(address_ev, "verified", False)
            if not address_verified:
                risk_factors["address_unverified"] = 15
                risk_flags.append("address_unverified")
                total_risk += 15
        
        # Compliance risk
        compliance_ev = self.get_evidence_by_type(evidence, "compliance")
        if compliance_ev:
            sanctions_status = self.extract_data_field(
                compliance_ev,
                "sanctions_screening.status",
                "unknown"
            )
            if sanctions_status == "hit":
                risk_factors["sanctions_hit"] = 100
                risk_flags.append("sanctions_hit")
                total_risk = 100  # Override to max risk
        
        # Use explicit risk assessment if available
        if risk_ev:
            explicit_risk = self.extract_data_field(risk_ev, "risk_score", 0)
            explicit_flags = self.extract_data_field(risk_ev, "risk_flags", [])
            total_risk = max(total_risk, explicit_risk)
            risk_flags.extend(explicit_flags)
        
        # Normalize risk score
        risk_score = min(total_risk, 100)
        
        # Determine action based on risk score
        if risk_score >= 80:
            action = ActionType.ESCALATE
            reasoning = f"HIGH RISK (score: {risk_score}). Escalation required. Risk factors: {', '.join(risk_flags)}."
            confidence = 0.9
        elif risk_score >= 50:
            action = ActionType.MANUAL_REVIEW
            reasoning = f"MEDIUM RISK (score: {risk_score}). Manual review recommended. Risk factors: {', '.join(risk_flags)}."
            confidence = 0.75
        elif risk_score >= 30:
            action = ActionType.MANUAL_REVIEW
            reasoning = f"LOW-MEDIUM RISK (score: {risk_score}). Quick review suggested."
            confidence = 0.8
        else:
            action = ActionType.APPROVE
            reasoning = f"LOW RISK (score: {risk_score}). Risk within acceptable parameters."
            confidence = 0.9
        
        return schemas.AgentRecommendationData(
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            risk_score=risk_score,
            risk_flags=risk_flags,
            confidence_breakdown=schemas.ConfidenceBreakdown(
                overall=confidence,
                components=risk_factors
            )
        )
