"""Monte Carlo stress testing for 529 college-fund payoff probability.

This service intentionally models one child account at a time and only the
4-year university path (direct_4yr) to match dashboard expectations.
"""

from __future__ import annotations

import json
import math
import random
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from lib.calculator import compute_blended_annual_return, get_child_config, get_phase_for_age, inflate_from_base_year
from .education_withdrawals import NC_COST_ASSUMPTIONS_2026
from ..models import Child, EducationStressTestResult

DEFAULT_SIMULATION_COUNT = 10000
MIN_SIMULATION_COUNT = 5000
MAX_SIMULATION_COUNT = 100000
DEFAULT_BASE_YEAR = 2026

# Keep rating semantics aligned with the retirement calculator.
RATING_BANDS = [
    {
        "tier": 5,
        "grade": "A",
        "label": "Fortress Outlook",
        "min_probability": 92.0,
    },
    {
        "tier": 4,
        "grade": "B",
        "label": "Strong Outlook",
        "min_probability": 85.0,
    },
    {
        "tier": 3,
        "grade": "C",
        "label": "Stable but Exposed",
        "min_probability": 75.0,
    },
    {
        "tier": 2,
        "grade": "D",
        "label": "Fragile Plan",
        "min_probability": 60.0,
    },
    {
        "tier": 1,
        "grade": "F",
        "label": "At Risk",
        "min_probability": 0.0,
    },
]


def _rating_for_probability(probability_pct: float) -> dict[str, Any]:
    for band in RATING_BANDS:
        if probability_pct >= band["min_probability"]:
            return band
    return RATING_BANDS[-1]


def _draw_annual_return(mean_return: float, volatility: float, shock: float) -> float:
    sigma = max(float(volatility), 1e-6)
    mu_log = math.log1p(float(mean_return)) - 0.5 * sigma * sigma
    simulated = math.exp(mu_log + sigma * float(shock)) - 1.0
    return max(simulated, -0.95)


def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    idx = (len(sorted_values) - 1) * max(0.0, min(1.0, q))
    lower = int(math.floor(idx))
    upper = int(math.ceil(idx))
    if lower == upper:
        return float(sorted_values[lower])
    weight = idx - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def _allocation_volatility(allocation: dict[str, Any]) -> float:
    # Reasonable defaults per asset class when explicit vol is not configured.
    ticker_volatility = {
        "VTSAX": 0.18,
        "VTIAX": 0.20,
        "VBTLX": 0.06,
    }
    total_weight = sum(float(item.get("pct", 0.0)) for item in allocation.values())
    if total_weight <= 0:
        return 0.12

    weighted_variance = 0.0
    for item in allocation.values():
        weight = float(item.get("pct", 0.0)) / total_weight
        ticker = str(item.get("ticker", "")).upper()
        sigma = ticker_volatility.get(ticker, 0.14)
        weighted_variance += (weight * sigma) ** 2

    return math.sqrt(max(weighted_variance, 1e-8))


def _monthly_contribution_for_age(child_config: dict[str, Any], age: int) -> float:
    base = float(child_config.get("monthly_contribution", 200.0))
    growth = float(child_config.get("annual_contribution_growth_rate", 0.03))
    return base * ((1.0 + growth) ** max(age, 0))


def _phase_moments_for_age(child_config: dict[str, Any], age: int) -> tuple[float, float]:
    phase_key = get_phase_for_age(age)
    allocation = (
        child_config.get("phases", {})
        .get(phase_key, {})
        .get("allocation", {})
    )
    mean_return = compute_blended_annual_return(allocation) if allocation else 0.06
    volatility = _allocation_volatility(allocation)
    return mean_return, volatility


def _simulate_single_trial(
    *,
    child_config: dict[str, Any],
    simulation_start_year: int,
    base_year: int,
    inflation_rate: float,
    rng: random.Random,
) -> tuple[bool, float]:
    birth_year = int(child_config["birth_year"])
    college_start_year = birth_year + 18
    college_end_year = college_start_year + 3

    start_balance = float(
        inflate_from_base_year(
            amount_2026_dollars=float(child_config.get("initial_investment", 2500.0)),
            base_year=base_year,
            target_year=birth_year,
            annual_inflation_rate=inflation_rate,
        )
    )

    balance = max(start_balance, 0.0)
    failed = False

    for year in range(birth_year, college_end_year + 1):
        age = year - birth_year
        mean_return, volatility = _phase_moments_for_age(child_config, age)
        if year < simulation_start_year:
            annual_return = mean_return
        else:
            annual_return = _draw_annual_return(mean_return, volatility, rng.gauss(0.0, 1.0))

        annual_contribution = 0.0
        if age <= 20:
            annual_contribution = _monthly_contribution_for_age(child_config, age) * 12.0

        balance = max(balance * (1.0 + annual_return), 0.0)
        balance += annual_contribution

        if year >= college_start_year:
            tuition = inflate_from_base_year(
                NC_COST_ASSUMPTIONS_2026["university"]["tuition"],
                base_year,
                year,
                inflation_rate,
            )
            room_board = inflate_from_base_year(
                NC_COST_ASSUMPTIONS_2026["university"]["room_board"],
                base_year,
                year,
                inflation_rate,
            )
            annual_cost = tuition + room_board
            if balance >= annual_cost:
                balance -= annual_cost
            else:
                failed = True
                balance = 0.0
                break

    return (not failed), round(balance, 2)


def _safe_parse_assumptions(raw_assumptions: str | None) -> dict[str, Any]:
    if not raw_assumptions:
        return {}
    try:
        parsed = json.loads(raw_assumptions)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _build_response_payload(result: EducationStressTestResult, child_name: str) -> dict[str, Any]:
    return {
        "id": result.id,
        "child_name": child_name,
        "created_at": result.created_at,
        "simulation_count": result.simulation_count,
        "random_seed": result.random_seed,
        "mean_return_pct": round(result.mean_return_pct, 4),
        "volatility_pct": round(result.volatility_pct, 4),
        "inflation_pct": round(result.inflation_pct, 4),
        "success_probability_pct": round(result.success_probability_pct, 2),
        "rating_tier": result.rating_tier,
        "rating_grade": result.rating_grade,
        "rating_label": result.rating_label,
        "p10_terminal_balance": round(result.p10_terminal_balance, 2),
        "p50_terminal_balance": round(result.p50_terminal_balance, 2),
        "p90_terminal_balance": round(result.p90_terminal_balance, 2),
        "assumptions": _safe_parse_assumptions(result.assumptions_json),
    }


def get_latest_stress_test(child_name: str, db: Session) -> EducationStressTestResult | None:
    child = db.query(Child).filter(Child.name == child_name).first()
    if not child:
        raise ValueError(f"Child '{child_name}' not found")

    return (
        db.query(EducationStressTestResult)
        .filter(EducationStressTestResult.child_id == child.id)
        .order_by(EducationStressTestResult.id.desc())
        .first()
    )


def get_latest_stress_test_payload(child_name: str, db: Session) -> dict[str, Any] | None:
    latest = get_latest_stress_test(child_name, db)
    if not latest:
        return None
    return _build_response_payload(latest, child_name)


def run_stress_test(
    *,
    child_name: str,
    db: Session,
    simulation_count: int = DEFAULT_SIMULATION_COUNT,
    random_seed: int | None = None,
    base_year: int = DEFAULT_BASE_YEAR,
) -> EducationStressTestResult:
    if simulation_count < MIN_SIMULATION_COUNT or simulation_count > MAX_SIMULATION_COUNT:
        raise ValueError(
            f"simulation_count must be between {MIN_SIMULATION_COUNT} and {MAX_SIMULATION_COUNT}"
        )

    child = db.query(Child).filter(Child.name == child_name).first()
    if not child:
        raise ValueError(f"Child '{child_name}' not found")

    child_config = get_child_config(child_name)
    inflation_rate = float(child_config.get("inflation_rate", 0.03))

    birth_year = int(child_config["birth_year"])
    current_year = datetime.now().year
    simulation_start_year = max(current_year, birth_year)

    # Weighted moments based on current age phase for compact dashboard display.
    display_age = max(0, simulation_start_year - birth_year)
    mean_return, volatility = _phase_moments_for_age(child_config, display_age)

    rng = random.Random(random_seed)
    successes = 0
    terminal_balances: list[float] = []

    for _ in range(simulation_count):
        success, terminal_balance = _simulate_single_trial(
            child_config=child_config,
            simulation_start_year=simulation_start_year,
            base_year=base_year,
            inflation_rate=inflation_rate,
            rng=rng,
        )
        if success:
            successes += 1
        terminal_balances.append(float(terminal_balance))

    terminal_balances.sort()
    success_probability_pct = (successes / simulation_count) * 100.0
    rating = _rating_for_probability(success_probability_pct)

    assumptions = {
        "success_definition": "529 covers full annual cost for all 4 university years (direct_4yr)",
        "child_name": child_name,
        "base_year": base_year,
        "simulation_start_year": simulation_start_year,
        "college_start_year": birth_year + 18,
        "college_end_year": birth_year + 21,
        "inflation_rate": inflation_rate,
        "path": "direct_4yr",
        "notes": "Single-fund stress test only; children are modeled independently under matching strategy assumptions.",
    }

    row = EducationStressTestResult(
        child_id=child.id,
        simulation_count=simulation_count,
        random_seed=random_seed,
        mean_return_pct=mean_return * 100.0,
        volatility_pct=volatility * 100.0,
        inflation_pct=inflation_rate * 100.0,
        success_probability_pct=success_probability_pct,
        rating_tier=int(rating["tier"]),
        rating_grade=str(rating["grade"]),
        rating_label=str(rating["label"]),
        p10_terminal_balance=_percentile(terminal_balances, 0.10),
        p50_terminal_balance=_percentile(terminal_balances, 0.50),
        p90_terminal_balance=_percentile(terminal_balances, 0.90),
        assumptions_json=json.dumps(assumptions),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_response_payload(result: EducationStressTestResult, child_name: str) -> dict[str, Any]:
    return _build_response_payload(result, child_name)
