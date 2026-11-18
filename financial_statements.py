"""Adjusted trial balance → GAAP-style financial statements.

Takes an adjusted trial balance (one row per account with a category, a
debit and a credit) and produces:

  * a trial-balance check, with textbook error diagnostics when it doesn't
    balance (divisible-by-9 transpositions, wrong-side postings, omissions)
  * abnormal-balance flags (e.g. an asset carrying a credit balance)
  * a multi-step income statement
  * a statement of retained earnings
  * a classified balance sheet with the A = L + E check
  * closing entries and a post-closing trial balance
  * common financial ratios
"""

from decimal import Decimal
from itertools import combinations

from ledger_utils import InputError, ZERO, fmt, money, parse_amount, read_csv

# category -> (normal balance, statement, display group)
CATEGORIES = {
    "current_asset":            ("debit",  "bs", "Current assets"),
    "contra_current_asset":     ("credit", "bs", "Current assets"),
    "noncurrent_asset":         ("debit",  "bs", "Property, plant & equipment and other assets"),
    "contra_noncurrent_asset":  ("credit", "bs", "Property, plant & equipment and other assets"),
    "current_liability":        ("credit", "bs", "Current liabilities"),
    "noncurrent_liability":     ("credit", "bs", "Long-term liabilities"),
    "equity":                   ("credit", "bs", "Contributed capital"),
    "retained_earnings":        ("credit", "re", "Retained earnings"),
    "dividends":                ("debit",  "re", "Dividends"),
    "revenue":                  ("credit", "is", "Revenue"),
    "contra_revenue":           ("debit",  "is", "Revenue"),
    "cogs":                     ("debit",  "is", "Cost of goods sold"),
    "operating_expense":        ("debit",  "is", "Operating expenses"),
    "other_income":             ("credit", "is", "Other income (expense)"),
    "other_expense":            ("debit",  "is", "Other income (expense)"),
    "income_tax_expense":       ("debit",  "is", "Income tax expense"),
}

TEMPORARY = {
    "revenue", "contra_revenue", "cogs", "operating_expense",
    "other_income", "other_expense", "income_tax_expense", "dividends",
}

ALIASES = {
    "asset": "current_asset",
    "contra_asset": "contra_noncurrent_asset",
    "liability": "current_liability",
    "long_term_liability": "noncurrent_liability",
    "expense": "operating_expense",
    "cost_of_goods_sold": "cogs",
    "sales_returns": "contra_revenue",
    "tax_expense": "income_tax_expense",
    "income_tax": "income_tax_expense",
    "common_stock": "equity",
    "paid_in_capital": "equity",
    "drawings": "dividends",
}


def _normalize_category(raw: str, row: int) -> str:
    key = raw.strip().lower().replace("-", "_").replace(" ", "_").replace("&", "and")
    key = ALIASES.get(key, key)
    if key not in CATEGORIES:
        raise InputError(
            f"Unknown category '{raw}' on row {row}. "
            f"Use one of: {', '.join(CATEGORIES)}."
        )
    return key


def parse_trial_balance(csv_text: str) -> list[dict]:
    rows = read_csv(csv_text, ["Account", "Category", "Debit", "Credit"])
    accounts = []
    for row_no, r in rows:
        name = r["account"]
        if not name:
            raise InputError(f"Row {row_no} has no account name.")
        debit = parse_amount(r["debit"], field="debit", row=row_no)
        credit = parse_amount(r["credit"], field="credit", row=row_no)
        if debit < 0 or credit < 0:
            raise InputError(
                f"Row {row_no} ({name}): enter debits and credits as positive "
                "numbers in their own column."
            )
        accounts.append({
            "row": row_no,
            "account": name,
            "category": _normalize_category(r["category"], row_no),
            "debit": debit,
            "credit": credit,
        })
    return accounts


# --- trial balance diagnostics ---------------------------------------------

def _digit_swaps(amount: Decimal):
    """Yield every amount reachable by swapping two digits of `amount`."""
    digits = list(str(int(amount * 100)))
    for i, j in combinations(range(len(digits)), 2):
        if digits[i] == digits[j]:
            continue
        swapped = digits[:]
        swapped[i], swapped[j] = swapped[j], swapped[i]
        if swapped[0] == "0":
            continue
        yield money(Decimal("".join(swapped)) / 100)


def diagnose_imbalance(accounts, total_debits, total_credits) -> list[str]:
    """Classic manual techniques for locating a trial-balance error."""
    diff = abs(total_debits - total_credits)
    if diff == ZERO:
        return []
    heavy = "debits" if total_debits > total_credits else "credits"
    hints = [f"Total {heavy} exceed the other side by ${diff:,.2f}."]

    for a in accounts:
        bal = a["debit"] or a["credit"]
        if bal == diff:
            hints.append(
                f"The difference equals the balance of {a['account']} "
                f"(${bal:,.2f}) — check whether it was omitted from one side "
                "or recorded twice."
            )
        if bal * 2 == diff:
            side = "debit" if a["debit"] else "credit"
            hints.append(
                f"The difference is exactly twice {a['account']} "
                f"(${bal:,.2f}) — it may be entered as a {side} when it "
                "belongs on the other side."
            )

    if int(diff * 100) % 9 == 0:
        hints.append(
            "The difference is divisible by 9, the signature of a "
            "transposition (e.g. 42 for 24) or a slide (e.g. 450 for 45)."
        )
        leads = []
        for a in accounts:
            on_heavy_side = (a["debit"] > 0) == (heavy == "debits")
            bal = a["debit"] or a["credit"]
            for candidate in _digit_swaps(bal):
                # A heavy-side account must have been overstated; a light-side
                # account must have been understated.
                fixes = (bal - candidate == diff) if on_heavy_side else (candidate - bal == diff)
                if fixes:
                    leads.append(f"{a['account']} (${bal:,.2f} → ${candidate:,.2f})")
                    break
        if leads:
            hints.append(
                "Digit swaps that would make the trial balance tie — trace "
                "these to source documents: " + "; ".join(leads) + "."
            )
    return hints


def abnormal_balances(accounts) -> list[dict]:
    flags = []
    for a in accounts:
        normal = CATEGORIES[a["category"]][0]
        net = a["debit"] - a["credit"]
        if (normal == "debit" and net < 0) or (normal == "credit" and net > 0):
            flags.append({
                "account": a["account"],
                "category": a["category"],
                "normal": normal,
                "balance": fmt(abs(net)),
                "side": "credit" if net < 0 else "debit",
            })
    return flags


# --- statements --------------------------------------------------------------

def _natural(a) -> Decimal:
    """Balance expressed on the account's normal side (positive = normal)."""
    net = a["debit"] - a["credit"]
    return net if CATEGORIES[a["category"]][0] == "debit" else -net


def _lines(accounts, *cats, sign=1):
    out = []
    for a in accounts:
        if a["category"] in cats:
            amt = _natural(a)
            if a["category"].startswith("contra_"):
                amt = -amt
            out.append({"account": a["account"], "amount": amt * sign})
    return out


def _sum(lines) -> Decimal:
    return sum((l["amount"] for l in lines), ZERO)


def _ser(lines):
    return [{"account": l["account"], "amount": fmt(l["amount"])} for l in lines]


def _ratio(num, den, kind):
    if den == ZERO:
        return None
    v = num / den
    return round(float(v * 100 if kind == "pct" else v), 2)


def build_statements(accounts: list[dict], entity: str = "", period_end: str = "") -> dict:
    total_debits = sum((a["debit"] for a in accounts), ZERO)
    total_credits = sum((a["credit"] for a in accounts), ZERO)
    balanced = total_debits == total_credits

    # Income statement (multi-step)
    revenue = _lines(accounts, "revenue", "contra_revenue")
    net_sales = _sum(revenue)
    cogs = _lines(accounts, "cogs")
    gross_profit = net_sales - _sum(cogs)
    opex = _lines(accounts, "operating_expense")
    operating_income = gross_profit - _sum(opex)
    other = _lines(accounts, "other_income") + _lines(accounts, "other_expense", sign=-1)
    pretax = operating_income + _sum(other)
    tax = _lines(accounts, "income_tax_expense")
    net_income = pretax - _sum(tax)

    # Retained earnings
    beginning_re = _sum(_lines(accounts, "retained_earnings"))
    dividends = _sum(_lines(accounts, "dividends"))
    ending_re = beginning_re + net_income - dividends

    # Balance sheet
    current_assets = _lines(accounts, "current_asset", "contra_current_asset")
    noncurrent_assets = _lines(accounts, "noncurrent_asset", "contra_noncurrent_asset")
    total_ca = _sum(current_assets)
    total_assets = total_ca + _sum(noncurrent_assets)
    current_liabs = _lines(accounts, "current_liability")
    noncurrent_liabs = _lines(accounts, "noncurrent_liability")
    total_cl = _sum(current_liabs)
    total_liabilities = total_cl + _sum(noncurrent_liabs)
    contributed = _lines(accounts, "equity")
    total_equity = _sum(contributed) + ending_re
    bs_difference = total_assets - (total_liabilities + total_equity)

    # Closing entries
    closing = _closing_entries(accounts, net_income, dividends)
    post_closing = [
        {"account": a["account"], "debit": fmt(a["debit"]), "credit": fmt(a["credit"])}
        for a in accounts
        if a["category"] not in TEMPORARY and a["category"] != "retained_earnings"
    ]
    re_name = next(
        (a["account"] for a in accounts if a["category"] == "retained_earnings"),
        "Retained Earnings",
    )
    post_closing.append({
        "account": re_name,
        "debit": fmt(-ending_re) if ending_re < 0 else 0.0,
        "credit": fmt(ending_re) if ending_re >= 0 else 0.0,
    })
    pc_debits = sum(Decimal(str(r["debit"])) for r in post_closing)
    pc_credits = sum(Decimal(str(r["credit"])) for r in post_closing)

    equity_for_ratios = total_equity
    ratios = [
        {"name": "Working capital", "value": fmt(total_ca - total_cl), "kind": "money",
         "note": "Current assets − current liabilities"},
        {"name": "Current ratio", "value": _ratio(total_ca, total_cl, "x"), "kind": "x",
         "note": "Short-term liquidity; above 1.0× covers current obligations"},
        {"name": "Debt-to-equity", "value": _ratio(total_liabilities, equity_for_ratios, "x"), "kind": "x",
         "note": "Total liabilities ÷ total equity"},
        {"name": "Gross margin", "value": _ratio(gross_profit, net_sales, "pct"), "kind": "pct",
         "note": "Gross profit ÷ net sales"},
        {"name": "Operating margin", "value": _ratio(operating_income, net_sales, "pct"), "kind": "pct",
         "note": "Operating income ÷ net sales"},
        {"name": "Net profit margin", "value": _ratio(net_income, net_sales, "pct"), "kind": "pct",
         "note": "Net income ÷ net sales"},
        {"name": "Return on assets", "value": _ratio(net_income, total_assets, "pct"), "kind": "pct",
         "note": "Net income ÷ ending total assets"},
        {"name": "Return on equity", "value": _ratio(net_income, equity_for_ratios, "pct"), "kind": "pct",
         "note": "Net income ÷ ending total equity"},
        {"name": "Effective tax rate", "value": _ratio(_sum(tax), pretax, "pct"), "kind": "pct",
         "note": "Income tax expense ÷ pretax income"},
    ]

    return {
        "entity": entity,
        "period_end": period_end,
        "trial_balance": {
            "total_debits": fmt(total_debits),
            "total_credits": fmt(total_credits),
            "balanced": balanced,
            "difference": fmt(abs(total_debits - total_credits)),
            "diagnostics": diagnose_imbalance(accounts, total_debits, total_credits),
            "abnormal_balances": abnormal_balances(accounts),
            "account_count": len(accounts),
        },
        "income_statement": {
            "revenue": _ser(revenue),
            "net_sales": fmt(net_sales),
            "cogs": _ser(cogs),
            "gross_profit": fmt(gross_profit),
            "operating_expenses": _ser(opex),
            "total_operating_expenses": fmt(_sum(opex)),
            "operating_income": fmt(operating_income),
            "other": _ser(other),
            "pretax_income": fmt(pretax),
            "income_tax": _ser(tax),
            "net_income": fmt(net_income),
        },
        "retained_earnings": {
            "beginning": fmt(beginning_re),
            "net_income": fmt(net_income),
            "dividends": fmt(dividends),
            "ending": fmt(ending_re),
        },
        "balance_sheet": {
            "current_assets": _ser(current_assets),
            "total_current_assets": fmt(total_ca),
            "noncurrent_assets": _ser(noncurrent_assets),
            "total_assets": fmt(total_assets),
            "current_liabilities": _ser(current_liabs),
            "total_current_liabilities": fmt(total_cl),
            "noncurrent_liabilities": _ser(noncurrent_liabs),
            "total_liabilities": fmt(total_liabilities),
            "contributed_capital": _ser(contributed),
            "ending_retained_earnings": fmt(ending_re),
            "total_equity": fmt(total_equity),
            "total_liabilities_and_equity": fmt(total_liabilities + total_equity),
            "balances": bs_difference == ZERO,
            "difference": fmt(bs_difference),
        },
        "closing_entries": closing,
        "post_closing_trial_balance": {
            "rows": post_closing,
            "total_debits": fmt(pc_debits),
            "total_credits": fmt(pc_credits),
            "balanced": pc_debits == pc_credits,
        },
        "ratios": ratios,
    }


def _closing_entries(accounts, net_income, dividends):
    def line(account, debit=ZERO, credit=ZERO):
        return {"account": account, "debit": fmt(debit), "credit": fmt(credit)}

    re_name = next(
        (a["account"] for a in accounts if a["category"] == "retained_earnings"),
        "Retained Earnings",
    )
    entries = []

    credit_temps = [a for a in accounts if a["category"] in ("revenue", "other_income")]
    if credit_temps:
        total = sum((_natural(a) for a in credit_temps), ZERO)
        entries.append({
            "description": "Close revenue and other income accounts to Income Summary",
            "lines": [line(a["account"], debit=_natural(a)) for a in credit_temps]
                     + [line("Income Summary", credit=total)],
        })

    debit_temps = [a for a in accounts if a["category"] in (
        "contra_revenue", "cogs", "operating_expense", "other_expense", "income_tax_expense")]
    if debit_temps:
        total = sum((_natural(a) for a in debit_temps), ZERO)
        entries.append({
            "description": "Close expense and contra-revenue accounts to Income Summary",
            "lines": [line("Income Summary", debit=total)]
                     + [line(a["account"], credit=_natural(a)) for a in debit_temps],
        })

    if net_income >= 0:
        lines = [line("Income Summary", debit=net_income), line(re_name, credit=net_income)]
        desc = "Close Income Summary (net income) to Retained Earnings"
    else:
        lines = [line(re_name, debit=-net_income), line("Income Summary", credit=-net_income)]
        desc = "Close Income Summary (net loss) to Retained Earnings"
    entries.append({"description": desc, "lines": lines})

    div_accounts = [a for a in accounts if a["category"] == "dividends"]
    if div_accounts:
        entries.append({
            "description": "Close Dividends to Retained Earnings",
            "lines": [line(re_name, debit=dividends)]
                     + [line(a["account"], credit=_natural(a)) for a in div_accounts],
        })
    return entries


def run_financial_statements(csv_text: str, entity: str = "", period_end: str = "") -> dict:
    return build_statements(parse_trial_balance(csv_text), entity, period_end)
