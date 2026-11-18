import os

import pytest

from app import app

HERE = os.path.join(os.path.dirname(__file__), "..", "static", "samples")


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


@pytest.mark.parametrize("path", ["/", "/financial-statements", "/bank-reconciliation",
                                  "/audit-analytics", "/methodology", "/stress-test", "/retirement",
                                  "/service-worker.js", "/manifest.webmanifest"])
def test_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_service_worker_precaches_only_real_urls(client):
    import re
    sw = client.get("/service-worker.js").get_data(as_text=True)
    for url in re.findall(r'^\s*"(/[^"]*)",?$', sw, flags=re.M):
        assert client.get(url).status_code == 200, url


def test_api_round_trips(client):
    tb = open(os.path.join(HERE, "trial_balance.csv")).read()
    r = client.post("/api/financial-statements", json={"csv": tb})
    assert r.status_code == 200 and r.get_json()["balance_sheet"]["balances"]

    r = client.post("/api/bank-reconciliation", json={
        "book_csv": open(os.path.join(HERE, "book_ledger.csv")).read(),
        "bank_csv": open(os.path.join(HERE, "bank_statement.csv")).read(),
        "book_balance": "28622.35", "bank_balance": "27219.02", "window_days": 7})
    assert r.status_code == 200 and r.get_json()["reconciled"]

    r = client.post("/api/audit-analytics", json={"csv": open(os.path.join(HERE, "ap_disbursements.csv")).read()})
    assert r.status_code == 200 and r.get_json()["threshold"]["flag"]


@pytest.mark.parametrize("url,body", [
    ("/api/financial-statements", {"csv": "nope"}),
    ("/api/bank-reconciliation", {"book_csv": "", "bank_csv": "", "book_balance": "1", "bank_balance": "1"}),
    ("/api/bank-reconciliation", {"book_csv": "x", "bank_csv": "x", "window_days": 999}),
    ("/api/audit-analytics", {"csv": ""}),
])
def test_bad_input_returns_400_with_message(client, url, body):
    r = client.post(url, json=body)
    assert r.status_code == 400 and r.get_json()["error"]


def test_non_object_body_is_400(client):
    r = client.post("/api/financial-statements", data="[1,2]", content_type="application/json")
    assert r.status_code == 400
