from abc import ABC, abstractmethod
from typing import Optional
from sentinel_sre.models.incident import CloudAlarm
from sentinel_sre.models.telemetry import TelemetrySnapshot


class BaseTelemetryCollector(ABC):
    """Abstract interface for collecting cloud metrics, logs, and resource states."""

    @abstractmethod
    async def collect_snapshot(
        self, alarm: CloudAlarm, lookback_minutes: int = 15
    ) -> TelemetrySnapshot:
        """Collects relevant logs and metric series for the target resource."""
        pass
