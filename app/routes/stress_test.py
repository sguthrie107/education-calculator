"""Stress test API routes for education Monte Carlo results."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..schemas import (
    EducationStressTestEnvelope,
    EducationStressTestRecalculateRequest,
)
from ..services.monte_carlo import (
    get_latest_stress_test_payload,
    run_stress_test,
    to_response_payload,
)

router = APIRouter(prefix="/api/stress-test")


def _run_stress_test_with_local_session(*, child_name: str, simulation_count: int, random_seed: int | None):
    db = SessionLocal()
    try:
        return run_stress_test(
            child_name=child_name,
            db=db,
            simulation_count=simulation_count,
            random_seed=random_seed,
        )
    finally:
        db.close()


@router.get("/{child_name}", response_model=EducationStressTestEnvelope)
def get_stress_test_result(child_name: str, db: Session = Depends(get_db)):
    """Get most recent stored stress test result for a child (without recalculating)."""
    try:
        latest = get_latest_stress_test_payload(child_name, db)
        return {"result": latest}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(exc)}",
        ) from exc


@router.post("/{child_name}/recalculate", response_model=EducationStressTestEnvelope)
async def recalculate_stress_test(
    child_name: str,
    body: EducationStressTestRecalculateRequest,
    db: Session = Depends(get_db),
):
    """Run and persist a new single-child 4-year college-fund stress test."""
    try:
        if db.bind and db.bind.dialect.name == "sqlite":
            result = run_stress_test(
                child_name=child_name,
                db=db,
                simulation_count=body.simulation_count,
                random_seed=body.random_seed,
            )
        else:
            result = await asyncio.to_thread(
                _run_stress_test_with_local_session,
                child_name=child_name,
                simulation_count=body.simulation_count,
                random_seed=body.random_seed,
            )
        return {"result": to_response_payload(result, child_name)}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(exc)}",
        ) from exc
