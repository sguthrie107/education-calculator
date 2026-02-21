"""Projection service — wraps the calculation engine for the web layer."""
import sys
from pathlib import Path

# Add parent directory to path so lib is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.calculator import load_children_config, get_child_config, project_529_account


def get_child_projection(child_name: str, base_year: int = 2026) -> dict:
    """Get projected 529 balances for a single child.

    Returns:
        {
            "child_name": str,
            "birth_year": int,
            "projected": [
                {"year": int, "age": int, "balance": float, "phase": str, "contributions_ytd": float},
                ...
            ]
        }
    """
    config = get_child_config(child_name)
    rows = project_529_account(config, base_year=base_year)

    projected = []
    initial_nominal = rows[0]["initial_investment_nominal"] if rows else config.get("initial_investment", 2500.0)
    initial_2026 = rows[0]["initial_investment_2026"] if rows else config.get("initial_investment", 2500.0)
    inflation_rate_pct = rows[0]["inflation_rate_pct"] if rows else 3.0

    cumulative_contributions = initial_nominal
    for row in rows:
        cumulative_contributions += row["contributions"]
        projected.append({
            "year": row["year"],
            "age": row["age"],
            "balance": row["ending_balance"],
            "phase": row["phase"],
            "phase_key": row["phase_key"],
            "contributions_ytd": round(cumulative_contributions, 2),
        })

    return {
        "child_name": config["name"],
        "birth_year": config["birth_year"],
        "inflation_rate_pct": inflation_rate_pct,
        "initial_investment_2026": initial_2026,
        "initial_investment_nominal": initial_nominal,
        "projected": projected,
    }


def get_all_projections(base_year: int = 2026) -> list[dict]:
    """Get projected balances for all children."""
    children = load_children_config()
    results = []
    for child in children:
        results.append(get_child_projection(child["name"], base_year=base_year))
    return results
