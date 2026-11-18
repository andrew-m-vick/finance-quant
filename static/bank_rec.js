(() => {
  const form = document.getElementById("br-form");
  const book = document.getElementById("book-csv");
  const bank = document.getElementById("bank-csv");
  const errBox = document.getElementById("br-error");
  const results = document.getElementById("br-results");
  const { money, esc } = Acct;

  async function loadSample() {
    const [b, k] = await Promise.all([
      Acct.loadText("/static/samples/book_ledger.csv"),
      Acct.loadText("/static/samples/bank_statement.csv"),
    ]);
    book.value = b;
    bank.value = k;
    form.book_balance.value = "28,622.35";
    form.bank_balance.value = "27,219.02";
  }
  document.getElementById("load-sample").addEventListener("click", () => loadSample().then(() => form.requestSubmit()));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    Acct.showError(errBox, null);
    try {
      render(await Acct.post("/api/bank-reconciliation", Object.fromEntries(new FormData(form).entries())));
    } catch (err) {
      results.classList.add("hidden");
      Acct.showError(errBox, err);
    }
  });

  const row = (label, amt, cls = "line", opts = {}) =>
    `<tr class="${cls}"><td>${label}</td><td class="amt"></td><td class="amt${cls === "total" ? " ruled" : ""}">${money(amt, opts)}</td></tr>`;
  const itemRows = (items, sign = 1) => items.map((i, n) =>
    `<tr class="line"><td>${esc(i.ref && /\d/.test(i.ref) ? `#${i.ref} ` : "")}${esc(i.description)} <span class="muted small">${esc(i.date)}</span></td>
      <td class="amt${n === items.length - 1 && items.length > 1 ? " underline" : ""}">${money(Math.abs(i.amount) * sign)}</td><td class="amt"></td></tr>`).join("");
  const group = (label, items, totalAmt, sign) => {
    if (!items.length) return "";
    if (items.length === 1) {
      const i = items[0];
      return row(`${label}: ${esc(i.description)} <span class="muted small">${esc(i.date)}</span>`, Math.abs(i.amount) * sign);
    }
    return `<tr class="section"><td colspan="3">${label}</td></tr>` + itemRows(items, sign) + row("", totalAmt * sign, "sub");
  };

  function render(r) {
    results.classList.remove("hidden");
    const b = r.bank, k = r.book;

    document.getElementById("br-verdict").innerHTML = r.reconciled
      ? `<div class="verdict ok tool-panel"><div class="mark">✓</div><div>
          <div class="title">Reconciled: adjusted bank = adjusted book = ${money(b.adjusted_balance, { dollar: true })}</div>
          <div class="sub">${r.counts.matched} of ${r.counts.book} ledger items cleared · ${r.adjusting_entries.length} adjusting entr${r.adjusting_entries.length === 1 ? "y" : "ies"} needed · ${k.errors.length} recording error${k.errors.length === 1 ? "" : "s"} found</div></div></div>`
      : `<div class="verdict bad tool-panel"><div class="mark">!</div><div>
          <div class="title">Unreconciled difference of ${money(Math.abs(r.difference), { dollar: true })}</div>
          <div class="sub">Adjusted bank ${money(b.adjusted_balance, { dollar: true })} vs adjusted book ${money(k.adjusted_balance, { dollar: true })}. Check the ending balances, then look for items outside the matching window or entered with the wrong sign.</div></div></div>`;

    const bankSide = `<div><h3>Bank side</h3><table class="stmt">
      ${row("Balance per bank statement", b.ending_balance, "line", { dollar: true })}
      ${group("Add: deposits in transit", b.deposits_in_transit, b.deposits_in_transit_total, 1)}
      ${group("Less: outstanding checks", b.outstanding_checks, b.outstanding_checks_total, -1)}
      <tr class="grand"><td>Adjusted bank balance</td><td class="amt" style="border:none"></td><td class="amt">${money(b.adjusted_balance, { dollar: true })}</td></tr>
      </table></div>`;
    const errRows = k.errors.map((e) =>
      row(`Correction: ${esc(e.reason)}`, e.adjustment)).join("");
    const bookSide = `<div><h3>Book side</h3><table class="stmt">
      ${row("Balance per general ledger", k.ending_balance, "line", { dollar: true })}
      ${group("Add: bank credits not yet recorded", k.bank_credits, k.bank_credits_total, 1)}
      ${group("Less: bank charges not yet recorded", k.bank_debits, k.bank_debits_total, -1)}
      ${errRows}
      <tr class="grand"><td>Adjusted book balance</td><td class="amt" style="border:none"></td><td class="amt">${money(k.adjusted_balance, { dollar: true })}</td></tr>
      </table></div>`;
    document.getElementById("rec-panel").innerHTML =
      `<div class="stmt-head"><div class="title">Bank Reconciliation</div><div class="period">As of statement date</div></div>
       <div class="two-col">${bankSide}${bookSide}</div>
       <p class="muted small" style="margin-top:14px">Bank-side items correct themselves when they clear next month; no entry needed. Book-side items need the adjusting entries below.</p>`;

    document.getElementById("aje-panel").innerHTML = `<h2>Proposed adjusting entries</h2>` + (r.adjusting_entries.length
      ? r.adjusting_entries.map((e, n) => `<div class="je"><div class="memo">AJE ${n + 1}. ${esc(e.memo)}</div>
          <table class="grid journal"><tbody>${e.lines.map((l) => `<tr><td class="${l.credit ? "cr-acct" : ""}">${esc(l.account)}</td>
          <td class="num">${l.debit ? money(l.debit) : ""}</td><td class="num">${l.credit ? money(l.credit) : ""}</td></tr>`).join("")}
          </tbody></table></div>`).join("")
      : `<p class="muted">None. The books already reflect everything the bank recorded.</p>`);

    document.getElementById("match-panel").innerHTML = `<h2>Matched items</h2>
      <p class="muted small">Matched by check number first, then exact amount within the date window.</p>
      <div class="table-scroll"><table class="grid"><thead><tr><th>Book</th><th>Cleared</th><th>Method</th><th class="num">Amount</th></tr></thead><tbody>
      ${r.matches.map((m) => `<tr><td>${esc(m.book.date)}<div class="muted small">${esc(m.book.description)}</div></td>
        <td>${esc(m.bank.date)}<div class="muted small">${m.days_to_clear} day${m.days_to_clear === 1 ? "" : "s"}</div></td>
        <td>${esc(m.method)}</td><td class="num">${money(m.book.amount)}</td></tr>`).join("")}
      </tbody></table></div>`;

    results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  loadSample().catch(() => {});
})();
