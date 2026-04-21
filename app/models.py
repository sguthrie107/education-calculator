"""SQLAlchemy ORM models."""
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship


def _utc_now_iso() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Child(Base):
    """A child with a 529 education savings account."""
    __tablename__ = "children"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(String, nullable=False, default=_utc_now_iso)

    accounts = relationship("Account529", back_populates="child", cascade="all, delete-orphan")
    stress_test_results = relationship("EducationStressTestResult", back_populates="child", cascade="all, delete-orphan")


class Account529(Base):
    """A 529 education savings account linked to a child."""
    __tablename__ = "accounts_529"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    provider = Column(String, default="Vanguard")

    child = relationship("Child", back_populates="accounts")
    actual_balances = relationship("ActualBalance", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("child_id", name="uq_child_account"),
    )


class ActualBalance(Base):
    """Yearly actual balance snapshot for a 529 account."""
    __tablename__ = "actual_balances"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts_529.id"), nullable=False)
    year = Column(Integer, nullable=False)
    balance = Column(Float, nullable=False)
    notes = Column(String)
    recorded_at = Column(String, nullable=False, default=_utc_now_iso)

    account = relationship("Account529", back_populates="actual_balances")

    __table_args__ = (
        UniqueConstraint("account_id", "year", name="uq_account_year"),
        CheckConstraint("balance >= 0", name="ck_balance_positive"),
    )


class ActualLoanBalance(Base):
    """Monthly actual loan balance snapshot for the household student loan."""
    __tablename__ = "actual_loan_balances"

    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    balance = Column(Float, nullable=False)
    notes = Column(String)
    recorded_at = Column(String, nullable=False, default=_utc_now_iso)

    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_loan_year_month"),
        CheckConstraint("balance >= 0", name="ck_loan_balance_positive"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_loan_month_range"),
    )


class EducationStressTestResult(Base):
    """Stored Monte Carlo result for one child's 4-year college payoff probability."""

    __tablename__ = "education_stress_test_results"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    created_at = Column(String, nullable=False, default=_utc_now_iso)
    simulation_count = Column(Integer, nullable=False)
    random_seed = Column(Integer, nullable=True)
    mean_return_pct = Column(Float, nullable=False)
    volatility_pct = Column(Float, nullable=False)
    inflation_pct = Column(Float, nullable=False)
    success_probability_pct = Column(Float, nullable=False)
    rating_tier = Column(Integer, nullable=False)
    rating_grade = Column(String, nullable=False)
    rating_label = Column(String, nullable=False)
    p10_terminal_balance = Column(Float, nullable=False)
    p50_terminal_balance = Column(Float, nullable=False)
    p90_terminal_balance = Column(Float, nullable=False)
    assumptions_json = Column(String, nullable=False, default="{}")

    child = relationship("Child", back_populates="stress_test_results")

    __table_args__ = (
        CheckConstraint("simulation_count >= 5000", name="ck_edu_stress_simulation_count"),
        CheckConstraint("success_probability_pct >= 0 AND success_probability_pct <= 100", name="ck_edu_stress_success_probability_range"),
        CheckConstraint("rating_tier >= 1 AND rating_tier <= 5", name="ck_edu_stress_rating_tier_range"),
    )
