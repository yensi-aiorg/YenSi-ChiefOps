"""
Alert models for the ChiefOps monitoring and notification system.

Alerts are configured through conversation (e.g. "Alert me if Project Alpha's
health score drops below 60") or by the system as defaults. Each alert
monitors a condition against a threshold and tracks triggered events.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.base import MongoBaseModel, generate_uuid, utc_now


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AlertType(str, Enum):
    """Category of alert being monitored."""

    SPRINT_METRIC = "sprint_metric"
    COMMUNICATION_PATTERN = "communication_pattern"
    TIMELINE_RISK = "timeline_risk"
    CAPACITY_UTILIZATION = "capacity_utilization"


class AlertOperator(str, Enum):
    """Comparison operator for threshold evaluation."""

    LT = "lt"
    GT = "gt"
    LTE = "lte"
    GTE = "gte"
    EQ = "eq"


class AlertSeverity(str, Enum):
    """Severity level of a triggered alert."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# ---------------------------------------------------------------------------
# Primary model: Alert
# ---------------------------------------------------------------------------


class Alert(MongoBaseModel):
    """
    A configured alert with threshold monitoring. Alerts fire when a
    monitored metric crosses a threshold. The COO can create, modify,
    activate, or deactivate alerts through conversation.

    MongoDB collection: ``alerts``
    """

    alert_id: str = Field(
        default_factory=generate_uuid,
        description="Unique alert identifier (UUID v4).",
    )
    alert_type: AlertType = Field(
        ...,
        description="Category of alert.",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable alert name.",
    )
    description: str = Field(
        default="",
        max_length=1000,
        description="Detailed description of what this alert monitors.",
    )
    metric: str = Field(
        ...,
        description="The metric being monitored (e.g. 'health_score', 'completion_rate', 'blocker_count').",
    )
    operator: AlertOperator = Field(
        ...,
        description="Comparison operator for threshold evaluation.",
    )
    threshold: float = Field(
        ...,
        description="Numeric threshold value to compare against.",
    )
    active: bool = Field(
        default=True,
        description="Whether this alert is actively being evaluated.",
    )


# ---------------------------------------------------------------------------
# Primary model: AlertTriggered
# ---------------------------------------------------------------------------


class AlertTriggered(MongoBaseModel):
    """
    Record of an alert being triggered. Created when a monitored metric
    crosses the configured threshold. Includes the current value at time
    of trigger, the threshold it crossed, and severity assessment.

    MongoDB collection: ``alerts_triggered``
    """

    trigger_id: str = Field(
        default_factory=generate_uuid,
        description="Unique trigger event identifier (UUID v4).",
    )
    alert_id: str = Field(
        ...,
        description="References the alert_id that was triggered.",
    )
    current_value: float = Field(
        ...,
        description="The metric value at the time the alert was triggered.",
    )
    threshold: float = Field(
        ...,
        description="The threshold value that was crossed.",
    )
    message: str = Field(
        ...,
        description="Human-readable alert message describing the trigger.",
    )
    severity: AlertSeverity = Field(
        default=AlertSeverity.WARNING,
        description="Severity level of this triggered alert.",
    )
    acknowledged: bool = Field(
        default=False,
        description="Whether the COO has acknowledged this alert.",
    )
    triggered_at: datetime = Field(
        default_factory=utc_now,
        description="When the alert was triggered.",
    )
