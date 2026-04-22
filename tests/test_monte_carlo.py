import numpy as np
import pytest

from monte_carlo import run_monte_carlo


def test_zero_volatility_matches_deterministic_growth():
    """With sigma=0, every path is identical and equals the closed-form FV."""
    r = run_monte_carlo(
        current_age=30,
        retirement_age=35,
        current_savings=10_000,
        annual_contribution=1_000,
        expected_return=0.05,
        volatility=0.0,
        inflation=0.0,
        goal=0,
        num_simulations=200,
    )
    # With sigma=0 the drift reduces to ln(1+mu), so growth = 1+mu per year.
    balance = 10_000
    for _ in range(5):
        balance = (balance + 1_000) * 1.05
    for key in ("p10", "p50", "p90"):
        assert r["percentiles_nominal"][key] == pytest.approx(balance, rel=1e-6)


def test_geometric_drift_correction_unbiased_expected_terminal():
    """The mu - sigma^2/2 drift correction should make E[B_T] match the
    arithmetic-return deterministic projection, within Monte Carlo error."""
    mu, sigma, years = 0.07, 0.20, 20
    r = run_monte_carlo(
        current_age=30,
        retirement_age=30 + years,
        current_savings=100_000,
        annual_contribution=0,
        expected_return=mu,
        volatility=sigma,
        inflation=0.0,
        goal=0,
        num_simulations=20_000,
    )
    # With the corrected drift, E[B_T] = B_0 * (1+mu)^T.
    expected = 100_000 * (1 + mu) ** years
    # MC error on mean of log-normal with sigma*sqrt(T) is substantial; allow 10%.
    assert r["mean_final"] == pytest.approx(expected, rel=0.10)


def test_percentiles_are_ordered():
    r = run_monte_carlo(
        current_age=25,
        retirement_age=65,
        current_savings=20_000,
        annual_contribution=10_000,
        expected_return=0.07,
        volatility=0.15,
        inflation=0.025,
        goal=1_000_000,
        num_simulations=2_000,
    )
    p = r["percentiles_nominal"]
    assert p["p10"] < p["p25"] < p["p50"] < p["p75"] < p["p90"]
    # Real < nominal when inflation > 0.
    for k in p:
        assert r["percentiles_real"][k] < p[k]


def test_probability_of_meeting_goal_bounds():
    # Huge goal → near-zero probability.
    r_hi = run_monte_carlo(
        current_age=60,
        retirement_age=65,
        current_savings=10_000,
        annual_contribution=0,
        expected_return=0.05,
        volatility=0.10,
        inflation=0.0,
        goal=10_000_000,
        num_simulations=2_000,
    )
    assert r_hi["prob_meeting_goal"] < 0.01

    # Trivial goal → near-certain.
    r_lo = run_monte_carlo(
        current_age=60,
        retirement_age=65,
        current_savings=100_000,
        annual_contribution=0,
        expected_return=0.05,
        volatility=0.10,
        inflation=0.0,
        goal=1,
        num_simulations=2_000,
    )
    assert r_lo["prob_meeting_goal"] > 0.99


def test_rejects_bad_age_inputs():
    with pytest.raises(ValueError):
        run_monte_carlo(
            current_age=65,
            retirement_age=65,
            current_savings=100_000,
            annual_contribution=0,
            expected_return=0.05,
            volatility=0.10,
        )
