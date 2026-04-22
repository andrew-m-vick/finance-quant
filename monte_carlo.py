"""Monte Carlo retirement simulator.

Uses geometric Brownian motion on annual returns. Each year's return is drawn
from a normal distribution parameterized by the user's expected return (mu)
and volatility (sigma). To avoid the classic arithmetic-return inflation bug,
the drift is converted to its geometric equivalent: mu_geo = mu - sigma^2 / 2.

Contributions are assumed to happen at the start of each year, before returns
are applied. Results are reported in both nominal and real (inflation-adjusted)
dollars so users can see the difference.
"""

from typing import Any

import numpy as np


PATHS_TO_RETURN = 200  # sample of paths to send to the fan chart


def run_monte_carlo(
    current_age: int,
    retirement_age: int,
    current_savings: float,
    annual_contribution: float,
    expected_return: float,
    volatility: float,
    inflation: float = 0.025,
    goal: float = 0.0,
    num_simulations: int = 10_000,
) -> dict[str, Any]:
    if current_age < 0 or current_age > 100:
        raise ValueError("current_age must be between 0 and 100")
    if retirement_age <= current_age:
        raise ValueError("retirement_age must be greater than current_age")
    if retirement_age > 110:
        raise ValueError("retirement_age must be 110 or less")
    if current_savings < 0:
        raise ValueError("current_savings must be non-negative")
    if annual_contribution < 0:
        raise ValueError("annual_contribution must be non-negative")
    if not -0.5 <= expected_return <= 0.5:
        raise ValueError("expected_return must be between -50% and 50%")
    if not 0 <= volatility <= 1.0:
        raise ValueError("volatility must be between 0% and 100%")
    if not -0.1 <= inflation <= 0.5:
        raise ValueError("inflation must be between -10% and 50%")
    if goal < 0:
        raise ValueError("goal must be non-negative")
    if num_simulations < 100 or num_simulations > 50_000:
        raise ValueError("num_simulations must be between 100 and 50,000")

    years = retirement_age - current_age
    # Interpret expected_return as the arithmetic annual return: E[1+R] = 1+mu.
    # For log-returns Z = ln(1+R) ~ Normal(m, sigma^2) to satisfy this we need
    # m = ln(1+mu) - sigma^2/2. This is the geometric-drift correction.
    log_mean = np.log(1 + expected_return) - 0.5 * volatility**2

    rng = np.random.default_rng(seed=None)
    log_returns = rng.normal(
        loc=log_mean, scale=volatility, size=(num_simulations, years)
    )
    growth = np.exp(log_returns)

    balances = np.empty((num_simulations, years + 1))
    balances[:, 0] = current_savings
    for t in range(years):
        balances[:, t + 1] = (balances[:, t] + annual_contribution) * growth[:, t]

    final = balances[:, -1]
    percentiles = {
        "p10": float(np.percentile(final, 10)),
        "p25": float(np.percentile(final, 25)),
        "p50": float(np.percentile(final, 50)),
        "p75": float(np.percentile(final, 75)),
        "p90": float(np.percentile(final, 90)),
    }

    real_deflator = (1 + inflation) ** years
    real_percentiles = {k: v / real_deflator for k, v in percentiles.items()}

    prob_meeting_goal = (
        float(np.mean(final >= goal)) if goal > 0 else None
    )

    # Fan chart percentile bands over time (yearly)
    bands_over_time = {
        "p10": np.percentile(balances, 10, axis=0).tolist(),
        "p25": np.percentile(balances, 25, axis=0).tolist(),
        "p50": np.percentile(balances, 50, axis=0).tolist(),
        "p75": np.percentile(balances, 75, axis=0).tolist(),
        "p90": np.percentile(balances, 90, axis=0).tolist(),
    }

    # Sample of raw paths for visual texture
    sample_idx = rng.choice(
        num_simulations, size=min(PATHS_TO_RETURN, num_simulations), replace=False
    )
    sample_paths = balances[sample_idx].tolist()

    # Histogram of final outcomes
    hist_counts, hist_edges = np.histogram(final, bins=40)
    histogram = {
        "counts": hist_counts.tolist(),
        "edges": hist_edges.tolist(),
    }

    ages = list(range(current_age, retirement_age + 1))

    return {
        "years": years,
        "ages": ages,
        "num_simulations": num_simulations,
        "percentiles_nominal": percentiles,
        "percentiles_real": real_percentiles,
        "prob_meeting_goal": prob_meeting_goal,
        "goal": goal,
        "bands_over_time": bands_over_time,
        "sample_paths": sample_paths,
        "histogram": histogram,
        "mean_final": float(np.mean(final)),
        "std_final": float(np.std(final)),
    }
