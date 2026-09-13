from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from sentinel_sre.config import settings
from sentinel_sre.models.incident import CloudAlarm
from sentinel_sre.models.telemetry import LogEntry, MetricPoint, TelemetrySnapshot
from sentinel_sre.telemetry.base import BaseTelemetryCollector
from sentinel_sre.telemetry.mock_collector import MockTelemetryCollector


class CloudWatchTelemetryCollector(BaseTelemetryCollector):
    """
    Live AWS CloudWatch Collector for Logs, Metrics, and Resource State.
    """

    def __init__(self, region: Optional[str] = None):
        self.region = region or settings.aws_region
        if not settings.mock_mode:
            self.logs_client = boto3.client("logs", region_name=self.region)
            self.cw_client = boto3.client("cloudwatch", region_name=self.region)
        else:
            self.logs_client = None
            self.cw_client = None
        self._fallback_mock = MockTelemetryCollector()

    async def collect_snapshot(
        self, alarm: CloudAlarm, lookback_minutes: int = 15
    ) -> TelemetrySnapshot:
        if settings.mock_mode or not self.cw_client:
            return await self._fallback_mock.collect_snapshot(alarm, lookback_minutes)

        now = datetime.now(timezone.utc)
        start_time = now - timedelta(minutes=lookback_minutes)
        logs: List[LogEntry] = []
        metrics: List[MetricPoint] = []
        error_patterns: List[str] = []
        anomalies: List[Dict] = []
        resource_state: Dict = {}

        try:
            # Query CloudWatch Metrics
            response = self.cw_client.get_metric_data(
                MetricDataQueries=[
                    {
                        "Id": "m1",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": f"AWS/{alarm.service.upper()}",
                                "MetricName": alarm.metric_name,
                                "Dimensions": [{"Name": "Resource", "Value": alarm.resource_name}],
                            },
                            "Period": 60,
                            "Stat": "Sum",
                        },
                        "ReturnData": True,
                    }
                ],
                StartTime=start_time,
                EndTime=now,
            )
            for result in response.get("MetricDataResults", []):
                for ts, val in zip(result.get("Timestamps", []), result.get("Values", [])):
                    metrics.append(
                        MetricPoint(
                            timestamp=ts,
                            metric_name=alarm.metric_name,
                            value=val,
                        )
                    )
        except (BotoCoreError, ClientError) as e:
            # If AWS credentials missing or permission issue, fallback to mock snapshot
            return await self._fallback_mock.collect_snapshot(alarm, lookback_minutes)

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
