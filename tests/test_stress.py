from stress_test import run_stress_test


def _scenario(result, name):
    return next(s for s in result["scenarios"] if s["name"] == name)


def test_strong_balance_sheet_scores_high():
    r = run_stress_test(
        monthly_income=10_000,
        monthly_fixed_expenses=3_000,
        monthly_variable_expenses=1_000,
        liquid_savings=80_000,
        invested_assets=200_000,
        total_debt=0,
        monthly_debt_payments=0,
    )
    assert r["resilience_score"] >= 85
    assert r["grade"] in ("A", "B")
    assert r["weak_points"] == []


def test_thin_cushion_flags_runway_and_emergency():
    r = run_stress_test(
        monthly_income=5_000,
        monthly_fixed_expenses=3_500,
        monthly_variable_expenses=1_000,
        liquid_savings=2_000,
        invested_assets=0,
        total_debt=0,
        monthly_debt_payments=0,
    )
    runway = _scenario(r, "Job Loss Runway")
    emergency = _scenario(r, "$5K Emergency Expense")
    assert runway["severity"] == "critical"
    assert emergency["severity"] == "critical"
    assert any(s["name"] == "Job Loss Runway" for s in r["weak_points"])


def test_dti_bands():
    high_dti = run_stress_test(
        monthly_income=5_000,
        monthly_fixed_expenses=2_000,
        monthly_variable_expenses=500,
        liquid_savings=50_000,
        invested_assets=0,
        total_debt=100_000,
        monthly_debt_payments=2_500,  # 50% DTI
    )
    assert _scenario(high_dti, "Debt Service Ratio")["severity"] == "critical"

    low_dti = run_stress_test(
        monthly_income=10_000,
        monthly_fixed_expenses=2_000,
        monthly_variable_expenses=500,
        liquid_savings=50_000,
        invested_assets=0,
        total_debt=10_000,
        monthly_debt_payments=500,  # 5% DTI
    )
    assert _scenario(low_dti, "Debt Service Ratio")["severity"] == "strong"


def test_market_drawdown_applies_30pct_loss():
    r = run_stress_test(
        monthly_income=6_000,
        monthly_fixed_expenses=3_000,
        monthly_variable_expenses=1_000,
        liquid_savings=20_000,
        invested_assets=100_000,
        total_debt=0,
        monthly_debt_payments=0,
    )
    md = _scenario(r, "30% Market Drawdown")
    assert md["loss"] == 30_000
    assert md["remaining_invested"] == 70_000
