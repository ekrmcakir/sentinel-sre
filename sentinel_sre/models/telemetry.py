from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str
    log_level: str = "ERROR"
    stream_name: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class MetricPoint(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metric_name: str
    value: float
    unit: str = "Count"
    dimensions: Dict[str, str] = Field(default_factory=dict)


class TelemetrySnapshot(BaseModel):
    resource_id: str
    service: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    logs: List[LogEntry] = Field(default_factory=list)
    metrics: List[MetricPoint] = Field(default_factory=list)
    error_patterns: List[str] = Field(default_factory=list)
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    resource_state: Dict[str, Any] = Field(default_factory=dict)
