"""
Base model for all MongoDB document models in ChiefOps.

Provides MongoBaseModel with automatic created_at/updated_at timestamps,
UUID generation helpers, and Pydantic v2 configuration for MongoDB compatibility.
"""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def generate_uuid() -> str:
    """Generate a new UUID v4 string for use as an application-level identifier."""
    return str(uuid4())


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


class MongoBaseModel(BaseModel):
    """
    Base model for all MongoDB documents.

    Provides:
    - Automatic created_at and updated_at timestamps (UTC).
    - Pydantic v2 configuration for MongoDB compatibility:
      - populate_by_name: allows field population by alias or field name.
      - arbitrary_types_allowed: permits Motor/PyMongo types.
      - ser_json_timedelta: serializes timedeltas as ISO 8601 strings.
      - from_attributes: supports ORM-style attribute access.
    """

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "ser_json_timedelta": "iso8601",
        "from_attributes": True,
        "json_schema_extra": {
            "description": "ChiefOps MongoDB document base model."
        },
    }

    created_at: datetime = Field(
        default_factory=utc_now,
        description="Document creation timestamp (UTC).",
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        description="Last modification timestamp (UTC).",
    )
