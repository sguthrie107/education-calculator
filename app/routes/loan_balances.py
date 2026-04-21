"""Household student loan actual balance management routes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ActualLoanBalance
from ..schemas import LoanBalanceCreate, LoanBalanceUpdate, LoanBalanceResponse
from ..sanitize import sanitize_notes
from ..auth import is_editor

router = APIRouter(prefix="/api/loan-balances")

MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


@router.post("", response_model=LoanBalanceResponse, status_code=status.HTTP_201_CREATED)
async def create_loan_balance(
    balance_data: LoanBalanceCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Record an actual loan balance for a given month/year."""
    user = request.state.authenticated_user
    if not is_editor(user):
        raise HTTPException(status_code=403, detail="Only Steven and Alyssa can create loan balances")

    clean_notes = sanitize_notes(balance_data.notes)

    entry = ActualLoanBalance(
        year=balance_data.year,
        month=balance_data.month,
        balance=balance_data.balance,
        notes=clean_notes,
    )

    try:
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except IntegrityError:
        db.rollback()
        month_name = MONTH_NAMES[balance_data.month]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Loan balance for {month_name} {balance_data.year} already exists",
        )


@router.get("", response_model=list[LoanBalanceResponse])
async def get_loan_balances(db: Session = Depends(get_db)):
    """Get all recorded actual loan balances, ordered by most recent first."""
    entries = (
        db.query(ActualLoanBalance)
        .order_by(ActualLoanBalance.year.desc(), ActualLoanBalance.month.desc())
        .all()
    )
    return entries


@router.put("/{balance_id}", response_model=LoanBalanceResponse)
async def update_loan_balance(
    balance_id: int,
    balance_data: LoanBalanceUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update an existing loan balance entry."""
    user = request.state.authenticated_user
    if not is_editor(user):
        raise HTTPException(status_code=403, detail="Only Steven and Alyssa can update loan balances")

    entry = db.query(ActualLoanBalance).filter(ActualLoanBalance.id == balance_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Loan balance not found")

    balance_changed = entry.balance != balance_data.balance
    entry.balance = balance_data.balance
    if balance_data.notes is not None:
        entry.notes = sanitize_notes(balance_data.notes)
    if balance_changed:
        entry.recorded_at = datetime.now(timezone.utc).isoformat()

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{balance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_loan_balance(
    balance_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a loan balance entry."""
    user = request.state.authenticated_user
    if not is_editor(user):
        raise HTTPException(status_code=403, detail="Only Steven and Alyssa can delete loan balances")

    entry = db.query(ActualLoanBalance).filter(ActualLoanBalance.id == balance_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Loan balance not found")

    db.delete(entry)
    db.commit()
    return None
