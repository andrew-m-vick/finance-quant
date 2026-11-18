(() => {
  const form = document.getElementById("tb-form");
  const csv = document.getElementById("tb-csv");
  const errBox = document.getElementById("tb-error");
  const results = document.getElementById("tb-results");
  const SAMPLE = "/static/samples/trial_balance.csv";
  const { money, esc } = Acct;

  async function load(withError) {
    let text = await Acct.loadText(SAMPLE);
    if (withError) {
      // Transposition: rent of 24,000 keyed as 42,000.
      text = text.replace("Rent Expense,operating_expense,24000.00", "Rent Expense,operating_expense,42000.00");
    }
    csv.value = text;
    form.requestSubmit();
  }
  document.getElementById("load-sample").addEventListener("click", () => load(false));
  document.getElementById("load-error").addEventListener("click", () => load(true));
  Acct.fileInto(document.getElementById("tb-file"), csv);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    Acct.showError(errBox, null);
    const body = Object.fromEntries(new FormData(form).entries());
    try {
      render(await Acct.post("/api/financial-statements", body), body);
    } catch (err) {
      results.classList.add("hidden");
      Acct.showError(errBox, err);
    }
  });

  // ---- statement row builders -------------------------------------------
  const head = (entity, title, period) => `
    <div class="stmt-head">
      <div class="entity">${esc(entity || "Company")}</div>
      <div class="title">${esc(title)}</div>
      <div class="period">${esc(period)}</div>
    </div>`;
  const section = (label) => `<tr class="section"><td colspan="3">${esc(label)}</td></tr>`;
  // Amounts in the inner column ("line") and outer column ("total").
  const linesInner = (items, firstDollar = true) => items.map((l, i) => `
    <tr class="line"><td>${esc(l.account)}</td>
      <td class="amt${i === items.length - 1 && items.length > 1 ? " underline" : ""}">${money(l.amount, { dollar: firstDollar && i === 0 })}</td>
      <td class="amt"></td></tr>`).join("");
  const sub = (label, amount, opts = {}) => `
    <tr class="sub"><td>${esc(label)}</td><td class="amt"></td>
      <td class="amt">${money(amount, opts)}</td></tr>`;
  const outer = (label, amount, opts = {}) => `
    <tr class="line"><td>${esc(label)}</td><td class="amt"></td>
      <td class="amt">${money(amount, opts)}</td></tr>`;
  const total = (label, amount, ruled = true) => `
    <tr class="total"><td>${esc(label)}</td><td class="amt"></td>
      <td class="amt${ruled ? " ruled" : ""}">${money(amount)}</td></tr>`;
  const grand = (label, amount) => `
    <tr class="grand"><td>${esc(label)}</td><td class="amt" style="border:none"></td>
      <td class="amt">${money(amount, { dollar: true })}</td></tr>`;
  const block = (label, items, totalLabel, totalAmount, dollar) => {
    if (!items.length) return "";
    if (items.length === 1) return section(label) + outer(items[0].account, items[0].amount, { dollar });
    return section(label) + linesInner(items, dollar) + sub(totalLabel, totalAmount, {});
  };

  function render(r, body) {
    results.classList.remove("hidden");
    const tb = r.trial_balance;
    const entity = body.entity, period = body.period_end;

    // Verdict
    const abn = tb.abnormal_balances.map((a) =>
      `<li>${esc(a.account)} carries a ${a.side} balance of ${money(a.balance, { dollar: true })}; its normal balance is a ${a.normal}.</li>`).join("");
    document.getElementById("tb-verdict").innerHTML = tb.balanced
      ? `<div class="verdict ok tool-panel"><div class="mark">✓</div><div>
          <div class="title">Trial balance is in balance: debits = credits = ${money(tb.total_debits, { dollar: true })}</div>
          <div class="sub">${tb.account_count} accounts. Balance sheet ${r.balance_sheet.balances ? "balances (A = L + E)" : "does NOT balance"}; post-closing TB ${r.post_closing_trial_balance.balanced ? "balances" : "does NOT balance"}.</div>
          ${abn ? `<ul>${abn}</ul>` : ""}</div></div>`
      : `<div class="verdict bad tool-panel"><div class="mark">!</div><div>
          <div class="title">Trial balance is out of balance by ${money(tb.difference, { dollar: true })}</div>
          <div class="sub">Debits ${money(tb.total_debits, { dollar: true })} · Credits ${money(tb.total_credits, { dollar: true })}. Statements below are drafts until this is fixed.</div>
          <ul>${tb.diagnostics.slice(1).map((d) => `<li>${esc(d)}</li>`).join("")}${abn}</ul></div></div>`;

    // Income statement (multi-step)
    const is = r.income_statement;
    let h = head(entity, "Income Statement", period) + "<table class='stmt'>";
    if (is.revenue.length > 1) {
      h += section("Revenue") + linesInner(is.revenue, true) + sub("Net sales", is.net_sales);
    } else {
      h += outer("Net sales", is.net_sales, { dollar: true });
    }
    h += is.cogs.length ? outer("Cost of goods sold", is.cogs.reduce((s, l) => s + l.amount, 0)) : "";
    h += total("Gross profit", is.gross_profit);
    h += block("Operating expenses", is.operating_expenses, "Total operating expenses", is.total_operating_expenses, false);
    h += total("Operating income", is.operating_income);
    if (is.other.length) {
      h += section("Other income (expense)");
      h += is.other.map((l) => outer(l.account, l.amount)).join("");
    }
    h += total("Income before income taxes", is.pretax_income);
    h += is.income_tax.map((l) => outer(l.account, l.amount)).join("");
    h += grand(is.net_income >= 0 ? "Net income" : "Net loss", is.net_income);
    document.getElementById("is-panel").innerHTML = h + "</table>";

    // Balance sheet (classified)
    const bs = r.balance_sheet;
    const balPeriod = period.replace(/^For the (Year|Month|Quarter) Ended /i, "");
    h = head(entity, "Balance Sheet", balPeriod) + "<table class='stmt'>";
    h += section("Assets");
    h += block("Current assets", bs.current_assets, "Total current assets", bs.total_current_assets, true);
    h += block("Property, plant & equipment and other", bs.noncurrent_assets, "Net noncurrent assets",
      bs.total_assets - bs.total_current_assets, false);
    h += grand("Total assets", bs.total_assets);
    h += section("Liabilities and stockholders' equity");
    h += block("Current liabilities", bs.current_liabilities, "Total current liabilities", bs.total_current_liabilities, true);
    h += block("Long-term liabilities", bs.noncurrent_liabilities, "Total long-term liabilities",
      bs.total_liabilities - bs.total_current_liabilities, false);
    h += total("Total liabilities", bs.total_liabilities);
    const equityItems = bs.contributed_capital.concat([{ account: "Retained earnings", amount: bs.ending_retained_earnings }]);
    h += block("Stockholders' equity", equityItems, "Total stockholders' equity", bs.total_equity, false);
    h += grand("Total liabilities and equity", bs.total_liabilities_and_equity);
    h += "</table>";
    if (!bs.balances) h += `<p class="error-box">Out of balance by ${money(bs.difference, { dollar: true })}.</p>`;
    document.getElementById("bs-panel").innerHTML = h;

    // Retained earnings
    const re = r.retained_earnings;
    h = head(entity, "Statement of Retained Earnings", period) + "<table class='stmt'>";
    h += outer("Retained earnings, beginning of period", re.beginning, { dollar: true });
    h += outer(re.net_income >= 0 ? "Add: net income" : "Less: net loss", Math.abs(re.net_income));
    h += outer("Less: dividends declared", re.dividends);
    h += grand("Retained earnings, end of period", re.ending);
    document.getElementById("re-panel").innerHTML = h + "</table>";

    // Ratios
    const fmtRatio = (x) => x.value === null ? "n/a"
      : x.kind === "pct" ? `${x.value.toFixed(1)}%`
      : x.kind === "x" ? `${x.value.toFixed(2)}×` : money(x.value, { dollar: true });
    document.getElementById("ratio-panel").innerHTML = `<h2>Financial ratios</h2>
      <table class="grid"><tbody>${r.ratios.map((x) => `<tr><td><strong>${esc(x.name)}</strong>
        <div class="muted small">${esc(x.note)}</div></td><td class="num">${fmtRatio(x)}</td></tr>`).join("")}
      </tbody></table>`;

    // Closing entries + post-closing TB
    const je = r.closing_entries.map((e, n) => `<div class="je"><div class="memo">CE${n + 1}. ${esc(e.description)}</div>
      <table class="grid journal"><thead><tr><th>Account</th><th class="num">Debit</th><th class="num">Credit</th></tr></thead><tbody>
      ${e.lines.map((l) => `<tr><td class="${l.credit ? "cr-acct" : ""}">${esc(l.account)}</td>
        <td class="num">${l.debit ? money(l.debit) : ""}</td><td class="num">${l.credit ? money(l.credit) : ""}</td></tr>`).join("")}
      </tbody></table></div>`).join("");
    const pc = r.post_closing_trial_balance;
    const pct = `<table class="grid"><thead><tr><th>Account</th><th class="num">Debit</th><th class="num">Credit</th></tr></thead><tbody>
      ${pc.rows.map((l) => `<tr><td>${esc(l.account)}</td><td class="num">${l.debit ? money(l.debit) : ""}</td>
        <td class="num">${l.credit ? money(l.credit) : ""}</td></tr>`).join("")}
      <tr><td><strong>Totals</strong></td><td class="num"><strong>${money(pc.total_debits, { dollar: true })}</strong></td>
        <td class="num"><strong>${money(pc.total_credits, { dollar: true })}</strong></td></tr></tbody></table>`;
    document.getElementById("close-panel").innerHTML = `<div class="two-col">
      <div><h2>Closing entries</h2><p class="muted small">Temporary accounts are zeroed out through Income Summary into Retained Earnings.</p>${je}</div>
      <div><h2>Post-closing trial balance</h2><p class="muted small">Only permanent (balance sheet) accounts remain. ${pc.balanced ? "In balance ✓" : "OUT OF BALANCE"}</p>
      <div class="table-scroll">${pct}</div></div></div>`;

    results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Pre-fill so the page is never empty.
  Acct.loadText(SAMPLE).then((t) => { if (!csv.value) csv.value = t; }).catch(() => {});
})();
