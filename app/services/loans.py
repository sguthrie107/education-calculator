"""Household student loan payoff projection service."""


def _fractional_year(base_year: int, months_elapsed: int) -> float:
    return round(base_year + (months_elapsed / 12.0), 4)


def _project_single_loan_path(
    principal: float,
    annual_interest_rate: float,
    total_monthly_payment: float,
    base_year: int,
) -> dict:
    """Project monthly amortization and return yearly balances until payoff."""
    monthly_rate = annual_interest_rate / 12.0
    monthly_payment = total_monthly_payment

    remaining_balance = principal
    month_of_year = 0
    months_elapsed = 0
    yearly_balances = [{"year": float(base_year), "balance": round(principal, 2)}]

    while remaining_balance > 0 and months_elapsed < 600:
        interest = remaining_balance * monthly_rate
        remaining_balance += interest

        payment = min(monthly_payment, remaining_balance)
        remaining_balance -= payment

        months_elapsed += 1
        month_of_year += 1

        if remaining_balance <= 0:
            yearly_balances.append(
                {
                    "year": _fractional_year(base_year, months_elapsed),
                    "balance": 0.0,
                }
            )
            month_of_year = 0
            break

        if month_of_year == 12:
            yearly_balances.append(
                {
                    "year": float(base_year + (months_elapsed // 12)),
                    "balance": round(max(remaining_balance, 0.0), 2),
                }
            )
            month_of_year = 0

    payoff_year = _fractional_year(base_year, months_elapsed)

    return {
        "additional_monthly_payment": max(0.0, monthly_payment - 500.0),
        "monthly_payment_total": monthly_payment,
        "years": yearly_balances,
        "months_to_payoff": months_elapsed,
        "payoff_year_estimate": payoff_year,
    }


def build_household_student_loan_projection(base_year: int = 2026) -> dict:
    """Build family student loan payoff scenarios.

    Assumptions:
    - Starting principal: $55,000
    - APR: 5%
    - Total monthly payment scenarios: $1,500, $2,000, $2,500
    """
    principal = 55000.0
    annual_interest_rate = 0.05
    assumed_total_monthly_payment = 2000.0
    scenario_payment_levels = [1500.0, 2000.0, 2500.0]

    scenarios = []
    for monthly_payment in scenario_payment_levels:
        projected = _project_single_loan_path(
            principal=principal,
            annual_interest_rate=annual_interest_rate,
            total_monthly_payment=monthly_payment,
            base_year=base_year,
        )
        projected["scenario_key"] = f"payment_{int(monthly_payment)}"
        scenarios.append(projected)

    baseline_scenario = next(
        (item for item in scenarios if item["monthly_payment_total"] == assumed_total_monthly_payment),
        scenarios[0],
    )

    return {
        "principal": principal,
        "annual_interest_rate": annual_interest_rate,
        "assumed_total_monthly_payment": assumed_total_monthly_payment,
        "scenario": baseline_scenario,
        "scenarios": scenarios,
    }
