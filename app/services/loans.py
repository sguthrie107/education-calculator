"""Household student loan payoff projection service."""


def _project_single_loan_path(
    principal: float,
    annual_interest_rate: float,
    minimum_monthly_payment: float,
    additional_monthly_payment: float,
    base_year: int,
) -> dict:
    """Project monthly amortization and return yearly balances until payoff."""
    monthly_rate = annual_interest_rate / 12.0
    monthly_payment = minimum_monthly_payment + additional_monthly_payment

    remaining_balance = principal
    year = base_year
    month_of_year = 0
    months_elapsed = 0
    yearly_balances = [{"year": base_year, "balance": round(principal, 2)}]

    while remaining_balance > 0 and months_elapsed < 600:
        interest = remaining_balance * monthly_rate
        remaining_balance += interest

        payment = min(monthly_payment, remaining_balance)
        remaining_balance -= payment

        months_elapsed += 1
        month_of_year += 1

        if month_of_year == 12 or remaining_balance <= 0:
            yearly_balances.append(
                {
                    "year": year + 1,
                    "balance": round(max(remaining_balance, 0.0), 2),
                }
            )
            year += 1
            month_of_year = 0

    payoff_year = base_year + (months_elapsed // 12)

    return {
        "additional_monthly_payment": additional_monthly_payment,
        "monthly_payment_total": monthly_payment,
        "years": yearly_balances,
        "months_to_payoff": months_elapsed,
        "payoff_year_estimate": payoff_year,
    }


def build_household_student_loan_projection(base_year: int = 2026) -> dict:
    """Build family student loan payoff scenarios.

    Assumptions:
    - Starting principal: $70,000
    - APR: 5%
    - Total monthly payment: $2,000
    """
    principal = 70000.0
    annual_interest_rate = 0.05
    assumed_total_monthly_payment = 2000.0
    minimum_monthly_payment = 500.0
    additional_monthly_payment = assumed_total_monthly_payment - minimum_monthly_payment

    scenario = _project_single_loan_path(
        principal=principal,
        annual_interest_rate=annual_interest_rate,
        minimum_monthly_payment=minimum_monthly_payment,
        additional_monthly_payment=additional_monthly_payment,
        base_year=base_year,
    )

    return {
        "principal": principal,
        "annual_interest_rate": annual_interest_rate,
        "assumed_total_monthly_payment": assumed_total_monthly_payment,
        "scenario": scenario,
    }
