"""Measurement Pydantic schemas with UTC timezone formatting."""

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class MeasurementInput(BaseModel):
    """Schema for submitting telemetry measurement from sensor."""
    model_config = ConfigDict(populate_by_name=True)

    value: float
    timestamp: Optional[datetime] = None


class MeasurementResponse(BaseModel):
    """Schema for telemetry measurement returned by the API."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: int
    series_id: int = Field(..., alias="seriesId")
    sensor_id: Optional[int] = Field(default=None, alias="sensorId")
    value: float
    timestamp: datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc_timestamp(cls, raw_timestamp_value: Any) -> Any:
        if isinstance(raw_timestamp_value, datetime) and raw_timestamp_value.tzinfo is None:
            return raw_timestamp_value.replace(tzinfo=timezone.utc)
        return raw_timestamp_value
