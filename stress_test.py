"""Financial stress test scenarios.

Scenarios modeled:
  1. Job loss runway — how many months can fixed expenses be covered from
     liquid savings, assuming zero income and variable expenses cut to 50%.
  2. Market drawdown — 30% peak-to-trough decline on invested assets.
  3. Emergency expense — $5,000 unplanned expense absorbed from liquid savings.
  4. Inflation shock — 5% annual inflation for 2 years compounded against
     fixed + variable expenses, with income growing at 2% to model lag.
"""

from typing import Any


EMERGENCY_SHOCK = 5_000.0
MARKET_DRAWDOWN = 0.30
INFLATION_RATE = 0.05
INCOME_GROWTH = 0.02
INFLATION_YEARS = 2
VARIABLE_CUT_UNDER_JOB_LOSS = 0.5


def _job_loss_runway(fixed: float, variable: float, savings: float) -> dict[str, Any]:
    burn = fixed + variable * VARIABLE_CUT_UNDER_JOB_LOSS
    months = savings / burn if burn > 0 else float("inf")
    if months >= 12:
        severity = "strong"
    elif months >= 6:
        severity = "adequate"
    elif months >= 3:
        severity = "weak"
    else:
        severity = "critical"
    return {
        "name": "Job Loss Runway",
        "months": round(months, 1),
        "monthly_burn_rate": round(burn, 2),
        "severity": severity,
        "summary": f"{months:.1f} months of runway at ${burn:,.0f}/mo burn.",
    }


def _market_drawdown(invested: float) -> dict[str, Any]:
    loss = invested * MARKET_DRAWDOWN
    remaining = invested - loss
    return {
        "name": "30% Market Drawdown",
        "loss": round(loss, 2),
        "remaining_invested": round(remaining, 2),
        "severity": "informational",
        "summary": f"Portfolio drops ${loss:,.0f} to ${remaining:,.0f}. Recovery "
        f"historically takes 1–4 years.",
    }


def _emergency_expense(savings: float) -> dict[str, Any]:
    after = savings - EMERGENCY_SHOCK
    if after >= savings * 0.7:
        severity = "strong"
    elif after >= 0:
        severity = "adequate"
    else:
        severity = "critical"
    return {
        "name": "$5K Emergency Expense",
        "savings_after": round(after, 2),
        "severity": severity,
        "summary": f"Liquid savings after shock: ${after:,.0f}.",
    }


def _inflation_shock(
    income: float, fixed: float, variable: float
) -> dict[str, Any]:
    expense_multiplier = (1 + INFLATION_RATE) ** INFLATION_YEARS
    income_multiplier = (1 + INCOME_GROWTH) ** INFLATION_YEARS
    new_expenses = (fixed + variable) * expense_multiplier
    new_income = income * income_multiplier
    old_surplus = income - (fixed + variable)
    new_surplus = new_income - new_expenses
    surplus_change = new_surplus - old_surplus
    if new_surplus > 0 and surplus_change > -old_surplus * 0.25:
        severity = "strong"
    elif new_surplus > 0:
        severity = "adequate"
    elif new_surplus > -income * 0.1:
        severity = "weak"
    else:
        severity = "critical"
    return {
        "name": "5% Inflation for 2 Years",
        "new_monthly_surplus": round(new_surplus, 2),
        "surplus_change": round(surplus_change, 2),
        "severity": severity,
        "summary": f"Monthly surplus moves from ${old_surplus:,.0f} to "
        f"${new_surplus:,.0f} after 2yr inflation lag.",
    }


def _debt_pressure(
    income: float, debt_payments: float, total_debt: float
) -> dict[str, Any]:
    dti = debt_payments / income if income > 0 else float("inf")
    if dti < 0.15:
        severity = "strong"
    elif dti < 0.28:
        severity = "adequate"
    elif dti < 0.40:
        severity = "weak"
    else:
        severity = "critical"
    return {
        "name": "Debt Service Ratio",
        "dti": round(dti, 3),
        "total_debt": round(total_debt, 2),
        "severity": severity,
        "summary": f"Debt payments consume {dti * 100:.1f}% of monthly income.",
    }


_SEVERITY_SCORES = {
    "strong": 100,
    "adequate": 75,
    "informational": 80,
    "weak": 45,
    "critical": 15,
}


def _resilience_score(scenarios: list[dict[str, Any]]) -> int:
    weights = {
        "Job Loss Runway": 0.35,
        "$5K Emergency Expense": 0.20,
        "Debt Service Ratio": 0.20,
        "5% Inflation for 2 Years": 0.15,
        "30% Market Drawdown": 0.10,
    }
    total = 0.0
    for s in scenarios:
        w = weights.get(s["name"], 0)
        total += w * _SEVERITY_SCORES.get(s["severity"], 50)
    return round(total)


def run_stress_test(
    monthly_income: float,
    monthly_fixed_expenses: float,
    monthly_variable_expenses: float,
    liquid_savings: float,
    invested_assets: float,
    total_debt: float,
    monthly_debt_payments: float,
) -> dict[str, Any]:
    values = {
        "monthly_income": monthly_income,
        "monthly_fixed_expenses": monthly_fixed_expenses,
        "monthly_variable_expenses": monthly_variable_expenses,
        "liquid_savings": liquid_savings,
        "invested_assets": invested_assets,
        "total_debt": total_debt,
        "monthly_debt_payments": monthly_debt_payments,
    }
    for name, v in values.items():
        if v < 0:
            raise ValueError(f"{name} must be non-negative")
        if v > 1e12:
            raise ValueError(f"{name} is implausibly large")
    if monthly_income <= 0:
        raise ValueError("monthly_income must be greater than zero")
    if monthly_debt_payments > monthly_income:
        raise ValueError("monthly_debt_payments cannot exceed monthly_income")
    scenarios = [
        _job_loss_runway(
            monthly_fixed_expenses, monthly_variable_expenses, liquid_savings
        ),
        _emergency_expense(liquid_savings),
        _debt_pressure(monthly_income, monthly_debt_payments, total_debt),
        _inflation_shock(
            monthly_income, monthly_fixed_expenses, monthly_variable_expenses
        ),
        _market_drawdown(invested_assets),
    ]
    score = _resilience_score(scenarios)
    weak_points = sorted(
        [s for s in scenarios if s["severity"] in ("weak", "critical")],
        key=lambda s: 0 if s["severity"] == "critical" else 1,
    )
    return {
        "resilience_score": score,
        "grade": _grade(score),
        "scenarios": scenarios,
        "weak_points": weak_points,
    }


def _grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"
