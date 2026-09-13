from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import random

from sentinel_sre.models.incident import CloudAlarm
from sentinel_sre.models.telemetry import LogEntry, MetricPoint, TelemetrySnapshot
from sentinel_sre.telemetry.base import BaseTelemetryCollector


class MockTelemetryCollector(BaseTelemetryCollector):
    """
    Offline simulator generating rich telemetry for local testing and chaos scenarios.
    """

    def __init__(self, scenario_data: Optional[Dict] = None):
        self.scenario_data = scenario_data or {}

    async def collect_snapshot(
        self, alarm: CloudAlarm, lookback_minutes: int = 15
    ) -> TelemetrySnapshot:
        now = datetime.now(timezone.utc)
        logs: List[LogEntry] = []
        metrics: List[MetricPoint] = []
        error_patterns: List[str] = []
        anomalies: List[Dict] = []
        resource_state: Dict = {}

        if alarm.service == "lambda":
            # Scenario: Lambda Concurrency / Throttling / Timeout
            resource_state = {
                "FunctionName": alarm.resource_name,
                "Runtime": "python3.11",
                "MemorySize": 256,
                "Timeout": 30,
                "ReservedConcurrentExecutions": 10,
                "State": "Active",
            }
            error_patterns = [
                "Task timed out after 30.00 seconds",
                "Rate exceeded (ThrottlingException)",
                "Lambda.TooManyRequestsException",
            ]
            for i in range(10):
                t = now - timedelta(minutes=random.randint(1, lookback_minutes))
                logs.append(
                    LogEntry(
                        timestamp=t,
                        log_level="ERROR",
                        message=f"2026-09-17T12:00:{i:02d}Z [ERROR] ClientError: An error occurred (TooManyRequestsException) when calling Invoke API: ConcurrencyLimitExceeded for {alarm.resource_name}",
                        stream_name=f"2026/09/17/[$LATEST]stream_{i}",
                    )
                )
            metrics.append(MetricPoint(metric_name="Throttles", value=142.0, dimensions={"FunctionName": alarm.resource_name}))
            metrics.append(MetricPoint(metric_name="ConcurrentExecutions", value=10.0, dimensions={"FunctionName": alarm.resource_name}))
            metrics.append(MetricPoint(metric_name="Duration", value=29800.0, unit="Milliseconds", dimensions={"FunctionName": alarm.resource_name}))
            anomalies.append({
                "metric": "Throttles",
                "deviation_sigma": 4.8,
                "baseline_mean": 0.2,
                "observed_value": 142.0,
            })

        elif alarm.service == "sqs":
            # Scenario: SQS Dead Letter Queue backlog
            resource_state = {
                "QueueUrl": f"https://sqs.us-east-1.amazonaws.com/123456789012/{alarm.resource_name}",
                "ApproximateNumberOfMessages": 1450,
                "ApproximateNumberOfMessagesDelayed": 0,
                "RedrivePolicy": '{"deadLetterTargetArn":"arn:aws:sqs:...","maxReceiveCount":3}',
            }
            error_patterns = [
                "ConnectionResetError: [Errno 54] Connection reset by peer",
                "DatabaseConnectionTimeout: pool exhausted after 30000ms",
            ]
            for i in range(8):
                t = now - timedelta(minutes=random.randint(1, lookback_minutes))
                logs.append(
                    LogEntry(
                        timestamp=t,
                        log_level="ERROR",
                        message=f"Worker node failed to process message payload {i}: DBConnectionTimeout -> Routing to DLQ {alarm.resource_name}",
                        stream_name=f"worker_pool_stream_{i}",
                    )
                )
            metrics.append(MetricPoint(metric_name="ApproximateNumberOfMessagesVisible", value=1450.0, dimensions={"QueueName": alarm.resource_name}))
            metrics.append(MetricPoint(metric_name="NumberOfMessagesReceived", value=5200.0, dimensions={"QueueName": alarm.resource_name}))
            anomalies.append({
                "metric": "ApproximateNumberOfMessagesVisible",
                "deviation_sigma": 6.2,
                "baseline_mean": 0.0,
                "observed_value": 1450.0,
            })

        elif alarm.service == "ecs":
            # Scenario: Container CrashLoopBackOff / OutOfMemory
            resource_state = {
                "ClusterName": "production-cluster",
                "ServiceName": alarm.resource_name,
                "DesiredCount": 4,
                "RunningCount": 1,
                "PendingCount": 3,
                "LastExitCode": 137,  # OOMKilled
            }
            error_patterns = [
                "OutOfMemoryError: Container killed by Linux OOM killer (exit code 137)",
                "Health check failed (HTTP 502 Bad Gateway)",
            ]
            for i in range(5):
                t = now - timedelta(minutes=random.randint(1, lookback_minutes))
                logs.append(
                    LogEntry(
                        timestamp=t,
                        log_level="CRITICAL",
                        message=f"container_task_{i} essential container exited with exit_code=137 (OOMKill) - recycling task",
                        stream_name=f"ecs_task_log_{i}",
                    )
                )
            metrics.append(MetricPoint(metric_name="MemoryUtilization", value=99.4, unit="Percent", dimensions={"ServiceName": alarm.resource_name}))
            metrics.append(MetricPoint(metric_name="CPUUtilization", value=84.2, unit="Percent", dimensions={"ServiceName": alarm.resource_name}))
            anomalies.append({
                "metric": "MemoryUtilization",
                "deviation_sigma": 5.1,
                "baseline_mean": 45.0,
                "observed_value": 99.4,
            })

        return TelemetrySnapshot(
            resource_id=alarm.resource_name,
            service=alarm.service,
            captured_at=now,
            logs=logs,
            metrics=metrics,
            error_patterns=error_patterns,
            anomalies=anomalies,
            resource_state=resource_state,
        )
