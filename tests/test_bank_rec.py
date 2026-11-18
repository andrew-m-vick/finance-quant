import os

from bank_rec import reconcile

HERE = os.path.join(os.path.dirname(__file__), "..", "static", "samples")
BOOK = open(os.path.join(HERE, "book_ledger.csv")).read()
BANK = open(os.path.join(HERE, "bank_statement.csv")).read()


def run(**kw):
    return reconcile(kw.get("book", BOOK), kw.get("bank", BANK),
                     kw.get("book_balance", "28,622.35"), kw.get("bank_balance", "27,219.02"))


def test_sample_reconciles_to_the_cent():
    r = run()
    assert r["reconciled"]
    assert r["bank"]["adjusted_balance"] == r["book"]["adjusted_balance"] == 27_928.77


def test_reconciling_items_are_classified():
    r = run()
    assert [i["amount"] for i in r["bank"]["deposits_in_transit"]] == [5640.00]
    assert sorted(i["ref"] for i in r["bank"]["outstanding_checks"]) == ["1045", "1046"]
    assert r["bank"]["outstanding_checks_total"] == 4_930.25
    assert r["book"]["bank_credits_total"] == 18.42   # interest
    assert r["book"]["bank_debits_total"] == 775.00   # NSF 740 + fee 35


def test_check_number_mismatch_is_a_recording_error():
    errors = run()["book"]["errors"]
    assert len(errors) == 1
    assert errors[0]["book"]["ref"] == "1043"
    assert errors[0]["adjustment"] == 63.00  # booked 492, cleared 429


def test_adjusting_entries_balance_and_map_accounts():
    entries = run()["adjusting_entries"]
    accounts = {l["account"] for e in entries for l in e["lines"]}
    assert {"Interest Revenue", "Accounts Receivable", "Bank Service Charges Expense"} <= accounts
    for e in entries:
        assert sum(l["debit"] for l in e["lines"]) == sum(l["credit"] for l in e["lines"])
    nsf = next(e for e in entries if "NSF" in e["memo"])
    assert nsf["lines"][0] == {"account": "Accounts Receivable", "debit": 740.0, "credit": 0.0}


def test_wrong_balance_surfaces_difference():
    r = run(bank_balance="27,319.02")
    assert not r["reconciled"] and r["difference"] == 100.00


def test_generic_refs_do_not_cross_match():
    # Two deposits tagged DEP with different amounts must match by amount, not ref.
    book = "Date,Ref,Description,Amount\n10/01/2026,DEP,A,100.00\n10/02/2026,DEP,B,250.00\n"
    bank = "Date,Ref,Description,Amount\n10/02/2026,DEP,Dep,250.00\n10/03/2026,DEP,Dep,100.00\n"
    r = reconcile(book, bank, "350", "350")
    assert r["reconciled"] and r["book"]["errors"] == [] and len(r["matches"]) == 2


def test_transposition_without_reference_is_caught():
    book = "Date,Ref,Description,Amount\n10/05/2026,,Vendor EFT,-1540.00\n"
    bank = "Date,Ref,Description,Amount\n10/06/2026,,ACH debit,-1450.00\n"
    r = reconcile(book, bank, "-1540.00", "-1450.00")
    assert r["reconciled"]
    assert r["book"]["errors"][0]["adjustment"] == 90.00
