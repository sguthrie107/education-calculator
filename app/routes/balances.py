"""Balance management routes."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from ..database import get_db
from ..models import Child, Account529, ActualBalance
from ..schemas import BalanceCreate, BalanceUpdate, BalanceResponse
from ..sanitize import sanitize_name, sanitize_notes
from ..auth import is_editor

router = APIRouter(prefix="/api/balances")


@router.post("/{child_name}", response_model=BalanceResponse, status_code=status.HTTP_201_CREATED)
async def create_balance(child_name: str, balance_data: BalanceCreate, request: Request, db: Session = Depends(get_db)):
    """Create a new actual balance entry for a child's education account."""
    user = request.state.authenticated_user
    if not is_editor(user):
        raise HTTPException(status_code=403, detail="Only Steven and Alyssa can create balances")

    try:
        clean_name = sanitize_name(child_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    clean_notes = sanitize_notes(balance_data.notes)

    # Get or create child
    child = db.query(Child).filter(Child.name == clean_name).first()
    if not child:
        child = Child(name=clean_name)
        db.add(child)
        db.commit()
        db.refresh(child)

    # Get or create 529 account
    account = db.query(Account529).filter(Account529.child_id == child.id).first()
    if not account:
        account = Account529(child_id=child.id)
        db.add(account)
        db.commit()
        db.refresh(account)

    actual_balance = ActualBalance(
        account_id=account.id,
        year=balance_data.year,
        balance=balance_data.balance,
        notes=clean_notes,
    )

    try:
        db.add(actual_balance)
        db.commit()
        db.refresh(actual_balance)
        return actual_balance
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Balance for year {balance_data.year} already exists",
        )


@router.get("/{child_name}", response_model=list[BalanceResponse])
async def get_balances(child_name: str, db: Session = Depends(get_db)):
    """Get all actual balances for a child."""
    child = db.query(Child).filter(Child.name == child_name).first()
    if not child:
        return []

    balances = (
        db.query(ActualBalance)
        .join(Account529)
        .filter(Account529.child_id == child.id)
        .order_by(ActualBalance.year.desc())
        .all()
    )
    return balances


@router.put("/{balance_id}", response_model=BalanceResponse)
async def update_balance(balance_id: int, balance_data: BalanceUpdate, request: Request, db: Session = Depends(get_db)):
    """Update an existing balance entry."""
    user = request.state.authenticated_user
    if not is_editor(user):
        raise HTTPException(status_code=403, detail="Only Steven and Alyssa can update balances")

    balance = db.query(ActualBalance).filter(ActualBalance.id == balance_id).first()
    if not balance:
        raise HTTPException(status_code=404, detail="Balance not found")

    balance_changed = balance.balance != balance_data.balance
    balance.balance = balance_data.balance
    if balance_data.notes is not None:
        balance.notes = sanitize_notes(balance_data.notes)
    if balance_changed:
        balance.recorded_at = datetime.utcnow().isoformat()

    db.commit()
    db.refresh(balance)
    return balance


@router.delete("/{balance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_balance(balance_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a balance entry."""
    user = request.state.authenticated_user
    if not is_editor(user):
        raise HTTPException(status_code=403, detail="Only Steven and Alyssa can delete balances")
    balance = db.query(ActualBalance).filter(ActualBalance.id == balance_id).first()
    if not balance:
        raise HTTPException(status_code=404, detail="Balance not found")

    db.delete(balance)
    db.commit()
    return None
