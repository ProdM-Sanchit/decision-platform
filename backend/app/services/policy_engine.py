"""
Policy Engine
Evaluates policy rules and manages policy lifecycle.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models import schemas
from app.models.schemas import ActionType, ActorType


class PolicyEngine:
    """Service for policy management and rule evaluation"""
    
    def __init__(self, db):
        self.db = db
    
    async def get_active_policy(self, vertical: str) -> schemas.Policy:
        """
        Get the active policy for a vertical.
        
        Args:
            vertical: Business vertical (kyc, insurance, procurement)
            
        Returns:
            Active policy
            
        Raises:
            ValueError: If no active policy found
        """
        # In real implementation, query from database
        # For now, return a mock policy
        
        # Query: SELECT * FROM policies WHERE vertical = ? AND active = true
        
        # Mock implementation
        if vertical == "kyc":
            return self._get_mock_kyc_policy()
        else:
            raise ValueError(f"No active policy found for vertical: {vertical}")
    
    async def get_policy(self, policy_id: str) -> schemas.Policy:
        """Get policy by ID"""
        # In real implementation, query from database
        # Mock for now
        return self._get_mock_kyc_policy()
    
    async def evaluate_rules(
        self,
        policy: schemas.Policy,
        case: schemas.Case,
        ensemble: schemas.EnsembleDecision
    ) -> "RuleMatch":
        """
        Evaluate policy rules against case and ensemble decision.
        Returns the first matching rule (rules are sorted by priority).
        
        Args:
            policy: Policy to evaluate
            case: Case being evaluated
            ensemble: Ensemble decision from agents
            
        Returns:
            RuleMatch with matched rule and action
        """
        from app.services.case_service import RuleMatch
        
        # Sort rules by priority (lower number = higher priority)
        sorted_rules = sorted(policy.rules, key=lambda r: r.priority)
        
        # Build evaluation context
        context = self._build_eval_context(case, ensemble)
        
        # Evaluate each rule
        for rule in sorted_rules:
            if self._evaluate_condition(rule.condition, context):
                return RuleMatch(
                    rule=rule,
                    action=rule.action,
                    assignee_role=rule.assignee_role,
                    sla_hours=rule.sla_hours
                )
        
        # Should never reach here if policy has default "*" rule
        raise ValueError("No matching rule found - policy must have default rule")
    
    async def is_transition_allowed(
        self,
        state_machine: schemas.StateMachine,
        from_state: schemas.CaseStatus,
        to_state: schemas.CaseStatus,
        actor: schemas.Actor
    ) -> bool:
        """
        Check if state transition is allowed by state machine.
        
        Args:
            state_machine: State machine configuration
            from_state: Current state
            to_state: Target state
            actor: Actor attempting transition
            
        Returns:
            True if transition is allowed
        """
        # Build transition key
        transition_key = f"{from_state.value} → {to_state.value}"
        
        # Check for wildcard transition (* → state)
        wildcard_key = f"* → {to_state.value}"
        
        # Get allowed actors for this transition
        allowed_actors = None
        if transition_key in state_machine.transitions:
            allowed_actors = state_machine.transitions[transition_key].get("allowed_actors", [])
        elif wildcard_key in state_machine.transitions:
            allowed_actors = state_machine.transitions[wildcard_key].get("allowed_actors", [])
        
        if not allowed_actors:
            return False
        
        # Check if actor type is allowed
        # Map actor type to policy actor names
        actor_map = {
            ActorType.SYSTEM: "system",
            ActorType.HUMAN: "reviewer",
            ActorType.API: "api"
        }
        
        policy_actor = actor_map.get(actor.type, actor.type.value)
        
        return policy_actor in allowed_actors or "workflow_engine" in allowed_actors
    
    async def simulate_policy(
        self,
        case_id: str,
        new_policy_id: str
    ) -> schemas.PolicySimulation:
        """
        Simulate what would happen if a different policy was applied to a case.
        Used for policy testing and compliance audits.
        
        Args:
            case_id: Case ID
            new_policy_id: Policy ID to simulate
            
        Returns:
            Simulation result showing differences
        """
        # Get original case and decision
        # In real implementation, get from database
        
        # Get ensemble decision (unchanged)
        # ensemble = await agent_orchestrator.get_ensemble(case_id)
        
        # Apply new policy
        # new_policy = await self.get_policy(new_policy_id)
        # new_rule_match = await self.evaluate_rules(new_policy, case, ensemble)
        
        # Return simulation
        # return schemas.PolicySimulation(...)
        
        raise NotImplementedError("Policy simulation not implemented")
    
    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================
    
    def _build_eval_context(
        self,
        case: schemas.Case,
        ensemble: schemas.EnsembleDecision
    ) -> Dict[str, Any]:
        """
        Build evaluation context for condition expressions.
        
        Returns dict with structure:
        {
            "case": {...},
            "ensemble": {
                "confidence": 0.95,
                "risk_score": 20,
                "risk_flags": [],
                ...
            },
            "compliance": {...},  # From evidence
            ...
        }
        """
        context = {
            "case": {
                "priority": case.priority.value,
                "vertical": case.vertical,
                "status": case.status.value
            },
            "ensemble": {
                "confidence": ensemble.final_recommendation.confidence,
                "risk_score": ensemble.final_recommendation.risk_score,
                "risk_flags": ensemble.final_recommendation.risk_flags,
                "action": ensemble.final_recommendation.action.value
            }
        }
        
        # TODO: Add evidence data to context
        # This would come from the evidence service
        # context["compliance"] = {...}
        # context["identity"] = {...}
        # context["address"] = {...}
        
        return context
    
    def _evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate condition expression against context.
        
        Condition DSL supports:
        - Property access: ensemble.confidence > 0.95
        - Comparisons: ==, !=, >, <, >=, <=
        - Boolean ops: AND, OR
        - Functions: .contains(), .empty()
        - Wildcards: *
        
        Args:
            condition: Condition string
            context: Evaluation context
            
        Returns:
            True if condition matches
        """
        # Handle wildcard (default rule)
        if condition == "*":
            return True
        
        # Parse and evaluate condition
        # In production, use a proper expression parser (pyparsing, lark, etc.)
        # For now, simple implementation
        
        try:
            # Replace DSL syntax with Python syntax
            python_expr = self._translate_condition(condition)
            
            # Safely evaluate
            return self._safe_eval(python_expr, context)
        except Exception as e:
            # Log error
            print(f"Error evaluating condition '{condition}': {e}")
            return False
    
    def _translate_condition(self, condition: str) -> str:
        """
        Translate DSL condition to Python expression.
        
        Examples:
        - "ensemble.confidence > 0.95" → "context['ensemble']['confidence'] > 0.95"
        - "risk_flags.empty()" → "len(context['risk_flags']) == 0"
        - "compliance.sanctions_screening.status == 'hit'" → "context['compliance']['sanctions_screening']['status'] == 'hit'"
        """
        # Simple implementation - in production use proper parser
        expr = condition
        
        # Replace property access
        # ensemble.confidence → context['ensemble']['confidence']
        import re
        
        # Match property paths like: word.word.word
        pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_\.]*)'
        
        def replace_property(match):
            parts = match.group(0).split('.')
            result = "context"
            for part in parts:
                result += f"['{part}']"
            return result
        
        expr = re.sub(pattern, replace_property, expr)
        
        # Replace functions
        expr = expr.replace('.empty()', ' == []')
        expr = expr.replace('.contains(', ' in ')
        
        # Replace boolean operators
        expr = expr.replace(' AND ', ' and ')
        expr = expr.replace(' OR ', ' or ')
        
        return expr
    
    def _safe_eval(self, expr: str, context: Dict[str, Any]) -> bool:
        """
        Safely evaluate expression with limited scope.
        
        Security: Only allow access to context dict, no imports/builtins.
        """
        # Whitelist of allowed names
        safe_dict = {
            "context": context,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "True": True,
            "False": False,
            "None": None
        }
        
        # Evaluate with restricted globals/locals
        try:
            result = eval(expr, {"__builtins__": {}}, safe_dict)
            return bool(result)
        except Exception as e:
            print(f"Error in safe_eval: {e}")
            return False
    
    def _get_mock_kyc_policy(self) -> schemas.Policy:
        """Return mock KYC policy for development"""
        return schemas.Policy(
            policy_id="pol_kyc_v1",
            policy_name="KYC Individual Verification",
            version="1.0",
            vertical="kyc",
            active=True,
            created_at=datetime.utcnow(),
            created_by="system",
            voting_strategy=schemas.VotingStrategyConfig(
                type="risk_weighted",
                config={
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
            ),
            rules=[
                schemas.PolicyRule(
                    priority=1,
                    name="Sanctions Hit",
                    condition="context['compliance']['sanctions_screening']['status'] == 'hit'",
                    action=ActionType.ESCALATE,
                    assignee_role="senior_compliance_officer",
                    sla_hours=2,
                    mandatory_reasoning=True
                ),
                schemas.PolicyRule(
                    priority=2,
                    name="High Confidence Auto-Approve",
                    condition="context['ensemble']['confidence'] > 0.95 and context['ensemble']['risk_score'] < 20",
                    action=ActionType.APPROVE,
                    sla_hours=None
                ),
                schemas.PolicyRule(
                    priority=3,
                    name="Low Confidence Manual Review",
                    condition="context['ensemble']['confidence'] < 0.70",
                    action=ActionType.MANUAL_REVIEW,
                    assignee_role="kyc_analyst",
                    sla_hours=24
                ),
                schemas.PolicyRule(
                    priority=99,
                    name="Default Manual Review",
                    condition="*",
                    action=ActionType.MANUAL_REVIEW,
                    assignee_role="kyc_analyst",
                    sla_hours=24
                )
            ],
            state_machine=schemas.StateMachine(
                states=[
                    "draft", "submitted", "processing",
                    "under_review", "under_review.identity_check",
                    "under_review.fraud_check", "under_review.compliance_check",
                    "under_review.manual_review",
                    "approved", "rejected", "needs_more_info", "expired"
                ],
                transitions={
                    "draft → submitted": {"allowed_actors": ["customer", "api"]},
                    "submitted → processing": {"allowed_actors": ["system"]},
                    "processing → under_review.*": {"allowed_actors": ["system", "workflow_engine"]},
                    "under_review.* → approved": {"allowed_actors": ["workflow_engine", "reviewer"]},
                    "under_review.* → rejected": {"allowed_actors": ["workflow_engine", "reviewer"]},
                    "under_review.* → needs_more_info": {"allowed_actors": ["reviewer"]},
                    "needs_more_info → submitted": {"allowed_actors": ["customer"]},
                    "* → expired": {"allowed_actors": ["system"]}
                },
                terminal_states=["approved", "rejected", "expired"]
            )
        )
