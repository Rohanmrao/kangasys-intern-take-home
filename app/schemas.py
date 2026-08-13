from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceCreate(BaseModel):
    id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    type: str = Field(min_length=1, max_length=80)
    status: str = "active"
    unit: str = Field(min_length=1, max_length=30)
    normal_min: float | None = None
    normal_max: float | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"active", "inactive"}:
            raise ValueError("status must be 'active' or 'inactive'")
        return value

    def validate_range(self):
        if self.status == "active":
            if self.normal_min is None or self.normal_max is None:
                raise ValueError("active devices require normal_min and normal_max")
            if self.normal_min >= self.normal_max:
                raise ValueError("normal_min must be smaller than normal_max")
        elif self.normal_min is not None or self.normal_max is not None:
            raise ValueError("inactive devices must not have a normal range")


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    type: str | None = Field(default=None, min_length=1, max_length=80)
    status: str | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    normal_min: float | None = None
    normal_max: float | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in {"active", "inactive"}:
            raise ValueError("status must be 'active' or 'inactive'")
        return value


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str
    status: str
    unit: str
    normal_min: float | None
    normal_max: float | None


class ReadingCreate(BaseModel):
    value: float
    unit: str = Field(min_length=1, max_length=30)
    timestamp: datetime | None = None


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    value: float
    unit: str
    timestamp: datetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    reading_id: int
    timestamp: datetime
    message: str
    resolved: bool
