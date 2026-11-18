import os

import pytest

from financial_statements import run_financial_statements
from ledger_utils import InputError

SAMPLE = open(os.path.join(os.path.dirname(__file__), "..", "static", "samples", "trial_balance.csv")).read()


def test_sample_ties_out():
    r = run_financial_statements(SAMPLE)
    tb, bs = r["trial_balance"], r["balance_sheet"]
    assert tb["balanced"] and tb["total_debits"] == tb["total_credits"] == 625_300.00
    assert bs["balances"]
    assert bs["total_assets"] == bs["total_liabilities_and_equity"] == 194_700.00
    assert r["post_closing_trial_balance"]["balanced"]


def test_multi_step_income_statement():
    i = run_financial_statements(SAMPLE)["income_statement"]
    assert i["net_sales"] == 405_000.00          # 412,000 − 7,000 returns
    assert i["gross_profit"] == 167_000.00       # − 238,000 COGS
    assert i["operating_income"] == 36_100.00    # − 130,900 opex
    assert i["pretax_income"] == 31_300.00       # − 4,800 interest
    assert i["net_income"] == 24_800.00          # − 6,500 tax


def test_retained_earnings_rollforward_feeds_balance_sheet():
    r = run_financial_statements(SAMPLE)
    re = r["retained_earnings"]
    assert re["ending"] == re["beginning"] + re["net_income"] - re["dividends"] == 49_500.00
    assert r["balance_sheet"]["ending_retained_earnings"] == re["ending"]


def test_contra_assets_reduce_their_section():
    bs = run_financial_statements(SAMPLE)["balance_sheet"]
    allowance = next(l for l in bs["current_assets"] if "Allowance" in l["account"])
    assert allowance["amount"] == -1_400.00
    assert bs["total_current_assets"] == 108_700.00  # 42.5 + 28 − 1.4 + 36 + 3.6


def test_every_closing_entry_balances_and_zeroes_income_summary():
    entries = run_financial_statements(SAMPLE)["closing_entries"]
    assert len(entries) == 4
    income_summary = 0.0
    for e in entries:
        assert round(sum(l["debit"] for l in e["lines"]), 2) == round(sum(l["credit"] for l in e["lines"]), 2)
        for l in e["lines"]:
            if l["account"] == "Income Summary":
                income_summary += l["credit"] - l["debit"]
    assert round(income_summary, 2) == 0.0


def test_transposition_is_diagnosed():
    bad = SAMPLE.replace("Rent Expense,operating_expense,24000.00", "Rent Expense,operating_expense,42000.00")
    tb = run_financial_statements(bad)["trial_balance"]
    assert not tb["balanced"] and tb["difference"] == 18_000.00
    text = " ".join(tb["diagnostics"])
    assert "divisible by 9" in text
    assert "Rent Expense ($42,000.00 → $24,000.00)" in text


def test_wrong_side_posting_is_diagnosed():
    bad = SAMPLE.replace("Utilities Expense,operating_expense,6200.00,", "Utilities Expense,operating_expense,,6200.00")
    tb = run_financial_statements(bad)["trial_balance"]
    assert tb["difference"] == 12_400.00
    assert any("twice Utilities Expense" in d for d in tb["diagnostics"])
    assert tb["abnormal_balances"][0]["account"] == "Utilities Expense"


def test_decimal_precision_no_float_drift():
    csv = "Account,Category,Debit,Credit\nCash,current_asset,0.10,\nSupplies,current_asset,0.20,\nCommon Stock,equity,,0.30\n"
    assert run_financial_statements(csv)["trial_balance"]["balanced"]  # 0.1 + 0.2 == 0.3 here


def test_net_loss_closes_with_debit_to_retained_earnings():
    csv = ("Account,Category,Debit,Credit\nCash,current_asset,500,\nCommon Stock,equity,,1000\n"
           "Retained Earnings,retained_earnings,,0\nRevenue,revenue,,200\nRent Expense,operating_expense,700,\n")
    r = run_financial_statements(csv)
    assert r["income_statement"]["net_income"] == -500.00
    last = r["closing_entries"][-1]
    assert "net loss" in last["description"]
    assert last["lines"][0]["account"] == "Retained Earnings" and last["lines"][0]["debit"] == 500.00
    assert r["balance_sheet"]["balances"]


@pytest.mark.parametrize("csv,msg", [
    ("Account,Debit,Credit\nCash,1,\n", "Missing column"),
    ("Account,Category,Debit,Credit\nCash,widgets,1,\n", "Unknown category"),
    ("Account,Category,Debit,Credit\nCash,current_asset,abc,\n", "Could not read debit"),
    ("Account,Category,Debit,Credit\nCash,current_asset,-5,\n", "positive"),
])
def test_bad_input_is_rejected_clearly(csv, msg):
    with pytest.raises(InputError, match=msg):
        run_financial_statements(csv)


def test_accepts_accounting_number_formats():
    csv = 'Account,Category,Debit,Credit\nCash,Current Asset,"$1,250.00",\nCommon Stock,common stock,,"1,250"\n'
    assert run_financial_statements(csv)["trial_balance"]["balanced"]
