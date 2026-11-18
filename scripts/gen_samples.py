"""Regenerate the synthetic AP disbursement sample used by /audit-analytics.

Deterministic (fixed seed). The base population is lognormal, which follows
Benford's Law closely. Three red flags are planted on purpose:

  1. One vendor billing repeatedly just under the $5,000 approval limit
  2. Duplicate invoices paid twice
  3. A handful of identical round-dollar payments

Run:  python scripts/gen_samples.py
"""

import csv
import os
from datetime import date, timedelta

import numpy as np

rng = np.random.default_rng(20261031)
OUT = os.path.join(os.path.dirname(__file__), "..", "static", "samples", "ap_disbursements.csv")

VENDORS = [
    "Harbor Industrial Supply", "Westline Distributors", "City Utilities",
    "Keystone Insurance", "Northgate Freight", "Summit Office Products",
    "Calder & Sons", "Pioneer Packaging", "Redwood IT Services",
    "Lakeshore Maintenance", "Atlas Fleet Fuel", "Meridian Staffing",
    "Granite Equipment Rental", "Bluewater Janitorial", "Cedar Point Legal",
    "Ironclad Security", "Evergreen Landscaping", "Union Telecom",
    "Prairie Electric Co-op", "Silverline Software", "Ridge Valley Printing",
    "Copperfield Chemicals", "Tidewater Logistics", "Oakmont Catering",
]
SHELL_VENDOR = "Brightline Consulting LLC"
START = date(2026, 1, 1)

rows = []
inv = 70000
for _ in range(2200):
    amount = round(float(rng.lognormal(mean=6.9, sigma=1.45)), 2)
    if amount < 1:
        continue
    inv += int(rng.integers(1, 4))
    rows.append([START + timedelta(days=int(rng.integers(0, 304))),
                 VENDORS[int(rng.integers(0, len(VENDORS)))], f"INV-{inv}", amount])

# 1. Just under the $5,000 approval limit
for _ in range(42):
    inv += 1
    rows.append([START + timedelta(days=int(rng.integers(0, 304))), SHELL_VENDOR,
                 f"BC-{inv}", round(float(rng.uniform(4650, 4995)), 2)])

# 2. Duplicate invoices
for r in [rows[i] for i in rng.choice(len(rows) - 42, size=7, replace=False)]:
    dup = list(r)
    dup[0] = r[0] + timedelta(days=int(rng.integers(9, 40)))
    rows.append(dup)

# 3. Repeated round-dollar payments
for _ in range(5):
    rows.append([START + timedelta(days=int(rng.integers(0, 304))),
                 "Cedar Point Legal", f"RET-{int(rng.integers(100, 999))}", 2500.00])

rows.sort(key=lambda r: r[0])
with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Date", "Vendor", "Invoice", "Amount"])
    for d, v, i, a in rows:
        w.writerow([d.strftime("%m/%d/%Y"), v, i, f"{a:.2f}"])
print(f"wrote {len(rows)} rows to {os.path.normpath(OUT)}")
