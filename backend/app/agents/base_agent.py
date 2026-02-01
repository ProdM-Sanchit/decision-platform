"""
Base Agent
Abstract base class for all agents in the system.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from app.models import schemas


class BaseAgent(ABC):
    """
    Abstract base class for all decision agents.
    
    All agents must:
    1. Analyze evidence
    2. Return a recommendation with confidence
    3. Provide reasoning for the recommendation
    4. Never directly change system state
    """
    
    def __init__(self):
        self.version = "1.0.0"
    
    @abstractmethod
    async def analyze(
        self,
        evidence: List[schemas.Evidence]
    ) -> schemas.AgentRecommendationData:
        """
        Analyze evidence and return recommendation.
        
        Args:
            evidence: List of evidence objects for the case
            
        Returns:
            AgentRecommendationData with action, confidence, reasoning
        """
        pass
    
    def get_evidence_by_type(
        self,
        evidence: List[schemas.Evidence],
        evidence_type: str
    ) -> Optional[schemas.Evidence]:
        """Helper to get evidence by type"""
        for evd in evidence:
            if evd.evidence_type == evidence_type:
                return evd
        return None
    
    def extract_data_field(
        self,
        evidence: Optional[schemas.Evidence],
        field_path: str,
        default: Any = None
    ) -> Any:
        """
        Extract a field from evidence data using dot notation.
        
        Example:
            extract_data_field(evidence, "identity.verified", False)
        """
        if not evidence:
            return default
        
        data = evidence.data
        fields = field_path.split('.')
        
        for field in fields:
            if isinstance(data, dict) and field in data:
                data = data[field]
            else:
                return default
        
        return data
