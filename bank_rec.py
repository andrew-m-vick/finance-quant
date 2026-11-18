"""Bank reconciliation: match the cash ledger to the bank statement.

Matching runs in three passes, strongest evidence first:

  1. Check/reference number — same check number on both sides. If the
     amounts disagree, it is flagged as a recording error (the bank's
     cleared amount is treated as correct, since it is the amount that
     actually left the account).
  2. Exact amount within a date window — for deposits and electronic items
     that carry no shared reference. Ties go to the nearest date.
  3. Transposition scan — leftover book/bank pairs within the window whose
     amounts are digit permutations of each other (e.g. 492.00 vs 429.00).

Everything still unmatched becomes a reconciling item:

  bank side  — deposits in transit (+), outstanding checks (−)
  book side  — bank credits not yet recorded (+), bank charges/NSF (−),
               and corrections of recording errors (±)

Book-side items need an adjusting journal entry; bank-side items do not.
"""

from datetime import timedelta
from decimal import Decimal

from ledger_utils import InputError, ZERO, fmt, parse_amount, parse_date, read_csv

COLUMNS = ["Date", "Ref", "Description", "Amount"]

# keyword -> (account to debit/credit opposite Cash, explanation)
BANK_ITEM_RULES = [
    (("nsf", "returned item", "returned check", "insufficient"),
     "Accounts Receivable", "Customer check returned NSF — re-establish the receivable"),
    (("interest",), "Interest Revenue", "Interest earned on the account"),
    (("service charge", "service fee", "monthly fee", "maintenance fee", "bank fee", "wire fee"),
     "Bank Service Charges Expense", "Bank fee not yet recorded"),
    (("collection", "note collected", "note receivable"),
     "Notes Receivable", "Bank collected a note on the company's behalf"),
    (("ach", "autopay", "auto pay", "electronic"),
     "Accounts Payable", "Electronic payment not yet recorded — confirm the payee"),
]


def _parse_side(text, label):
    rows = read_csv(text, COLUMNS)
    items = []
    for row_no, r in rows:
        try:
            amount = parse_amount(r["amount"], row=row_no)
            when = parse_date(r["date"], row=row_no)
        except InputError as e:
            raise InputError(f"{label}: {e}") from None
        if amount == ZERO:
            continue
        items.append({
            "id": f"{label[:4].lower()}-{row_no}",
            "row": row_no,
            "date": when,
            "ref": r["ref"].lstrip("#").strip(),
            "description": r["description"],
            "amount": amount,
        })
    return items


def _is_permutation(a: Decimal, b: Decimal) -> bool:
    da, db = str(abs(int(a * 100))), str(abs(int(b * 100)))
    return a != b and sorted(da) == sorted(db)


def _classify_bank_item(item):
    text = item["description"].lower()
    for keywords, account, why in BANK_ITEM_RULES:
        if any(k in text for k in keywords):
            return account, why
    if item["amount"] > 0:
        return "Suspense (investigate)", "Unidentified bank credit — research before recording"
    return "Suspense (investigate)", "Unidentified bank debit — research before recording"


def _ser_item(i):
    return {
        "date": i["date"].strftime("%m/%d/%Y"),
        "ref": i["ref"],
        "description": i["description"],
        "amount": fmt(i["amount"]),
    }


def reconcile(book_csv, bank_csv, book_balance, bank_balance, window_days=7) -> dict:
    book = _parse_side(book_csv, "Book ledger")
    bank = _parse_side(bank_csv, "Bank statement")
    book_balance = parse_amount(book_balance, field="book ending balance")
    bank_balance = parse_amount(bank_balance, field="bank ending balance")
    window = timedelta(days=int(window_days))

    open_book = {i["id"]: i for i in book}
    open_bank = {i["id"]: i for i in bank}
    matches, errors = [], []

    def take(b, k, method):
        open_book.pop(b["id"]), open_bank.pop(k["id"])
        matches.append({"method": method, "book": _ser_item(b), "bank": _ser_item(k),
                        "days_to_clear": (k["date"] - b["date"]).days})

    # Pass 1: shared reference numbers
    for b in list(open_book.values()):
        # Only real document numbers count; generic tags like "DEP" don't.
        if not any(ch.isdigit() for ch in b["ref"]):
            continue
        k = next((k for k in open_bank.values() if k["ref"] == b["ref"]), None)
        if k is None:
            continue
        if k["amount"] == b["amount"]:
            take(b, k, "Reference #")
        else:
            open_book.pop(b["id"]), open_bank.pop(k["id"])
            errors.append({"book": b, "bank": k, "reason": f"Ref #{b['ref']} recorded at "
                           f"${abs(b['amount']):,.2f} but cleared at ${abs(k['amount']):,.2f}"})

    # Pass 2: exact amount, nearest date within the window
    for b in sorted(open_book.values(), key=lambda i: i["date"]):
        candidates = [k for k in open_bank.values()
                      if k["amount"] == b["amount"]
                      # bank may post up to 2 days before the book date
                      and -timedelta(days=2) <= k["date"] - b["date"] <= window]
        if candidates:
            k = min(candidates, key=lambda k: abs((k["date"] - b["date"]).days))
            take(b, k, "Amount + date")

    # Pass 3: transposition scan
    for b in list(open_book.values()):
        k = next((k for k in open_bank.values()
                  if (k["amount"] > 0) == (b["amount"] > 0)
                  and _is_permutation(b["amount"], k["amount"])
                  and abs((k["date"] - b["date"]).days) <= window.days), None)
        if k:
            open_book.pop(b["id"]), open_bank.pop(k["id"])
            errors.append({"book": b, "bank": k, "reason":
                           f"${abs(b['amount']):,.2f} vs ${abs(k['amount']):,.2f} — "
                           "same digits in a different order (likely transposition)"})

    # Reconciling items
    deposits_in_transit = [i for i in open_book.values() if i["amount"] > 0]
    outstanding_checks = [i for i in open_book.values() if i["amount"] < 0]
    bank_credits = [i for i in open_bank.values() if i["amount"] > 0]
    bank_debits = [i for i in open_bank.values() if i["amount"] < 0]

    dit_total = sum((i["amount"] for i in deposits_in_transit), ZERO)
    oc_total = sum((-i["amount"] for i in outstanding_checks), ZERO)
    credits_total = sum((i["amount"] for i in bank_credits), ZERO)
    debits_total = sum((-i["amount"] for i in bank_debits), ZERO)
    error_total = sum((e["bank"]["amount"] - e["book"]["amount"] for e in errors), ZERO)

    adjusted_bank = bank_balance + dit_total - oc_total
    adjusted_book = book_balance + credits_total - debits_total + error_total
    difference = adjusted_bank - adjusted_book

    # Adjusting journal entries (book side only)
    entries = []
    for i in bank_credits + bank_debits:
        account, why = _classify_bank_item(i)
        amt = abs(i["amount"])
        lines = ([("Cash", amt, ZERO), (account, ZERO, amt)] if i["amount"] > 0
                 else [(account, amt, ZERO), ("Cash", ZERO, amt)])
        entries.append({"memo": f"{i['description']} ({i['date']:%m/%d}) — {why}", "lines": lines})
    for e in errors:
        delta = e["bank"]["amount"] - e["book"]["amount"]
        is_payment = e["book"]["amount"] < 0
        offset = ("Accounts Payable / original expense account" if is_payment
                  else "Accounts Receivable / original revenue account")
        amt = abs(delta)
        lines = ([("Cash", amt, ZERO), (offset, ZERO, amt)] if delta > 0
                 else [(offset, amt, ZERO), ("Cash", ZERO, amt)])
        entries.append({"memo": f"Correct recording error — {e['reason']}", "lines": lines})

    def ser_entry(en):
        return {"memo": en["memo"], "lines": [
            {"account": a, "debit": fmt(d), "credit": fmt(c)} for a, d, c in en["lines"]]}

    return {
        "reconciled": difference == ZERO,
        "difference": fmt(difference),
        "bank": {
            "ending_balance": fmt(bank_balance),
            "deposits_in_transit": [_ser_item(i) for i in deposits_in_transit],
            "deposits_in_transit_total": fmt(dit_total),
            "outstanding_checks": [_ser_item(i) for i in outstanding_checks],
            "outstanding_checks_total": fmt(oc_total),
            "adjusted_balance": fmt(adjusted_bank),
        },
        "book": {
            "ending_balance": fmt(book_balance),
            "bank_credits": [_ser_item(i) for i in bank_credits],
            "bank_credits_total": fmt(credits_total),
            "bank_debits": [_ser_item(i) for i in bank_debits],
            "bank_debits_total": fmt(debits_total),
            "errors": [{"reason": e["reason"], "book": _ser_item(e["book"]), "bank": _ser_item(e["bank"]),
                        "adjustment": fmt(e["bank"]["amount"] - e["book"]["amount"])} for e in errors],
            "errors_total": fmt(error_total),
            "adjusted_balance": fmt(adjusted_book),
        },
        "matches": matches,
        "match_rate": round(100 * len(matches) / max(len(book), 1), 1),
        "adjusting_entries": [ser_entry(e) for e in entries],
        "counts": {"book": len(book), "bank": len(bank), "matched": len(matches)},
    }
