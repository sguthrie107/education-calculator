"""Comparison service — merges projected and actual balances."""
from sqlalchemy.orm import Session

from ..models import Child, Account529, ActualBalance
from .projection import get_child_projection, get_all_projections
from .loans import build_household_student_loan_projection


def get_comparison_data(child_name: str, db: Session, base_year: int = 2026) -> dict:
    """Build comparison payload: projected vs actual with deltas.

    Returns:
        {
            "child_name": str,
            "birth_year": int,
            "projected": [...],
            "actual": [...],
            "deltas": [...]
        }
    """
    projection = get_child_projection(child_name, base_year=base_year)

    # Fetch actual balances from DB
    actual_by_year = {}
    child = db.query(Child).filter(Child.name == child_name).first()
    if child:
        account = (
            db.query(Account529)
            .filter(Account529.child_id == child.id)
            .first()
        )
        if account:
            balances = (
                db.query(ActualBalance)
                .filter(ActualBalance.account_id == account.id)
                .order_by(ActualBalance.year)
                .all()
            )
            for b in balances:
                actual_by_year[b.year] = {
                    "id": b.id,
                    "year": b.year,
                    "balance": b.balance,
                    "notes": b.notes,
                    "recorded_at": b.recorded_at,
                }

    # Build actual list aligned to projection years
    actual_list = []
    for pt in projection["projected"]:
        if pt["year"] in actual_by_year:
            actual_list.append(actual_by_year[pt["year"]])

    # Build deltas where we have both projected and actual
    projected_by_year = {p["year"]: p for p in projection["projected"]}
    deltas = []
    for year, act in sorted(actual_by_year.items()):
        proj = projected_by_year.get(year)
        if proj:
            diff = act["balance"] - proj["balance"]
            pct = (diff / proj["balance"] * 100) if proj["balance"] != 0 else 0.0
            deltas.append({
                "year": year,
                "age": proj["age"],
                "projected": proj["balance"],
                "actual": act["balance"],
                "delta": round(diff, 2),
                "delta_pct": round(pct, 2),
                "balance_ids": [act["id"]],
            })

    return {
        "child_name": projection["child_name"],
        "birth_year": projection["birth_year"],
        "inflation_rate_pct": projection.get("inflation_rate_pct", 3.0),
        "initial_investment_2026": projection.get("initial_investment_2026", 2500.0),
        "initial_investment_nominal": projection.get("initial_investment_nominal", 2500.0),
        "projected": projection["projected"],
        "actual": actual_list,
        "deltas": deltas,
    }


def get_all_children_comparison(db: Session, base_year: int = 2026) -> dict:
    """Get comparison data for all children."""
    all_projections = get_all_projections(base_year=base_year)
    children_data = []
    for proj in all_projections:
        comparison = get_comparison_data(proj["child_name"], db, base_year=base_year)
        children_data.append(comparison)
    household_loan = build_household_student_loan_projection(base_year=base_year)
    return {
        "children": children_data,
        "household_loan": household_loan,
    }
