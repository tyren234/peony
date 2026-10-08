from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class SeriesInput(BaseModel):
    """Schema for creating or updating a measurement series."""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=100)
    min_value: float = Field(..., alias="minValue")
    max_value: float = Field(..., alias="maxValue")
    color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None
    unit: Optional[str] = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_min_value_strictly_less_than_max_value(self) -> "SeriesInput":
        if self.min_value >= self.max_value:
            raise ValueError("minValue must be strictly less than maxValue")
        return self


class SeriesResponse(SeriesInput):
    """Schema representing a measurement series returned by the API."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: int
