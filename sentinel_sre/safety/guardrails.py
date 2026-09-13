import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from sentinel_sre.config import settings
from sentinel_sre.models.actions import ActionRiskLevel, RemediationAction, SafetyVerdict


class SafetyGuardrailEngine:
    """
    Deterministic Policy Engine enforcing Blast-Radius limits, Action Allowlists,
    and Human-in-the-Loop approvals.
    """

    def __init__(self, policy_file: Optional[Path] = None):
        self.policy_file = policy_file or settings.guardrails_config_path
        self.policies = self._load_policies()

    def _load_policies(self) -> Dict[str, Any]:
        if not self.policy_file.exists():
            # Fallback default policy if file missing
            return {
                "policies": [],
                "denylist": ["*:delete*", "*:terminate*"],
                "global": {"max_consecutive_actions_per_hour": 5},
            }
        with open(self.policy_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def evaluate_action(self, action: RemediationAction) -> SafetyVerdict:
        """
        Evaluate a proposed remediation action against safety rules.
        Returns a SafetyVerdict detailing whether it can execute autonomously,
        requires human approval, or is forbidden.
        """
        violations: List[str] = []

        # 1. Denylist Check (Hard Block)
        denylist = self.policies.get("denylist", [])
        for pattern in denylist:
            if fnmatch.fnmatch(action.action_type, pattern):
                return SafetyVerdict(
                    allowed=False,
                    requires_human_approval=False,
                    risk_level=ActionRiskLevel.CRITICAL,
                    reason=f"Action '{action.action_type}' is strictly forbidden by security denylist pattern '{pattern}'.",
                    violations=[f"Denylist match: {pattern}"],
                    blast_radius_score=1.0,
                )

        # 2. Find matching policy definition
        policy_rules = self.policies.get("policies", [])
        matching_rule = next(
            (p for p in policy_rules if p["action_type"] == action.action_type), None
        )

        if not matching_rule:
            # Unknown action: block autonomous execution, require human gate
            return SafetyVerdict(
                allowed=False,
                requires_human_approval=True,
                risk_level=ActionRiskLevel.HIGH,
                reason=f"Action '{action.action_type}' does not have a registered safety policy. Manual verification required.",
                violations=["Unregistered action type"],
                blast_radius_score=0.8,
            )

        risk_level = ActionRiskLevel(matching_rule.get("risk_level", "MEDIUM"))
        auto_approve = matching_rule.get("auto_approve", False)

        # 3. Parameter Boundary & Blast Radius Checks
        blast_radius_score = 0.2
        if action.action_type == "lambda:set_concurrency":
            concurrency = action.parameters.get("concurrency", 0)
            max_allowed = matching_rule.get("max_allowed_concurrency", 500)
            min_allowed = matching_rule.get("min_allowed_concurrency", 5)

            if concurrency > max_allowed:
                violations.append(
                    f"Requested concurrency ({concurrency}) exceeds safe maximum limit ({max_allowed})."
                )
            if concurrency < min_allowed:
                violations.append(
                    f"Requested concurrency ({concurrency}) is below safe minimum limit ({min_allowed})."
                )
            blast_radius_score = min(1.0, concurrency / max_allowed)

        elif action.action_type == "sqs:start_dlq_redrive":
            max_msgs = matching_rule.get("max_messages_per_run", 50000)
            target_msgs = action.parameters.get("max_number_of_messages", 1000)
            if target_msgs > max_msgs:
                violations.append(
                    f"DLQ redrive batch ({target_msgs}) exceeds max safe threshold ({max_msgs})."
                )
            blast_radius_score = 0.1

        elif action.action_type == "ecs:recycle_service":
            blast_radius_score = 0.3

        # 4. Final Verdict Calculation
        if violations:
            return SafetyVerdict(
                allowed=False,
                requires_human_approval=True,
                risk_level=ActionRiskLevel.HIGH,
                reason=f"Action parameters violated safety boundaries: {'; '.join(violations)}",
                violations=violations,
                blast_radius_score=blast_radius_score,
            )

        if not auto_approve:
            return SafetyVerdict(
                allowed=False,
                requires_human_approval=True,
                risk_level=risk_level,
                reason=f"Action '{action.action_type}' is classified as {risk_level.value} risk and requires manual SRE approval.",
                violations=[],
                blast_radius_score=blast_radius_score,
            )

        return SafetyVerdict(
            allowed=True,
            requires_human_approval=False,
            risk_level=risk_level,
            reason="Action conforms to all policy-as-code safety guardrails and blast-radius limits.",
            violations=[],
            blast_radius_score=blast_radius_score,
        )


guardrail_engine = SafetyGuardrailEngine()
