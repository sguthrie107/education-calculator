"""Pydantic models for request/response validation."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class BalanceCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    balance: float = Field(ge=0)
    notes: Optional[str] = None


class BalanceUpdate(BaseModel):
    balance: float = Field(ge=0)
    notes: Optional[str] = None


class BalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    year: int
    balance: float
    notes: Optional[str]
    recorded_at: str


class ProjectionPoint(BaseModel):
    year: int
    age: int
    balance: float
    phase: str
    contributions_ytd: float


class ChildProjectionResponse(BaseModel):
    child_name: str
    birth_year: int
    projected: list[ProjectionPoint]


class ComparisonResponse(BaseModel):
    child_name: str
    birth_year: int
    projected: list[ProjectionPoint]
    actual: list[dict]
    deltas: list[dict]
