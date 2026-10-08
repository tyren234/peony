from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


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
