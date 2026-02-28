"""Education withdrawal scenario modeling for 529 usage."""

from __future__ import annotations

from typing import Any

from lib.calculator import compute_blended_annual_return

BASE_YEAR = 2026

NC_COST_ASSUMPTIONS_2026 = {
    "university": {
        "school": "UNC Chapel Hill",
        "tuition": 9100.0,
        "room_board": 14300.0,
    },
    "community_college": {
        "school": "Central Piedmont Community College",
        "tuition": 2800.0,
        "room_board": 8200.0,
    },
}

SCENARIO_DEFINITIONS = {
    "direct_4yr": {
        "label": "UNC Chapel Hill (4-Year)",
        "path": ["university", "university", "university", "university"],
    },
    "blended_2plus2": {
        "label": "CPCC (2-Year) + UNC Chapel Hill (2-Year)",
        "path": ["community_college", "community_college", "university", "university"],
    },
}


def _inflate(amount: float, inflation_rate: float, from_year: int, to_year: int) -> float:
    year_offset = max(0, to_year - from_year)
    return amount * ((1 + inflation_rate) ** year_offset)


def build_child_withdrawal_scenarios(
    child_config: dict[str, Any],
    projected_rows: list[dict[str, Any]],
    base_year: int = BASE_YEAR,
    covered_ratio: float = 0.9,
) -> dict[str, Any]:
    """Build NC public-college cost withdrawal scenarios for one child.

    Each scenario projects annual education costs and applies 529 withdrawals
    beginning at age 18 with no additional contributions.
    """
    birth_year = int(child_config.get("birth_year", base_year))
    inflation_rate = float(child_config.get("inflation_rate", 0.03))

    phase_3_allocation = (
        child_config.get("phases", {})
        .get("phase_3", {})
        .get("allocation", {})
    )
    annual_return = compute_blended_annual_return(phase_3_allocation) if phase_3_allocation else 0.06

    projected_by_year = {int(r.get("year", 0)): r for r in projected_rows}
    contributions_ytd_by_year = {
        int(r.get("year", 0)): float(r.get("contributions_ytd", 0.0))
        for r in projected_rows
        if int(r.get("year", 0)) > 0
    }

    annual_contribution_by_year: dict[int, float] = {}
    for year in sorted(contributions_ytd_by_year.keys()):
        prev = contributions_ytd_by_year.get(year - 1, 0.0)
        annual_contribution_by_year[year] = max(contributions_ytd_by_year[year] - prev, 0.0)

    college_start_year = birth_year + 18
    contribution_stop_year = birth_year + 20

    start_snapshot = projected_by_year.get(college_start_year)
    if start_snapshot:
        starting_balance = float(start_snapshot.get("balance", 0.0))
    elif projected_rows:
        starting_balance = float(projected_rows[-1].get("balance", 0.0))
    else:
        starting_balance = 0.0

    scenarios: dict[str, Any] = {}
    for scenario_key, scenario_info in SCENARIO_DEFINITIONS.items():
        path = scenario_info["path"]

        running_balance = max(starting_balance, 0.0)
        yearly_costs = []
        balance_timeline = [{"year": float(college_start_year), "balance": round(running_balance, 2)}]

        total_cost = 0.0
        target_covered_total = 0.0
        total_paid_by_529 = 0.0

        for idx, school_type in enumerate(path):
            year = college_start_year + idx
            school_year = idx + 1
            cost_assumption = NC_COST_ASSUMPTIONS_2026[school_type]

            tuition = _inflate(cost_assumption["tuition"], inflation_rate, base_year, year)
            room_board = _inflate(cost_assumption["room_board"], inflation_rate, base_year, year)
            annual_cost = tuition + room_board

            target_covered = annual_cost * covered_ratio
            annual_contribution = annual_contribution_by_year.get(year, 0.0) if year <= contribution_stop_year else 0.0
            balance_after_growth = (running_balance * (1 + annual_return)) + annual_contribution
            paid_by_529 = min(target_covered, balance_after_growth)
            ending_balance = max(balance_after_growth - paid_by_529, 0.0)

            total_cost += annual_cost
            target_covered_total += target_covered
            total_paid_by_529 += paid_by_529

            yearly_costs.append(
                {
                    "year": year,
                    "school_year": school_year,
                    "school_type": school_type,
                    "tuition": round(tuition, 2),
                    "room_board": round(room_board, 2),
                    "annual_cost": round(annual_cost, 2),
                    "target_covered_by_529": round(target_covered, 2),
                    "paid_by_529": round(paid_by_529, 2),
                    "remaining_cost": round(max(annual_cost - paid_by_529, 0.0), 2),
                    "annual_contribution": round(annual_contribution, 2),
                    "starting_balance": round(running_balance, 2),
                    "ending_balance": round(ending_balance, 2),
                }
            )

            running_balance = ending_balance
            balance_timeline.append({"year": float(year + 1), "balance": round(ending_balance, 2)})

        scenarios[scenario_key] = {
            "key": scenario_key,
            "label": scenario_info["label"],
            "covered_ratio": covered_ratio,
            "annual_return_assumption": round(annual_return, 6),
            "college_start_year": college_start_year,
            "yearly_costs": yearly_costs,
            "balance_timeline": balance_timeline,
            "summary": {
                "starting_balance": round(starting_balance, 2),
                "ending_balance": round(running_balance, 2),
                "total_cost": round(total_cost, 2),
                "target_covered_by_529": round(target_covered_total, 2),
                "paid_by_529": round(total_paid_by_529, 2),
                "remaining_cost": round(max(total_cost - total_paid_by_529, 0.0), 2),
                "percent_paid_by_529": round((total_paid_by_529 / total_cost * 100.0), 2) if total_cost > 0 else 0.0,
            },
        }

    return {
        "state": "NC",
        "base_year": base_year,
        "inflation_rate": inflation_rate,
        "covered_ratio": covered_ratio,
        "assumptions_2026": NC_COST_ASSUMPTIONS_2026,
        "scenarios": scenarios,
    }
