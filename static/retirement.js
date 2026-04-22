const form = document.getElementById("mc-form");
const statusEl = document.getElementById("mc-status");
const results = document.getElementById("mc-results");
const probValue = document.getElementById("prob-value");
const probSub = document.getElementById("prob-sub");
const pctBody = document.getElementById("pct-body");

let fanChart = null;
let histChart = null;

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  statusEl.textContent = "Running simulation…";
  const raw = Object.fromEntries(new FormData(form).entries());
  const body = {
    current_age: Number(raw.current_age),
    retirement_age: Number(raw.retirement_age),
    current_savings: Number(raw.current_savings),
    annual_contribution: Number(raw.annual_contribution),
    expected_return: Number(raw.expected_return_pct) / 100,
    volatility: Number(raw.volatility_pct) / 100,
    inflation: Number(raw.inflation_pct) / 100,
    goal: Number(raw.goal),
    num_simulations: Number(raw.num_simulations),
  };
  const res = await fetch("/api/monte-carlo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Request failed" }));
    statusEl.textContent = err.error || "Request failed";
    return;
  }
  statusEl.textContent = "";
  render(await res.json(), body.goal);
});

const fmt = (n) =>
  "$" +
  Math.round(n).toLocaleString("en-US", { maximumFractionDigits: 0 });

function render(r, goal) {
  results.classList.remove("hidden");

  if (r.prob_meeting_goal == null) {
    probValue.textContent = "—";
    probSub.textContent = "Set a goal > 0 to see probability.";
  } else {
    const pct = (r.prob_meeting_goal * 100).toFixed(1);
    probValue.textContent = `${pct}%`;
    probValue.className = "score-value " + probClass(r.prob_meeting_goal);
    probSub.textContent = `of ${r.num_simulations.toLocaleString()} simulations reached ${fmt(goal)}`;
  }

  const rows = [
    ["10th (pessimistic)", "p10"],
    ["25th", "p25"],
    ["50th (median)", "p50"],
    ["75th", "p75"],
    ["90th (optimistic)", "p90"],
  ];
  pctBody.innerHTML = "";
  rows.forEach(([label, key]) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${label}</td><td>${fmt(r.percentiles_nominal[key])}</td><td>${fmt(r.percentiles_real[key])}</td>`;
    pctBody.appendChild(tr);
  });

  drawFanChart(r);
  drawHistogram(r);
}

function drawFanChart(r) {
  const ctx = document.getElementById("fan-chart").getContext("2d");
  if (fanChart) fanChart.destroy();
  const labels = r.ages;
  const b = r.bands_over_time;
  fanChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "90th pct",
          data: b.p90,
          borderColor: "rgba(56,142,60,0.9)",
          backgroundColor: "rgba(56,142,60,0.15)",
          fill: "+1",
          pointRadius: 0,
          borderWidth: 1,
        },
        {
          label: "75th pct",
          data: b.p75,
          borderColor: "rgba(56,142,60,0.6)",
          backgroundColor: "rgba(56,142,60,0.20)",
          fill: "+1",
          pointRadius: 0,
          borderWidth: 1,
        },
        {
          label: "Median",
          data: b.p50,
          borderColor: "#1b5e20",
          backgroundColor: "rgba(27,94,32,0.25)",
          fill: "+1",
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "25th pct",
          data: b.p25,
          borderColor: "rgba(211,47,47,0.6)",
          backgroundColor: "rgba(211,47,47,0.20)",
          fill: "+1",
          pointRadius: 0,
          borderWidth: 1,
        },
        {
          label: "10th pct",
          data: b.p10,
          borderColor: "rgba(211,47,47,0.9)",
          backgroundColor: "rgba(0,0,0,0)",
          fill: false,
          pointRadius: 0,
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { title: { display: true, text: "Age" } },
        y: {
          title: { display: true, text: "Portfolio value ($)" },
          ticks: { callback: (v) => fmt(v) },
        },
      },
      plugins: {
        tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.parsed.y)}` } },
      },
    },
  });
}

function drawHistogram(r) {
  const ctx = document.getElementById("hist-chart").getContext("2d");
  if (histChart) histChart.destroy();
  const { counts, edges } = r.histogram;
  const labels = counts.map((_, i) => fmt((edges[i] + edges[i + 1]) / 2));
  histChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Simulations",
          data: counts,
          backgroundColor: "rgba(27,94,32,0.7)",
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: "Final balance (nominal $)" }, ticks: { maxTicksLimit: 10 } },
        y: { title: { display: true, text: "Count" } },
      },
      plugins: { legend: { display: false } },
    },
  });
}

function probClass(p) {
  if (p >= 0.85) return "s-a";
  if (p >= 0.7) return "s-b";
  if (p >= 0.5) return "s-c";
  if (p >= 0.3) return "s-d";
  return "s-f";
}
