"""Projection and comparison API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.comparison import get_comparison_data, get_all_children_comparison

router = APIRouter(prefix="/api")


@router.get("/comparison/{child_name}")
async def get_comparison(child_name: str, db: Session = Depends(get_db)):
    """Get projected vs actual balance comparison for a single child."""
    try:
        data = get_comparison_data(child_name, db)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/comparison-all")
async def get_all_comparisons(db: Session = Depends(get_db)):
    """Get projected balances for all children."""
    try:
        data = get_all_children_comparison(db)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
