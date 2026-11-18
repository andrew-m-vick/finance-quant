"""Shared parsing helpers for the accounting tools.

All money is handled as ``decimal.Decimal`` rounded to the cent, so ledgers
tie out exactly — no binary floating-point drift (0.1 + 0.2 != 0.3).
"""

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class InputError(ValueError):
    """Raised for user-correctable problems with pasted data."""


def money(value) -> Decimal:
    """Round any numeric to a cent-precision Decimal."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def parse_amount(raw, *, field="amount", row=None) -> Decimal:
    """Parse '$1,234.50', '(1,234.50)', '-1234.5' or '' (→ 0.00)."""
    text = str(raw if raw is not None else "").strip()
    if text in ("", "-", "—"):
        return ZERO
    negative = text.startswith("(") and text.endswith(")")
    cleaned = text.strip("()").replace("$", "").replace(",", "").strip()
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        where = f" on row {row}" if row else ""
        raise InputError(f"Could not read {field} '{raw}'{where}.") from None
    return money(-value if negative else value)


_DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%m-%d-%Y")


def parse_date(raw, *, row=None) -> date:
    text = str(raw or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    where = f" on row {row}" if row else ""
    raise InputError(f"Could not read date '{raw}'{where}. Use MM/DD/YYYY.")


def read_csv(text: str, required: list[str]) -> list[tuple[int, dict]]:
    """Parse pasted CSV with a header row; returns (row_number, row) pairs.

    Header matching is case-insensitive and ignores surrounding whitespace.
    Blank lines are skipped. Row numbers are 1-based and count the header,
    so they match what a user sees in a spreadsheet.
    """
    if not text or not text.strip():
        raise InputError("No data provided.")
    reader = csv.reader(io.StringIO(text.strip()))
    try:
        header = [h.strip().lower() for h in next(reader)]
    except StopIteration:
        raise InputError("No data provided.") from None
    missing = [c for c in required if c.lower() not in header]
    if missing:
        raise InputError(
            f"Missing column(s): {', '.join(missing)}. "
            f"Expected header: {', '.join(required)}."
        )
    rows = []
    for i, cells in enumerate(reader, start=2):
        if not any(c.strip() for c in cells):
            continue
        cells = cells + [""] * (len(header) - len(cells))
        rows.append((i, {header[j]: cells[j].strip() for j in range(len(header))}))
    if not rows:
        raise InputError("Header found but no data rows.")
    return rows


def fmt(d: Decimal) -> float:
    """Decimal → float for JSON. Safe: values are already cent-rounded."""
    return float(d)
