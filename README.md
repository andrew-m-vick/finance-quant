# Accounting Portfolio

**Live:** <https://web-production-a0dcb.up.railway.app>

A portfolio site for an accounting student, built around three working
accounting tools, each loaded with a fictional sample company:

1. **Trial Balance → Financial Statements** (`/financial-statements`):
   adjusted TB in; multi-step income statement, statement of retained
   earnings, classified balance sheet, closing entries, post-closing TB, and
   ratios out. When the TB doesn't balance, it diagnoses why: divisible-by-9
   transpositions (with the specific digit swap), wrong-side postings,
   omissions, and abnormal balances.
2. **Bank Reconciliation** (`/bank-reconciliation`): matches the cash
   ledger to the bank statement (check number, then amount within a date
   window, then transposition scan), classifies deposits in transit,
   outstanding checks, NSF items, fees and recording errors, and drafts the
   adjusting journal entries.
3. **Audit Data Analytics** (`/audit-analytics`): full-population testing
   of AP disbursements: Benford first-digit and first-two-digits tests (MAD
   conformity per Nigrini, chi-square, per-bin z), approval-limit clustering,
   and duplicate-payment detection, with recommended audit procedures.

Two earlier quantitative projects are kept as a secondary section: a
**Financial Stress Test** and a **Monte Carlo Retirement Simulator**
(10,000 GBM paths).

All money math uses `decimal.Decimal` rounded to the cent, so ledgers tie
exactly with no floating-point drift.

## Personalizing

Everything personal (name, school, CPA plan, coursework, skills,
experience) lives in **[about_me.py](about_me.py)**. Any value still in
`[square brackets]` is a placeholder; while one remains, every page shows a
yellow "unfinished profile" banner. To add a resume, drop it at
`static/resume.pdf` and the Résumé buttons appear automatically.

A `/methodology` page explains every accounting rule, statistical test, and
assumption, with sources. Read that first if you're reviewing for depth.

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

Tests assert accounting identities rather than just "it runs": debits =
credits, A = L + E, every closing entry balances and Income Summary nets to
zero, post-closing TB balances, adjusted bank = adjusted book, and Benford
tests pass on natural (lognormal) data while catching the planted fraud in
the sample file. Plus the original stress-test thresholds and the Monte
Carlo drift correction (`E[B_T] = B_0 · (1+μ)^T` within MC error).

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
app.py                   Flask routes + JSON APIs
about_me.py              All personal/profile content (edit this)
ledger_utils.py          Decimal money parsing, dates, CSV reading
financial_statements.py  TB → statements, closing entries, TB error diagnostics
bank_rec.py              Three-pass matching + reconciliation + AJEs
benford.py               Benford tests, threshold + duplicate analytics
stress_test.py           Scenario scoring logic
monte_carlo.py           NumPy GBM engine
templates/               Jinja templates
static/                  style.css, per-page JS, manifest, service worker
static/samples/          Fictional sample data for each tool
static/icons/            PNG home-screen icons (180/192/512 + maskable)
scripts/                 gen_icons.py, gen_samples.py (rebuilds the AP sample)
tests/                   pytest suite
```

## What to read first

- [financial_statements.py](financial_statements.py): `diagnose_imbalance`
  automates the manual TB error-finding techniques (÷9, ÷2, = balance).
- [bank_rec.py](bank_rec.py): matching passes are ordered by strength of
  evidence; book-side vs bank-side classification drives which items need
  adjusting entries.
- [benford.py](benford.py): why MAD, not chi-square, is the headline
  verdict on large populations.
- [monte_carlo.py](monte_carlo.py) — the drift correction
  (`m = ln(1+μ) − σ²/2`) is the non-obvious bit. It makes μ behave as the
  arithmetic annual return so that `E[B_T] = B_0·(1+μ)^T`, avoiding the
  classic volatility-drag inflation bug. Derivation on the methodology page.
- [stress_test.py](stress_test.py) — the weighting rubric is explicit and
  the thresholds are documented in the methodology page.

Sample companies and figures are fictional. Not financial, tax, or audit advice.
