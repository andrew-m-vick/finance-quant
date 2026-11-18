(() => {
  const form = document.getElementById("aa-form");
  const csv = document.getElementById("aa-csv");
  const errBox = document.getElementById("aa-error");
  const results = document.getElementById("aa-results");
  const { money, esc } = Acct;
  const SAMPLE = "/static/samples/ap_disbursements.csv";

  // Validated categorical slots 1–2 (dataviz reference palette, light surface).
  const C = { observed: "#2a78d6", expected: "#eb6834", grid: "#eceef1", text: "#5b6670", surface: "#ffffff" };
  const charts = {};

  document.getElementById("load-sample").addEventListener("click", async () => {
    csv.value = await Acct.loadText(SAMPLE);
    form.requestSubmit();
  });
  Acct.fileInto(document.getElementById("aa-file"), csv);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    Acct.showError(errBox, null);
    const btn = form.querySelector("button.primary");
    btn.disabled = true; btn.textContent = "Running…";
    try {
      render(await Acct.post("/api/audit-analytics", Object.fromEntries(new FormData(form).entries())));
    } catch (err) {
      results.classList.add("hidden");
      Acct.showError(errBox, err);
    } finally {
      btn.disabled = false; btn.textContent = "Run analytics";
    }
  });

  const isConform = (c) => c.startsWith("Close") || c.startsWith("Acceptable");
  const fmtInt = (n) => n.toLocaleString("en-US");
  const pval = (p) => (p < 0.0001 ? "< 0.0001" : p.toFixed(4));

  function tiles(r) {
    const f1 = r.first_digit, f2 = r.first_two_digits, t = r.threshold;
    const tile = (k, v, s, cls = "") => `<div class="tile ${cls}"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
    return [
      tile("Payments tested", fmtInt(r.count_tested), `${money(r.total_dollars, { dollar: true })} total · ${r.excluded_under_10} under $10 excluded`),
      tile("First digit", isConform(f1.conformity) ? "✓ Conforms" : "▲ " + f1.conformity.replace(" conformity", ""), `MAD ${f1.mad.toFixed(4)} · ${f1.conformity}`, isConform(f1.conformity) ? "good" : "warn"),
      tile("First two digits", isConform(f2.conformity) ? "✓ Conforms" : "▲ " + f2.conformity.replace(" conformity", ""), `MAD ${f2.mad.toFixed(4)} · ${f2.conformity}`, isConform(f2.conformity) ? "good" : "warn"),
      t ? tile("Just under limit", t.flag ? `▲ ${t.ratio.toFixed(2)}×` : `✓ ${t.ratio.toFixed(2)}×`, `${t.band_below} vs ${t.band_above} above · expect ≈${t.expected_ratio.toFixed(2)}×`, t.flag ? "bad" : "good") : "",
      tile("Duplicate invoices", r.duplicate_invoices.length ? `▲ ${r.duplicate_invoices.length}` : "✓ 0",
        r.duplicate_invoices.length ? `${money(r.duplicate_invoice_exposure, { dollar: true })} potential overpayment` : "Vendor + invoice # unique", r.duplicate_invoices.length ? "bad" : "good"),
    ].join("");
  }

  function findings(r) {
    const out = [];
    const t = r.threshold;
    if (t && t.flag) {
      const v = t.top_vendors[0];
      const share = Math.round((100 * v.count) / t.band_below);
      out.push({ high: true,
        title: `Payments cluster just below the ${money(t.limit, { dollar: true })} approval limit`,
        body: `${t.band_below} payments fall in the 10% band below the limit versus ${t.band_above} in the 10% band above, a ${t.ratio.toFixed(2)}× ratio against ≈${t.expected_ratio.toFixed(2)}× expected under Benford. ${esc(v.vendor)} accounts for ${v.count} (${share}%) of them.`,
        proc: `Procedures: vouch ${esc(v.vendor)} payments to invoices, receiving reports, and contracts; confirm vendor existence (W-9, address, bank account) and compare against the employee master file; check whether one approver signed off on all of them; look for invoice splitting (same day, sequential invoice numbers).` });
    }
    if (r.duplicate_invoices.length) {
      out.push({ high: true,
        title: `${r.duplicate_invoices.length} invoice${r.duplicate_invoices.length > 1 ? "s" : ""} paid more than once`,
        body: `Same vendor and invoice number paid twice; ${money(r.duplicate_invoice_exposure, { dollar: true })} in potential overpayments.`,
        proc: "Procedures: pull both payments and the invoice, request vendor credit memos or refunds, and test the AP system's duplicate-invoice control (is the check disabled or overridable?)." });
    }
    const f2 = r.first_two_digits;
    if (f2.spikes.length) {
      const f1ok = isConform(r.first_digit.conformity);
      out.push({ high: false,
        title: `First-two-digit spikes at ${f2.spikes.slice(0, 5).join(", ")}`,
        body: `These leading digits appear significantly more often than Benford predicts (|z| > 1.96).${f1ok ? " The first-digit test alone rates this file as conforming; only the finer first-two-digit test shows the anomaly." : ""}`,
        proc: `Procedures: filter the population to amounts beginning ${f2.spikes.slice(0, 3).join(", ")}; summarize by vendor and approver; scan for round, repeated, or just-under-threshold amounts.` });
    }
    const rep = r.repeated_amounts.filter((d) => d.count >= 3);
    if (rep.length) {
      const d = rep[0];
      out.push({ high: false,
        title: `Repeated identical payments: ${esc(d.vendor)}, ${d.count} × ${money(d.amount, { dollar: true })}`,
        body: "Identical amounts to one vendor may be a legitimate retainer or a recurring fictitious charge.",
        proc: "Procedures: agree to a signed engagement letter or contract and evidence that services were received." });
    }
    r.warnings.forEach((w) => out.push({ high: false, title: "Sample size", body: esc(w), proc: "" }));
    if (!out.length) {
      out.push({ high: false, title: "No exceptions noted", body: "The population conforms to Benford's Law, with no threshold clustering or duplicate payments.", proc: "Conformity does not prove the absence of fraud; it means these specific red flags are absent." });
    }
    return `<h2>Findings</h2>` + out.map((f) => `<div class="finding${f.high ? " high" : ""}">
      <div class="f-title">${f.high ? "▲ High: " : "● "}${f.title}</div><div class="f-body">${f.body}</div>
      ${f.proc ? `<div class="f-proc">${f.proc}</div>` : ""}</div>`).join("");
  }

  function chart(id, test, { thin }) {
    if (charts[id]) charts[id].destroy();
    const labels = test.rows.map((r) => String(r.digits));
    charts[id] = new Chart(document.getElementById(id), {
      data: {
        labels,
        datasets: [
          { type: "bar", label: "Observed", data: test.rows.map((r) => r.observed_pct),
            backgroundColor: C.observed, borderRadius: { topLeft: 4, topRight: 4 }, borderSkipped: "start",
            maxBarThickness: 24, barPercentage: thin ? 0.85 : 0.7, categoryPercentage: 1, order: 2 },
          { type: "line", label: "Benford expected", data: test.rows.map((r) => r.expected_pct),
            borderColor: C.expected, backgroundColor: C.expected, borderWidth: 2,
            pointRadius: thin ? 0 : 4, pointHoverRadius: 5, pointBorderColor: C.surface, pointBorderWidth: 2,
            tension: 0, order: 1 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "top", align: "end", labels: { color: C.text, boxWidth: 12, boxHeight: 12, usePointStyle: false } },
          tooltip: {
            callbacks: {
              title: (items) => `Leading digit${thin ? "s" : ""} ${items[0].label}`,
              label: (item) => {
                const row = test.rows[item.dataIndex];
                return item.datasetIndex === 0
                  ? `Observed: ${row.observed_pct.toFixed(2)}% (${fmtInt(row.observed)})`
                  : `Expected: ${row.expected_pct.toFixed(2)}% (${row.expected.toFixed(0)})`;
              },
              afterBody: (items) => {
                const row = test.rows[items[0].dataIndex];
                return row.flag ? `z = ${row.z.toFixed(2)}: significantly over-represented` : `z = ${row.z.toFixed(2)}`;
              },
            },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: C.text, autoSkip: thin, maxRotation: 0, autoSkipPadding: 6 } },
          y: { beginAtZero: true, grid: { color: C.grid }, border: { display: false },
               ticks: { color: C.text, callback: (v) => `${v}%` } },
        },
      },
    });
  }

  function render(r) {
    results.classList.remove("hidden");
    document.getElementById("aa-tiles").innerHTML = tiles(r);
    document.getElementById("findings-panel").innerHTML = findings(r);

    const f1 = r.first_digit, f2 = r.first_two_digits;
    document.getElementById("f1-sub").textContent =
      `MAD ${f1.mad.toFixed(4)} (${f1.conformity}) · χ² = ${f1.chi_square} on ${f1.df} df, p ${pval(f1.p_value)}`;
    document.getElementById("f2-sub").textContent =
      `MAD ${f2.mad.toFixed(4)} (${f2.conformity}) · χ² = ${f2.chi_square} on ${f2.df} df, p ${pval(f2.p_value)}` +
      (f2.spikes.length ? ` · Over-represented: ${f2.spikes.join(", ")}` : "");
    chart("f2-chart", f2, { thin: true });
    chart("f1-chart", f1, { thin: false });

    document.getElementById("f1-table").innerHTML = `<table class="grid"><thead><tr><th>Digit</th>
      <th class="num">Count</th><th class="num">Actual</th><th class="num">Benford</th><th class="num">z</th><th></th></tr></thead><tbody>
      ${f1.rows.map((x) => `<tr class="${x.flag ? "flag" : ""}"><td>${x.digits}</td><td class="num">${fmtInt(x.observed)}</td>
        <td class="num">${x.observed_pct.toFixed(1)}%</td><td class="num">${x.expected_pct.toFixed(1)}%</td>
        <td class="num">${x.z.toFixed(2)}</td><td class="small">${x.flag ? "▲ Over" : x.under ? "▼ Under" : ""}</td></tr>`).join("")}
      </tbody></table>`;

    document.getElementById("dup-panel").innerHTML = `<h2>Duplicate payments</h2>` + (r.duplicate_invoices.length
      ? `<div class="table-scroll"><table class="grid"><thead><tr><th>Vendor</th><th>Invoice</th><th class="num">Paid</th><th class="num">Amount</th><th>Rows</th></tr></thead><tbody>
         ${r.duplicate_invoices.map((d) => `<tr class="flag"><td>${esc(d.vendor)}</td><td style="white-space:nowrap">${esc(d.invoice)}</td><td class="num">${d.count}</td>
           <td class="num">${money(d.amount)}</td><td class="small" style="white-space:nowrap">${d.rows.join(", ")}</td></tr>`).join("")}
         </tbody></table></div>`
      : `<p class="muted">No vendor + invoice number pairs were paid more than once${csv.value.toLowerCase().includes("invoice") ? "" : " (add Vendor and Invoice columns to run this test)"}.</p>`)
      + (r.repeated_amounts.length ? `<h3>Most-repeated vendor amounts</h3><table class="grid"><tbody>
         ${r.repeated_amounts.slice(0, 5).map((d) => `<tr><td>${esc(d.vendor)}</td><td class="num">${d.count} × ${money(d.amount)}</td></tr>`).join("")}
         </tbody></table>` : "");

    const t = r.threshold;
    document.getElementById("thr-panel").innerHTML = `<h2>Approval-limit test</h2>` + (t
      ? `<p class="small">Limit ${money(t.limit, { dollar: true })}. Payments ${money(t.limit * 0.9, { dollar: true })}–${money(t.limit - 0.01, { dollar: true })}: <strong>${t.band_below}</strong>.
         Payments ${money(t.limit, { dollar: true })}–${money(t.limit * 1.1 - 0.01, { dollar: true })}: <strong>${t.band_above}</strong>.</p>
         <p class="small">Under Benford the band below should hold about ${t.expected_ratio.toFixed(2)}× the band above. Observed: <strong>${t.ratio.toFixed(2)}×</strong>
         ${t.flag ? "<strong style='color:var(--danger)'>▲ flagged</strong>" : "✓ within range"}.</p>
         <h3>Vendors in the band just below</h3><table class="grid"><tbody>
         ${t.top_vendors.map((v) => `<tr><td>${esc(v.vendor)}</td><td class="num">${v.count}</td></tr>`).join("")}</tbody></table>`
      : `<p class="muted">Enter an approval limit to run this test.</p>`);

    results.scrollIntoView({ behavior: "smooth", block: "start" });
  }
})();
