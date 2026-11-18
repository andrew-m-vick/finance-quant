"""Audit data analytics on a disbursement file.

Tests (following Nigrini, *Benford's Law*, 2012, and the AICPA's Guide to
Audit Data Analytics):

  * First-digit test        — 9 bins, Benford P(d) = log10(1 + 1/d)
  * First-two-digits test   — 90 bins (10–99); Nigrini's preferred test
                              because it pinpoints *which* amounts are
                              over-represented
  * Conformity              — mean absolute deviation (MAD) against
                              Nigrini's critical values. MAD is reported as
                              the primary verdict because chi-square rejects
                              almost every large real-world dataset.
  * Per-bin z-statistics    — with continuity correction; |z| > 1.96 flagged
  * Approval-limit test     — amounts clustered just below a sign-off limit
  * Duplicate tests         — same vendor + invoice, same vendor + amount

Amounts under $10 are excluded from the digit tests (Nigrini): they are
dominated by fees and adjustments and distort the low digits.
"""

import csv
import io
import math
from collections import Counter, defaultdict
from decimal import Decimal

from ledger_utils import InputError, fmt, parse_amount

FIRST_DIGIT_MAD = [(0.006, "Close conformity"), (0.012, "Acceptable conformity"),
                   (0.015, "Marginally acceptable conformity")]
FIRST_TWO_MAD = [(0.0012, "Close conformity"), (0.0018, "Acceptable conformity"),
                 (0.0022, "Marginally acceptable conformity")]
NONCONFORMITY = "Nonconformity"
MIN_AMOUNT = Decimal("10")


def benford_first(d: int) -> float:
    return math.log10(1 + 1 / d)


def _first_digits(amount: Decimal, n: int) -> int:
    digits = format(abs(amount), "f").replace(".", "").lstrip("0")
    digits = (digits + "0" * n)[:n]
    return int(digits)


def _chi2_sf_even_df(x: float, df: int) -> float:
    """Exact chi-square survival function for even degrees of freedom."""
    m = df // 2
    term, total = 1.0, 1.0
    for i in range(1, m):
        term *= (x / 2) / i
        total += term
    return math.exp(-x / 2) * total


def _chi2_sf_wilson_hilferty(x: float, df: int) -> float:
    """Wilson–Hilferty normal approximation (accurate for df ≳ 30)."""
    z = ((x / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
    return 0.5 * math.erfc(z / math.sqrt(2))


def _verdict(mad, table):
    for limit, label in table:
        if mad <= limit:
            return label
    return NONCONFORMITY


def _digit_test(amounts, bins, expected_fn, mad_table, df_exact):
    n = len(amounts)
    width = len(str(bins[0]))
    counts = Counter(_first_digits(a, width) for a in amounts)
    rows, chi2, abs_dev = [], 0.0, 0.0
    for d in bins:
        p_e = expected_fn(d)
        obs = counts.get(d, 0)
        p_o = obs / n
        exp_count = p_e * n
        chi2 += (obs - exp_count) ** 2 / exp_count
        abs_dev += abs(p_o - p_e)
        se = math.sqrt(p_e * (1 - p_e) / n)
        z = max(abs(p_o - p_e) - 1 / (2 * n), 0) / se
        rows.append({
            "digits": d, "observed": obs, "expected": round(exp_count, 1),
            "observed_pct": round(100 * p_o, 2), "expected_pct": round(100 * p_e, 2),
            "z": round(z, 2), "flag": z > 1.96 and p_o > p_e,
            "under": z > 1.96 and p_o < p_e,
        })
    df = len(bins) - 1
    p_value = (_chi2_sf_even_df(chi2, df) if df_exact and df % 2 == 0
               else _chi2_sf_wilson_hilferty(chi2, df))
    mad = abs_dev / len(bins)
    return {
        "rows": rows, "chi_square": round(chi2, 2), "df": df,
        "p_value": p_value, "mad": round(mad, 5),
        "conformity": _verdict(mad, mad_table),
        "spikes": [r["digits"] for r in sorted(rows, key=lambda r: -r["z"]) if r["flag"]][:8],
    }


def _expected_first_two(d):
    return math.log10(1 + 1 / d)


def parse_disbursements(text):
    if not text or not text.strip():
        raise InputError("No data provided.")
    lines = text.strip().splitlines()
    first = next(csv.reader([lines[0]]))
    has_header = any(c.strip().lower() == "amount" for c in first)
    if not has_header:
        # bare list of numbers, one per line
        return [{"row": i, "vendor": "", "invoice": "", "amount": parse_amount(l.split(",")[0], row=i)}
                for i, l in enumerate(lines, start=1) if l.strip()]
    reader = csv.DictReader(io.StringIO(text.strip()))
    reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]
    out = []
    for i, r in enumerate(reader, start=2):
        if not r.get("amount", "").strip():
            continue
        out.append({"row": i, "vendor": (r.get("vendor") or "").strip(),
                    "invoice": (r.get("invoice") or "").strip(),
                    "amount": parse_amount(r["amount"], row=i)})
    return out


def run_benford(text, approval_limit=5000):
    records = parse_disbursements(text)
    amounts = [abs(r["amount"]) for r in records]
    tested = [a for a in amounts if a >= MIN_AMOUNT]
    if len(tested) < 50:
        raise InputError(
            f"Only {len(tested)} amounts of $10 or more — Benford analysis needs "
            "a few hundred at minimum to say anything."
        )

    warnings = []
    if len(tested) < 500:
        warnings.append(
            f"{len(tested)} amounts tested. Nigrini recommends 1,000+ for "
            "reliable conformity results; treat these as indicative."
        )

    first = _digit_test(tested, list(range(1, 10)), benford_first, FIRST_DIGIT_MAD, True)
    first_two = _digit_test(tested, list(range(10, 100)), _expected_first_two, FIRST_TWO_MAD, False)

    # Approval-limit clustering: compare the 10% band below the limit with the
    # 10% band above it. Under Benford the lower band should hold slightly
    # *more* items (≈1.1× for a $5,000 limit) — a large excess is a red flag.
    limit = parse_amount(approval_limit, field="approval limit")
    threshold = None
    if limit > 0:
        lo, hi = limit * Decimal("0.9"), limit * Decimal("1.1")
        below = [r for r in records if lo <= abs(r["amount"]) < limit]
        above = [r for r in records if limit <= abs(r["amount"]) < hi]
        lo_f, l_f, hi_f = float(lo), float(limit), float(hi)
        expected_ratio = math.log10(l_f / lo_f) / math.log10(hi_f / l_f)
        ratio = len(below) / max(len(above), 1)
        by_vendor = Counter(r["vendor"] or "(no vendor)" for r in below)
        threshold = {
            "limit": fmt(limit), "band_below": len(below), "band_above": len(above),
            "ratio": round(ratio, 2), "expected_ratio": round(expected_ratio, 2),
            "flag": len(below) >= 10 and ratio > 2 * expected_ratio,
            "top_vendors": [{"vendor": v, "count": c} for v, c in by_vendor.most_common(5)],
        }

    # Duplicates
    by_invoice = defaultdict(list)
    by_amount = defaultdict(list)
    for r in records:
        if r["vendor"] and r["invoice"]:
            by_invoice[(r["vendor"], r["invoice"])].append(r)
        if r["vendor"] and abs(r["amount"]) >= 100:
            by_amount[(r["vendor"], r["amount"])].append(r)
    dup_invoices = [
        {"vendor": v, "invoice": inv, "count": len(rs),
         "amount": fmt(rs[0]["amount"]), "rows": [r["row"] for r in rs],
         "exposure": fmt(sum(abs(r["amount"]) for r in rs[1:]))}
        for (v, inv), rs in by_invoice.items() if len(rs) > 1
    ]
    dup_amounts = sorted([
        {"vendor": v, "amount": fmt(a), "count": len(rs), "rows": [r["row"] for r in rs]}
        for (v, a), rs in by_amount.items() if len(rs) > 1
    ], key=lambda d: (-d["count"], -d["amount"]))[:10]

    round_hundreds = sum(1 for a in tested if a % 100 == 0)

    return {
        "count_total": len(records),
        "count_tested": len(tested),
        "excluded_under_10": len(amounts) - len(tested),
        "total_dollars": fmt(sum(amounts)),
        "warnings": warnings,
        "first_digit": first,
        "first_two_digits": first_two,
        "threshold": threshold,
        "duplicate_invoices": sorted(dup_invoices, key=lambda d: -d["exposure"]),
        "duplicate_invoice_exposure": fmt(sum(Decimal(str(d["exposure"])) for d in dup_invoices)),
        "repeated_amounts": dup_amounts,
        "round_hundreds_pct": round(100 * round_hundreds / len(tested), 2),
    }
