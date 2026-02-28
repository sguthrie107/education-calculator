from app.services.education_withdrawals import build_child_withdrawal_scenarios


def test_withdrawals_apply_growth_before_deduction():
    child_config = {
        "birth_year": 2008,
        "inflation_rate": 0.03,
        "phases": {
            "phase_3": {
                "allocation": {
                    "test_asset": {
                        "pct": 1.0,
                        "expected_annual_return": 0.10,
                    }
                }
            }
        },
    }

    projected_rows = [
        {
            "year": 2026,
            "balance": 10000.0,
            "contributions_ytd": 0.0,
        }
    ]

    scenarios = build_child_withdrawal_scenarios(
        child_config=child_config,
        projected_rows=projected_rows,
        base_year=2026,
        covered_ratio=0.9,
    )

    year_one = scenarios["scenarios"]["direct_4yr"]["yearly_costs"][0]
    assert year_one["starting_balance"] == 10000.0
    assert year_one["annual_contribution"] == 0.0
    assert year_one["paid_by_529"] == 11000.0
    assert year_one["ending_balance"] == 0.0
