# Finance Quant Toolkit

Two quantitative personal-finance tools under one Flask app:

1. **Financial Stress Test** — scores a user's balance sheet against five
   adverse scenarios (job loss, market drawdown, emergency expense, debt
   service, inflation shock) and returns a weighted resilience score.
2. **Monte Carlo Retirement Simulator** — runs 10,000 geometric Brownian
   motion paths on a savings+contribution model and reports percentile
   bands, a distribution histogram, and probability of meeting a user goal.

A `/methodology` page explains every assumption and formula in plain
English — read that first if you're reviewing this for depth over polish.

## Stack

- Python 3.12, Flask 3, NumPy, Gunicorn
- Vanilla JS + Chart.js (CDN)
- No database. Fully stateless.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open <http://localhost:5000>.

## Deploy (Railway)

The repo includes `railway.json`, `Procfile`, and `runtime.txt`. Push to a
Railway project; enable Serverless in the service settings. The app is
stateless and cold-starts quickly, so serverless pricing is near-zero at
portfolio-traffic levels.

## Layout

```
app.py              Flask routes + JSON APIs
stress_test.py      Scenario scoring logic
monte_carlo.py      NumPy GBM engine
templates/          Jinja templates (base, index, stress, retirement, methodology)
static/             style.css, per-page JS
```

## What to read first

- [monte_carlo.py](monte_carlo.py) — the geometric-return drift correction
  (`mu_geo = mu - 0.5 * sigma^2`) is the non-obvious bit. The methodology
  page has the derivation.
- [stress_test.py](stress_test.py) — the weighting rubric is explicit and
  the thresholds are documented in the methodology page.

Educational tool. Not financial advice.
