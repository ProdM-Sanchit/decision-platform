"""
Agent Orchestrator
Manages multi-agent analysis and ensemble voting.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from app.models import schemas
from app.models.schemas import ActionType, ActorType
from app.agents.base_agent import BaseAgent
from app.agents.identity_agent import IdentityAgent
from app.agents.fraud_agent import FraudAgent
from app.agents.compliance_agent import ComplianceAgent
from app.agents.risk_agent import RiskAgent


class AgentOrchestrator:
    """Service for orchestrating multi-agent analysis"""
    
    def __init__(self, db):
        self.db = db
        
        # Initialize agents
        self.agents: Dict[str, BaseAgent] = {
            "identity_agent": IdentityAgent(),
            "fraud_agent": FraudAgent(),
            "compliance_agent": ComplianceAgent(),
            "risk_agent": RiskAgent()
        }
    
    async def run_all_agents(
        self,
        case_id: str,
        evidence: List[schemas.Evidence]
    ) -> List[schemas.AgentRecommendation]:
        """
        Run all agents in parallel and collect recommendations.
        
        Args:
            case_id: Case ID
            evidence: All evidence for the case
            
        Returns:
            List of agent recommendations
        """
        # Run agents in parallel
        tasks = []
        for agent_name, agent in self.agents.items():
            task = self._run_agent(
                agent=agent,
                agent_name=agent_name,
                case_id=case_id,
                evidence=evidence
            )
            tasks.append(task)
        
        recommendations = await asyncio.gather(*tasks)
        
        # Save recommendations to database
        for rec in recommendations:
            await self._save_recommendation(rec)
        
        return recommendations
    
    async def synthesize_ensemble(
        self,
        case_id: str,
        agent_recommendations: List[schemas.AgentRecommendation],
        policy_version: str
    ) -> schemas.EnsembleDecision:
        """
        Synthesize agent recommendations into ensemble decision.
        Uses voting strategy from policy.
        
        Args:
            case_id: Case ID
            agent_recommendations: Individual agent recommendations
            policy_version: Policy version (contains voting strategy)
            
        Returns:
            Ensemble decision
        """
        # Get policy to determine voting strategy
        from app.services.policy_engine import PolicyEngine
        policy_engine = PolicyEngine(self.db)
        policy = await policy_engine.get_policy(policy_version)
        
        # Get voting strategy
        strategy_type = policy.voting_strategy.type
        strategy_config = policy.voting_strategy.config
        
        # Select voting strategy implementation
        if strategy_type == "weighted":
            ensemble = await self._weighted_voting(
                agent_recommendations,
                strategy_config
            )
        elif strategy_type == "conservative":
            ensemble = await self._conservative_voting(
                agent_recommendations,
                strategy_config
            )
        elif strategy_type == "risk_weighted":
            ensemble = await self._risk_weighted_voting(
                agent_recommendations,
                strategy_config
            )
        else:
            raise ValueError(f"Unknown voting strategy: {strategy_type}")
        
        # Create ensemble decision record
        ensemble_decision = schemas.EnsembleDecision(
            ensemble_id=f"ens_{self._generate_id()}",
            case_id=case_id,
            timestamp=datetime.utcnow(),
            voting_strategy=strategy_type,
            agent_recommendations=ensemble["agent_votes"],
            final_recommendation=ensemble["final_recommendation"]
        )
        
        # Save to database
        await self._save_ensemble(ensemble_decision)
        
        return ensemble_decision
    
    async def get_ensemble(self, case_id: str) -> Optional[schemas.EnsembleDecision]:
        """Get ensemble decision for a case"""
        # In real implementation, query from database
        # Placeholder for now
        return None
    
    # ========================================================================
    # VOTING STRATEGIES
    # ========================================================================
    
    async def _weighted_voting(
        self,
        recommendations: List[schemas.AgentRecommendation],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Weighted voting: Each agent has a weight, final decision is weighted average.
        
        Args:
            recommendations: Agent recommendations
            config: Strategy configuration with agent weights
            
        Returns:
            Ensemble result with final recommendation
        """
        agent_weights = config.get("agent_weights", {})
        
        # Collect votes
        agent_votes = []
        total_weight = 0
        weighted_confidence = 0
        action_weights = {}  # action -> total weight
        
        for rec in recommendations:
            weight = agent_weights.get(rec.agent_name, 1.0)
            action = rec.recommendation.action
            confidence = rec.recommendation.confidence
            
            agent_votes.append(schemas.AgentVote(
                agent=rec.agent_name,
                action=action,
                confidence=confidence,
                weight=weight
            ))
            
            # Accumulate weighted confidence
            weighted_confidence += confidence * weight
            total_weight += weight
            
            # Accumulate action weights
            action_weights[action] = action_weights.get(action, 0) + weight
        
        # Calculate final weighted confidence
        final_confidence = weighted_confidence / total_weight if total_weight > 0 else 0
        
        # Winning action is the one with highest total weight
        final_action = max(action_weights.items(), key=lambda x: x[1])[0]
        
        # Calculate voting details
        voting_details = self._calculate_voting_details(
            agent_votes,
            final_confidence,
            action_weights
        )
        
        # Synthesize reasoning
        reasoning = self._synthesize_reasoning(recommendations, final_action)
        
        # Aggregate risk
        risk_score, risk_flags = self._aggregate_risk(recommendations)
        
        return {
            "agent_votes": agent_votes,
            "final_recommendation": schemas.EnsembleRecommendation(
                action=final_action,
                confidence=final_confidence,
                reasoning=reasoning,
                risk_score=risk_score,
                risk_flags=risk_flags,
                voting_details=voting_details
            )
        }
    
    async def _conservative_voting(
        self,
        recommendations: List[schemas.AgentRecommendation],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Conservative voting: Most restrictive recommendation wins.
        Priority: reject > escalate > manual_review > approve
        
        Args:
            recommendations: Agent recommendations
            config: Strategy configuration
            
        Returns:
            Ensemble result
        """
        # Action priority (higher = more restrictive)
        action_priority = {
            ActionType.REJECT: 4,
            ActionType.ESCALATE: 3,
            ActionType.MANUAL_REVIEW: 2,
            ActionType.REQUEST_MORE_INFO: 2,
            ActionType.APPROVE: 1
        }
        
        # Find most restrictive action
        most_restrictive = None
        highest_priority = 0
        
        agent_votes = []
        for rec in recommendations:
            action = rec.recommendation.action
            priority = action_priority.get(action, 0)
            
            agent_votes.append(schemas.AgentVote(
                agent=rec.agent_name,
                action=action,
                confidence=rec.recommendation.confidence,
                weight=1.0
            ))
            
            if priority > highest_priority:
                highest_priority = priority
                most_restrictive = rec
        
        # Use most restrictive recommendation
        final_action = most_restrictive.recommendation.action
        final_confidence = most_restrictive.recommendation.confidence
        
        # Calculate voting details
        action_counts = {}
        for vote in agent_votes:
            action_counts[vote.action] = action_counts.get(vote.action, 0) + 1
        
        voting_details = schemas.VotingDetails(
            approve_votes=action_counts.get(ActionType.APPROVE, 0),
            reject_votes=action_counts.get(ActionType.REJECT, 0),
            manual_review_votes=action_counts.get(ActionType.MANUAL_REVIEW, 0),
            escalate_votes=action_counts.get(ActionType.ESCALATE, 0),
            weighted_confidence=final_confidence,
            consensus_level="conservative"
        )
        
        reasoning = f"Conservative strategy: {most_restrictive.agent_name} recommended {final_action.value}, which is the most restrictive action."
        risk_score, risk_flags = self._aggregate_risk(recommendations)
        
        return {
            "agent_votes": agent_votes,
            "final_recommendation": schemas.EnsembleRecommendation(
                action=final_action,
                confidence=final_confidence,
                reasoning=reasoning,
                risk_score=risk_score,
                risk_flags=risk_flags,
                voting_details=voting_details
            )
        }
    
    async def _risk_weighted_voting(
        self,
        recommendations: List[schemas.AgentRecommendation],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Risk-weighted voting:
        - High-risk cases require unanimous approval
        - Low-risk cases use majority voting
        - Medium-risk uses weighted voting
        
        Args:
            recommendations: Agent recommendations
            config: Strategy configuration
            
        Returns:
            Ensemble result
        """
        high_threshold = config.get("high_risk_threshold", 70)
        low_threshold = config.get("low_risk_threshold", 30)
        agent_weights = config.get("agent_weights", {})
        
        # Calculate aggregate risk
        risk_score, risk_flags = self._aggregate_risk(recommendations)
        
        # Determine consensus requirement
        if risk_score >= high_threshold:
            # High risk: require unanimous approval
            consensus_required = "unanimous"
        elif risk_score <= low_threshold:
            # Low risk: majority vote
            consensus_required = "majority"
        else:
            # Medium risk: weighted vote
            consensus_required = "weighted"
        
        agent_votes = []
        action_counts = {}
        weighted_confidence = 0
        total_weight = 0
        
        for rec in recommendations:
            weight = agent_weights.get(rec.agent_name, 1.0)
            action = rec.recommendation.action
            confidence = rec.recommendation.confidence
            
            agent_votes.append(schemas.AgentVote(
                agent=rec.agent_name,
                action=action,
                confidence=confidence,
                weight=weight
            ))
            
            action_counts[action] = action_counts.get(action, 0) + 1
            weighted_confidence += confidence * weight
            total_weight += weight
        
        # Determine final action based on consensus requirement
        if consensus_required == "unanimous":
            # All agents must agree on approve, otherwise manual review
            approve_count = action_counts.get(ActionType.APPROVE, 0)
            if approve_count == len(recommendations):
                final_action = ActionType.APPROVE
                consensus_level = "unanimous"
            else:
                final_action = ActionType.MANUAL_REVIEW
                consensus_level = "not_unanimous"
        
        elif consensus_required == "majority":
            # Simple majority
            final_action = max(action_counts.items(), key=lambda x: x[1])[0]
            consensus_level = "majority"
        
        else:  # weighted
            # Weighted vote
            action_weights = {}
            for vote in agent_votes:
                action_weights[vote.action] = action_weights.get(vote.action, 0) + vote.weight
            final_action = max(action_weights.items(), key=lambda x: x[1])[0]
            consensus_level = "weighted"
        
        final_confidence = weighted_confidence / total_weight if total_weight > 0 else 0
        
        voting_details = schemas.VotingDetails(
            approve_votes=action_counts.get(ActionType.APPROVE, 0),
            reject_votes=action_counts.get(ActionType.REJECT, 0),
            manual_review_votes=action_counts.get(ActionType.MANUAL_REVIEW, 0),
            escalate_votes=action_counts.get(ActionType.ESCALATE, 0),
            weighted_confidence=final_confidence,
            consensus_level=consensus_level
        )
        
        reasoning = self._synthesize_reasoning(recommendations, final_action)
        
        return {
            "agent_votes": agent_votes,
            "final_recommendation": schemas.EnsembleRecommendation(
                action=final_action,
                confidence=final_confidence,
                reasoning=reasoning,
                risk_score=risk_score,
                risk_flags=risk_flags,
                voting_details=voting_details
            )
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _run_agent(
        self,
        agent: BaseAgent,
        agent_name: str,
        case_id: str,
        evidence: List[schemas.Evidence]
    ) -> schemas.AgentRecommendation:
        """Run a single agent and return its recommendation"""
        start_time = datetime.utcnow()
        
        try:
            # Run agent analysis
            recommendation_data = await agent.analyze(evidence)
            
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return schemas.AgentRecommendation(
                recommendation_id=f"rec_{self._generate_id()}",
                case_id=case_id,
                agent_name=agent_name,
                agent_version=agent.version,
                timestamp=datetime.utcnow(),
                recommendation=recommendation_data,
                processing_time_ms=processing_time
            )
        except Exception as e:
            # If agent fails, return low-confidence manual review recommendation
            print(f"Agent {agent_name} failed: {e}")
            return schemas.AgentRecommendation(
                recommendation_id=f"rec_{self._generate_id()}",
                case_id=case_id,
                agent_name=agent_name,
                agent_version=agent.version,
                timestamp=datetime.utcnow(),
                recommendation=schemas.AgentRecommendationData(
                    action=ActionType.MANUAL_REVIEW,
                    confidence=0.0,
                    reasoning=f"Agent {agent_name} encountered an error and could not complete analysis.",
                    risk_score=100,
                    risk_flags=["agent_error"]
                ),
                processing_time_ms=0
            )
    
    def _calculate_voting_details(
        self,
        agent_votes: List[schemas.AgentVote],
        final_confidence: float,
        action_weights: Dict[ActionType, float]
    ) -> schemas.VotingDetails:
        """Calculate voting details from agent votes"""
        action_counts = {}
        for vote in agent_votes:
            action_counts[vote.action] = action_counts.get(vote.action, 0) + 1
        
        # Determine consensus level
        max_votes = max(action_weights.values()) if action_weights else 0
        total_votes = sum(action_weights.values())
        
        if max_votes == total_votes:
            consensus = "unanimous"
        elif max_votes > total_votes * 0.7:
            consensus = "strong_majority"
        elif max_votes > total_votes * 0.5:
            consensus = "majority"
        else:
            consensus = "divided"
        
        return schemas.VotingDetails(
            approve_votes=action_counts.get(ActionType.APPROVE, 0),
            reject_votes=action_counts.get(ActionType.REJECT, 0),
            manual_review_votes=action_counts.get(ActionType.MANUAL_REVIEW, 0),
            escalate_votes=action_counts.get(ActionType.ESCALATE, 0),
            weighted_confidence=final_confidence,
            consensus_level=consensus
        )
    
    def _synthesize_reasoning(
        self,
        recommendations: List[schemas.AgentRecommendation],
        final_action: ActionType
    ) -> str:
        """Synthesize reasoning from all agent recommendations"""
        # Collect key points from agents
        points = []
        for rec in recommendations:
            agent_name = rec.agent_name.replace("_agent", "").title()
            action = rec.recommendation.action.value
            confidence = int(rec.recommendation.confidence * 100)
            
            # Extract first sentence of reasoning
            reasoning_preview = rec.recommendation.reasoning.split('.')[0]
            
            points.append(f"{agent_name} ({action}, {confidence}% confident): {reasoning_preview}")
        
        # Build final reasoning
        reasoning = f"Ensemble decision: {final_action.value}. "
        reasoning += " | ".join(points)
        
        return reasoning
    
    def _aggregate_risk(
        self,
        recommendations: List[schemas.AgentRecommendation]
    ) -> tuple[int, List[str]]:
        """Aggregate risk scores and flags from all agents"""
        # Take maximum risk score (most conservative)
        risk_scores = [
            rec.recommendation.risk_score
            for rec in recommendations
            if rec.recommendation.risk_score is not None
        ]
        risk_score = max(risk_scores) if risk_scores else 50
        
        # Combine all risk flags (deduplicated)
        risk_flags = set()
        for rec in recommendations:
            risk_flags.update(rec.recommendation.risk_flags)
        
        return risk_score, list(risk_flags)
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        return str(uuid.uuid4())[:12]
    
    async def _save_recommendation(self, rec: schemas.AgentRecommendation) -> None:
        """Save agent recommendation to database"""
        # Placeholder
        pass
    
    async def _save_ensemble(self, ensemble: schemas.EnsembleDecision) -> None:
        """Save ensemble decision to database"""
        # Placeholder
        pass
