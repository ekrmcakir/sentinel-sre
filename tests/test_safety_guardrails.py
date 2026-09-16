import pytest
from sentinel_sre.models.actions import ActionRiskLevel, RemediationAction
from sentinel_sre.safety.guardrails import SafetyGuardrailEngine


@pytest.fixture
def guardrail():
    return SafetyGuardrailEngine()


def test_safe_sqs_action_allowed(guardrail):
    action = RemediationAction(
        action_type="sqs:start_dlq_redrive",
        service="sqs",
        target_resource="orders-dlq",
        parameters={"max_number_of_messages": 1000},
        description="Redrive DLQ messages",
    )
    verdict = guardrail.evaluate_action(action)
    assert verdict.allowed is True
    assert verdict.requires_human_approval is False
    assert verdict.risk_level == ActionRiskLevel.LOW


def test_safe_lambda_concurrency_allowed(guardrail):
    action = RemediationAction(
        action_type="lambda:set_concurrency",
        service="lambda",
        target_resource="checkout-fn",
        parameters={"concurrency": 100},
        description="Scale concurrency to 100",
    )
    verdict = guardrail.evaluate_action(action)
    assert verdict.allowed is True
    assert verdict.requires_human_approval is False


def test_excessive_lambda_concurrency_blocked(guardrail):
    action = RemediationAction(
        action_type="lambda:set_concurrency",
        service="lambda",
        target_resource="checkout-fn",
        parameters={"concurrency": 5000},  # Exceeds max 500
        description="Dangerous massive scale",
    )
    verdict = guardrail.evaluate_action(action)
    assert verdict.allowed is False
    assert verdict.requires_human_approval is True
    assert len(verdict.violations) > 0


def test_dangerous_denylist_action_hard_blocked(guardrail):
    action = RemediationAction(
        action_type="rds:delete_db_instance",
        service="rds",
        target_resource="prod-db",
        description="Drop DB",
    )
    verdict = guardrail.evaluate_action(action)
    assert verdict.allowed is False
    assert verdict.requires_human_approval is False
    assert verdict.risk_level == ActionRiskLevel.CRITICAL
    assert verdict.blast_radius_score == 1.0


def test_high_risk_rds_reboot_requires_approval(guardrail):
    action = RemediationAction(
        action_type="rds:reboot_db_instance",
        service="rds",
        target_resource="prod-aurora-cluster",
        description="Reboot DB instance",
    )
    verdict = guardrail.evaluate_action(action)
    assert verdict.allowed is False
    assert verdict.requires_human_approval is True
    assert verdict.risk_level == ActionRiskLevel.HIGH
