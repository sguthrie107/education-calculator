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


class EducationStressTestRecalculateRequest(BaseModel):
    simulation_count: int = Field(default=10000, ge=5000, le=100000)
    random_seed: Optional[int] = Field(default=None, ge=0)


class EducationStressTestResponse(BaseModel):
    id: int
    child_name: str
    created_at: str
    simulation_count: int
    random_seed: Optional[int]
    mean_return_pct: float
    volatility_pct: float
    inflation_pct: float
    success_probability_pct: float
    rating_tier: int
    rating_grade: str
    rating_label: str
    p10_terminal_balance: float
    p50_terminal_balance: float
    p90_terminal_balance: float
    assumptions: dict


class EducationStressTestEnvelope(BaseModel):
    result: Optional[EducationStressTestResponse] = None
