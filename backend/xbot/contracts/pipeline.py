"""
xbot.contracts.pipeline: Universal DTOs for pipeline and task telemetry.
"""
from typing import Any, Literal
from pydantic import BaseModel, Field


class PipelineResult(BaseModel):
    """Normalized output DTO returned by Celery tasks and pipeline runners."""
    pipeline: str
    status: Literal["success", "partial_success", "failed", "skipped"]
    actions_executed: int = 0
    per_profile: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
