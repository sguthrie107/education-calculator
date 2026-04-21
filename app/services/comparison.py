"""Comparison service — merges projected and actual balances."""
from collections import defaultdict

from sqlalchemy.orm import Session

from ..models import Child, Account529, ActualBalance, ActualLoanBalance
from .projection import get_child_projection, get_all_projections
from .loans import build_household_student_loan_projection
from .education_withdrawals import build_child_withdrawal_scenarios
from lib.calculator import get_child_config


def _load_actual_balances_for_children(db: Session, child_names: list[str]) -> dict[str, dict[int, dict]]:
    if not child_names:
        return {}

    rows = (
        db.query(
            Child.name.label("child_name"),
            ActualBalance.id.label("id"),
            ActualBalance.year.label("year"),
            ActualBalance.balance.label("balance"),
            ActualBalance.notes.label("notes"),
            ActualBalance.recorded_at.label("recorded_at"),
        )
        .join(Account529, Account529.child_id == Child.id)
        .join(ActualBalance, ActualBalance.account_id == Account529.id)
        .filter(Child.name.in_(child_names))
        .order_by(ActualBalance.year)
        .all()
    )

    actual_by_child: dict[str, dict[int, dict]] = defaultdict(dict)
    for row in rows:
        actual_by_child[row.child_name][int(row.year)] = {
            "id": int(row.id),
            "year": int(row.year),
            "balance": float(row.balance),
            "notes": row.notes,
            "recorded_at": row.recorded_at,
        }

    return actual_by_child


def get_comparison_data(
    child_name: str,
    db: Session,
    base_year: int = 2026,
    precomputed_projection: dict | None = None,
    preloaded_actual_by_year: dict[int, dict] | None = None,
) -> dict:
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
    projection = precomputed_projection or get_child_projection(child_name, base_year=base_year)
    child_config = get_child_config(child_name)
    withdrawal_scenarios = build_child_withdrawal_scenarios(
        child_config=child_config,
        projected_rows=projection.get("projected", []),
        base_year=base_year,
        covered_ratio=0.9,
    )

    # Fetch actual balances from DB
    actual_by_year = preloaded_actual_by_year or {}
    if preloaded_actual_by_year is None:
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
        "withdrawal_scenarios": withdrawal_scenarios,
        "actual": actual_list,
        "deltas": deltas,
    }


def _load_actual_loan_balances(db: Session) -> list[dict]:
    """Load all actual loan balance entries ordered by year/month."""
    rows = (
        db.query(ActualLoanBalance)
        .order_by(ActualLoanBalance.year, ActualLoanBalance.month)
        .all()
    )
    return [
        {
            "id": int(row.id),
            "year": int(row.year),
            "month": int(row.month),
            "balance": float(row.balance),
            "notes": row.notes,
            "recorded_at": row.recorded_at,
            "fractional_year": round(row.year + (row.month - 1) / 12.0, 4),
        }
        for row in rows
    ]


def get_all_children_comparison(db: Session, base_year: int = 2026) -> dict:
    """Get comparison data for all children."""
    all_projections = get_all_projections(base_year=base_year)
    child_names = [proj["child_name"] for proj in all_projections]
    actual_by_child = _load_actual_balances_for_children(db, child_names)
    children_data = []
    for proj in all_projections:
        child_name = proj["child_name"]
        comparison = get_comparison_data(
            child_name,
            db,
            base_year=base_year,
            precomputed_projection=proj,
            preloaded_actual_by_year=actual_by_child.get(child_name, {}),
        )
        children_data.append(comparison)
    household_loan = build_household_student_loan_projection(base_year=base_year)
    actual_loan_balances = _load_actual_loan_balances(db)
    household_loan["actual_balances"] = actual_loan_balances
    return {
        "children": children_data,
        "household_loan": household_loan,
    }
