"""Onboarding profile and dashboard configuration schemas."""
from typing import Any
from pydantic import BaseModel, Field

class OnboardingRequest(BaseModel):
    risk_profile: str = Field(pattern="^(conservative|aggressive)$")
    investment_horizon: str = Field(pattern="^(short|long)$")
    widgets: list[str] = Field(default_factory=list)

class DashboardResponse(BaseModel):
    email: str
    risk_profile: str | None
    investment_horizon: str | None
    widgets: list[str]

class AlertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    condition: dict[str, Any] = Field(min_length=1)
    enabled: bool = True

class AlertUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    condition: dict[str, Any] | None = Field(default=None, min_length=1)
    enabled: bool | None = None

class AlertResponse(AlertRequest):
    id: int
    model_config = {"from_attributes": True}
