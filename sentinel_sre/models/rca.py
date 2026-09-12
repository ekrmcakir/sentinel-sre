from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Hypothesis(BaseModel):
    id: str
    summary: str
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")
    evidence: List[str] = Field(default_factory=list)
    contributing_factors: List[str] = Field(default_factory=list)
    suggested_action_type: str
    suggested_action_params: Dict[str, Any] = Field(default_factory=dict)


class RootCauseAnalysis(BaseModel):
    analysis_id: str
    incident_id: str
    primary_hypothesis: Hypothesis
    alternative_hypotheses: List[Hypothesis] = Field(default_factory=list)
    diagnosed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reasoning_summary: str
    telemetry_summary: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
