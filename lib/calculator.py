"""529 projection calculation engine.

Pure financial math — no database, no HTTP, no UI.
Takes child configuration and returns year-by-year projected balances
with phase-aware allocation switching.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_ANNUAL_INFLATION_RATE = 0.03

# Phase age boundaries (inclusive upper bounds)
PHASE_BOUNDARIES = [
    ("phase_1", 0, 12),
    ("phase_2", 13, 17),
    ("phase_3", 18, 20),
]


def load_children_config() -> list[dict]:
    """Load all children from children.json."""
    children_file = DATA_DIR / "children.json"
    with open(children_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("children", [])


def get_child_config(child_name: str) -> dict:
    """Load configuration for a single child by name."""
    for child in load_children_config():
        if child["name"] == child_name:
            return child
    raise ValueError(f"Child '{child_name}' not found in children.json")


def get_phase_for_age(age: int) -> str:
    """Return the phase key (phase_1, phase_2, phase_3) for a given age."""
    for phase_key, start_age, end_age in PHASE_BOUNDARIES:
        if start_age <= age <= end_age:
            return phase_key
    return "phase_3"


def compute_blended_annual_return(allocation: dict) -> float:
    """Compute the weighted-average annual return for a phase allocation.

    Each allocation entry has 'pct' (weight) and 'expected_annual_return'.
    """
    blended = 0.0
    for _asset, info in allocation.items():
        blended += info["pct"] * info["expected_annual_return"]
    return blended


def inflate_from_base_year(
    amount_2026_dollars: float,
    base_year: int,
    target_year: int,
    annual_inflation_rate: float = DEFAULT_ANNUAL_INFLATION_RATE,
) -> float:
    """Convert a base-year amount into nominal dollars at target_year.

    Example: $2,500 in 2026 dollars becomes $2,500 * (1.03^3) for 2029.
    """
    year_offset = max(0, target_year - base_year)
    return amount_2026_dollars * ((1 + annual_inflation_rate) ** year_offset)


def project_529_account(child_config: dict, base_year: int = 2026) -> list[dict]:
    """Run the full year-by-year projection for a single 529 account.

    Returns a list of dicts, one per year from birth_year to birth_year + 20:
        {
            "year": int,
            "age": int,
            "phase": str,          # e.g. "Aggressive Growth (Age 0-12)"
            "phase_key": str,      # e.g. "phase_1"
            "annual_return_pct": float,
            "beginning_balance": float,
            "contributions": float,
            "growth": float,
            "ending_balance": float,
            "allocation": dict,    # the raw allocation block
        }

    The simulation works on a monthly basis internally for accuracy,
    then outputs annual snapshots.
    """
    birth_year = child_config["birth_year"]
    initial_investment_2026 = child_config.get("initial_investment", 2500.0)
    inflation_rate = child_config.get("inflation_rate", DEFAULT_ANNUAL_INFLATION_RATE)
    initial_investment_nominal = inflate_from_base_year(
        amount_2026_dollars=initial_investment_2026,
        base_year=base_year,
        target_year=birth_year,
        annual_inflation_rate=inflation_rate,
    )
    starting_monthly_contribution = child_config.get("monthly_contribution", 200.0)
    phases = child_config["phases"]

    rows = []
    balance = initial_investment_nominal

    # Project from age 0 (birth_year) through age 20 (birth_year + 20)
    for age in range(0, 21):
        year = birth_year + age
        monthly_contribution = starting_monthly_contribution + (age * 5.0)
        phase_key = get_phase_for_age(age)
        phase_info = phases[phase_key]
        allocation = phase_info["allocation"]
        annual_return = compute_blended_annual_return(allocation)
        monthly_return = (1 + annual_return) ** (1 / 12) - 1

        beginning_balance = balance
        total_contributions = 0.0

        # Month-by-month simulation for this year
        # Age 0, year = birth_year: initial investment already in, start contributions month 1
        for month in range(12):
            # Apply monthly growth on existing balance
            balance = balance * (1 + monthly_return)
            # Add monthly contribution
            balance += monthly_contribution
            total_contributions += monthly_contribution

        growth = balance - beginning_balance - total_contributions

        rows.append({
            "year": year,
            "age": age,
            "phase": phase_info["name"],
            "phase_key": phase_key,
            "inflation_rate_pct": round(inflation_rate * 100, 2),
            "initial_investment_2026": round(initial_investment_2026, 2),
            "initial_investment_nominal": round(initial_investment_nominal, 2),
            "annual_return_pct": round(annual_return * 100, 2),
            "beginning_balance": round(beginning_balance, 2),
            "contributions": round(total_contributions, 2),
            "growth": round(growth, 2),
            "ending_balance": round(balance, 2),
            "allocation": allocation,
        })

    return rows
