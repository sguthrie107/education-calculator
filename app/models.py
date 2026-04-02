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
