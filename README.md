# Finance Quant Toolkit

**Live:** <https://web-production-a0dcb.up.railway.app>

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
- Installable PWA (manifest + service worker, offline app shell)
- No database. Fully stateless.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open <http://localhost:5000>.

## Tests

```bash
pip install pytest
python -m pytest tests/ -q
```

Covers the stress-test scoring thresholds and the Monte Carlo drift
correction (verifies `E[B_T] = B_0 · (1+μ)^T` within MC error).

## PWA

The app is installable as a Progressive Web App. On first load the service
worker precaches the app shell (HTML routes, CSS, JS, favicon, manifest)
so the UI works offline; API calls fall through to the network and are
never cached (results depend on user input).

- `static/manifest.webmanifest` — app metadata, icons, theme color.
- `static/service-worker.js` — precache + runtime caching strategy.
- `static/icons/` — opaque PNG icons (180/192/512 + maskable 512) with
  the brand color baked in. iOS ignores SVG apple-touch-icons and won't
  fill transparency, so PNGs are required for a clean home-screen look.
- `scripts/gen_icons.py` — regenerates the PNGs from the brand glyph
  (run after changing colors or the chart mark): `python scripts/gen_icons.py`.
- `app.py` serves the manifest and service worker at the root
  (`/manifest.webmanifest`, `/service-worker.js`) so the worker has
  site-wide scope.

The browser "Install" prompt requires HTTPS — Railway provides this
automatically. Locally the SW also works on `http://localhost`.

> **Updating the home-screen icon on iOS:** iOS caches the old icon
> aggressively. Remove the existing home-screen shortcut, then re-visit
> the site in Safari and "Add to Home Screen" again.

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
static/             style.css, favicon, per-page JS, manifest, service worker
static/icons/       PNG home-screen icons (180/192/512 + maskable)
scripts/            gen_icons.py — regenerate PNG icons from brand glyph
tests/              pytest suite
```

## What to read first

- [monte_carlo.py](monte_carlo.py) — the drift correction
  (`m = ln(1+μ) − σ²/2`) is the non-obvious bit. It makes μ behave as the
  arithmetic annual return so that `E[B_T] = B_0·(1+μ)^T`, avoiding the
  classic volatility-drag inflation bug. Derivation on the methodology page.
- [stress_test.py](stress_test.py) — the weighting rubric is explicit and
  the thresholds are documented in the methodology page.

Educational tool. Not financial advice.
