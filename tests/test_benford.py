import math
import os

import numpy as np
import pytest

from benford import _chi2_sf_even_df, _first_digits, run_benford
from ledger_utils import InputError
from decimal import Decimal

SAMPLE = open(os.path.join(os.path.dirname(__file__), "..", "static", "samples", "ap_disbursements.csv")).read()


def lognormal_csv(seed, n=3000):
    rng = np.random.default_rng(seed)
    return "\n".join(f"{x:.2f}" for x in rng.lognormal(6.9, 1.45, n))


def test_benford_probabilities_sum_to_one():
    assert math.isclose(sum(math.log10(1 + 1 / d) for d in range(1, 10)), 1.0)
    assert math.isclose(sum(math.log10(1 + 1 / d) for d in range(10, 100)), 1.0)


@pytest.mark.parametrize("amount,n,expected", [
    ("6000", 2, 60), ("10.50", 2, 10), ("0.0347", 1, 3), ("1E+3", 2, 10), ("9.99", 1, 9),
])
def test_leading_digit_extraction(amount, n, expected):
    assert _first_digits(Decimal(amount), n) == expected


def test_chi2_survival_matches_known_values():
    # Critical values for 8 df: 15.507 at α=0.05, 20.090 at α=0.01
    assert math.isclose(_chi2_sf_even_df(15.507, 8), 0.05, abs_tol=1e-3)
    assert math.isclose(_chi2_sf_even_df(20.090, 8), 0.01, abs_tol=1e-3)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_natural_data_conforms_and_raises_no_threshold_flag(seed):
    r = run_benford(lognormal_csv(seed))
    assert r["first_digit"]["conformity"] in ("Close conformity", "Acceptable conformity")
    assert r["first_two_digits"]["mad"] < 0.0018
    assert not r["threshold"]["flag"]


def test_sample_exposes_planted_fraud():
    r = run_benford(SAMPLE)
    assert r["threshold"]["flag"]
    assert r["threshold"]["top_vendors"][0]["vendor"] == "Brightline Consulting LLC"
    assert {47, 48, 49} <= set(r["first_two_digits"]["spikes"])
    assert len(r["duplicate_invoices"]) == 7
    assert r["repeated_amounts"][0]["vendor"] == "Cedar Point Legal"


def test_small_population_is_refused():
    with pytest.raises(InputError, match="needs"):
        run_benford("\n".join(["123.45"] * 20))


def test_small_population_warns():
    r = run_benford(lognormal_csv(4, n=300))
    assert r["warnings"]
