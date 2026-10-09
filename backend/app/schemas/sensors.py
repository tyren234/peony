"""Sensor Pydantic schemas with UTC timezone formatting."""

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SensorInput(BaseModel):
    """Schema for registering a new sensor."""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=100)
    series_id: int = Field(..., alias="seriesId")


class SensorResponse(BaseModel):
    """Schema representing sensor information returned by the API."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: int
    name: str
    series_id: int = Field(..., alias="seriesId")
    created_at: datetime = Field(..., alias="createdAt")
    last_measurement_at: Optional[datetime] = Field(default=None, alias="lastMeasurementAt")

    @field_validator("created_at", "last_measurement_at", mode="before")
    @classmethod
    def ensure_utc_timestamps(cls, raw_timestamp_value: Any) -> Any:
        if isinstance(raw_timestamp_value, datetime) and raw_timestamp_value.tzinfo is None:
            return raw_timestamp_value.replace(tzinfo=timezone.utc)
        return raw_timestamp_value


class SensorCreatedResponse(SensorResponse):
    """Schema returned only once upon sensor registration, containing the plaintext API key."""
    api_key: str = Field(..., alias="apiKey", min_length=32)
