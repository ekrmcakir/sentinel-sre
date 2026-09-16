import pytest
from sentinel_sre.models.incident import CloudAlarm, Incident, IncidentSeverity
from sentinel_sre.rca.engine import RootCauseAnalysisEngine
from sentinel_sre.telemetry.mock_collector import MockTelemetryCollector


@pytest.mark.asyncio
async def test_rca_lambda_concurrency_detection():
    collector = MockTelemetryCollector()
    alarm = CloudAlarm(
        alarm_name="Lambda_Throttle_Alarm",
        service="lambda",
        resource_arn="arn:aws:lambda:us-east-1:123456789012:function:payment-service",
        resource_name="payment-service",
        metric_name="Throttles",
        threshold=5.0,
        current_value=120.0,
    )
    incident = Incident(
        title="Lambda Throttling",
        severity=IncidentSeverity.P1_CRITICAL,
        alarm=alarm,
    )
    telemetry = await collector.collect_snapshot(alarm)

    rca = RootCauseAnalysisEngine()
    analysis = await rca.diagnose(incident, telemetry)

    assert analysis.primary_hypothesis is not None
    assert "Concurrency" in analysis.primary_hypothesis.summary
    assert analysis.confidence > 0.85
    assert analysis.primary_hypothesis.suggested_action_type == "lambda:set_concurrency"


@pytest.mark.asyncio
async def test_rca_sqs_dlq_detection():
    collector = MockTelemetryCollector()
    alarm = CloudAlarm(
        alarm_name="SQS_DLQ_Alarm",
        service="sqs",
        resource_arn="arn:aws:sqs:us-east-1:123456789012:order-dlq",
        resource_name="order-dlq",
        metric_name="ApproximateNumberOfMessagesVisible",
        threshold=50.0,
        current_value=1450.0,
    )
    incident = Incident(
        title="SQS Backlog",
        severity=IncidentSeverity.P2_HIGH,
        alarm=alarm,
    )
    telemetry = await collector.collect_snapshot(alarm)

    rca = RootCauseAnalysisEngine()
    analysis = await rca.diagnose(incident, telemetry)

    assert "DLQ" in analysis.primary_hypothesis.summary
    assert analysis.primary_hypothesis.suggested_action_type == "sqs:start_dlq_redrive"
