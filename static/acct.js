// Shared helpers for the accounting tool pages.
const Acct = (() => {
  const nf = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // Accounting format: negatives in parentheses, optional $.
  function money(n, { dollar = false } = {}) {
    if (n === null || n === undefined) return "—";
    const abs = nf.format(Math.abs(n));
    const s = (dollar ? "$" : "") + abs;
    return n < 0 ? `(${s})` : s;
  }

  function esc(v) {
    return String(v ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[c]);
  }

  async function post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({ error: "Unexpected server response." }));
    if (!res.ok) throw new Error(data.error || "Request failed.");
    return data;
  }

  async function loadText(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Could not load sample (${res.status}).`);
    return res.text();
  }

  function showError(el, err) {
    el.textContent = err ? (err.message || String(err)) : "";
    el.classList.toggle("hidden", !err);
  }

  // Wire an <input type=file> to fill a textarea, entirely client-side.
  function fileInto(input, textarea) {
    input.addEventListener("change", () => {
      const f = input.files && input.files[0];
      if (!f) return;
      const r = new FileReader();
      r.onload = () => { textarea.value = r.result; };
      r.readAsText(f);
    });
  }

  return { money, esc, post, loadText, showError, fileInto };
})();
