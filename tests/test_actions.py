import pytest
from sentinel_sre.actions import get_action_executor
from sentinel_sre.models.actions import RemediationAction


@pytest.mark.asyncio
async def test_lambda_action_mock_execution():
    executor = get_action_executor("lambda")
    action = RemediationAction(
        action_type="lambda:set_concurrency",
        service="lambda",
        target_resource="mock-payment-service",
        parameters={"concurrency": 150},
        description="Scale concurrency",
    )
    result = await executor.execute(action)
    assert result.success is True
    assert result.duration_ms > 0
    assert result.output["reserved_concurrency"] == 150


@pytest.mark.asyncio
async def test_sqs_action_mock_execution():
    executor = get_action_executor("sqs")
    action = RemediationAction(
        action_type="sqs:start_dlq_redrive",
        service="sqs",
        target_resource="mock-order-dlq",
        parameters={"max_number_of_messages": 2000},
        description="Redrive DLQ",
    )
    result = await executor.execute(action)
    assert result.success is True
    assert result.output["status"] == "RUNNING"


@pytest.mark.asyncio
async def test_ecs_action_mock_execution():
    executor = get_action_executor("ecs")
    action = RemediationAction(
        action_type="ecs:recycle_service",
        service="ecs",
        target_resource="mock-user-service",
        parameters={"cluster": "production-cluster"},
        description="Recycle tasks",
    )
    result = await executor.execute(action)
    assert result.success is True
    assert result.output["strategy"] == "ROLLING_RECYCLE"
