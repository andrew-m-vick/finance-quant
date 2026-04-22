const form = document.getElementById("stress-form");
const results = document.getElementById("results");
const scoreValue = document.getElementById("score-value");
const scoreGrade = document.getElementById("score-grade");
const weakPointsEl = document.getElementById("weak-points");
const scenariosEl = document.getElementById("scenarios");

const SEVERITY_LABEL = {
  strong: "Strong",
  adequate: "Adequate",
  informational: "Informational",
  weak: "Weak",
  critical: "Critical",
};

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(form).entries());
  const res = await fetch("/api/stress-test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Request failed" }));
    alert(err.error || "Request failed");
    return;
  }
  render(await res.json());
});

function render(r) {
  results.classList.remove("hidden");
  scoreValue.textContent = r.resilience_score;
  scoreValue.className = "score-value " + scoreClass(r.resilience_score);
  scoreGrade.textContent = `Grade ${r.grade}`;

  weakPointsEl.innerHTML = "";
  if (r.weak_points.length === 0) {
    const li = document.createElement("li");
    li.className = "weak-item none";
    li.textContent = "No critical or weak points detected.";
    weakPointsEl.appendChild(li);
  } else {
    r.weak_points.forEach((s) => {
      const li = document.createElement("li");
      li.className = `weak-item sev-${s.severity}`;
      li.innerHTML = `<strong>${s.name}</strong><span class="tag">${
        SEVERITY_LABEL[s.severity]
      }</span><div class="summary">${s.summary}</div>`;
      weakPointsEl.appendChild(li);
    });
  }

  scenariosEl.innerHTML = "";
  r.scenarios.forEach((s) => {
    const d = document.createElement("div");
    d.className = `scenario sev-${s.severity}`;
    d.innerHTML = `<div class="scenario-head"><span class="name">${
      s.name
    }</span><span class="tag">${SEVERITY_LABEL[s.severity]}</span></div><div class="summary">${s.summary}</div>`;
    scenariosEl.appendChild(d);
  });
}

function scoreClass(score) {
  if (score >= 85) return "s-a";
  if (score >= 70) return "s-b";
  if (score >= 55) return "s-c";
  if (score >= 40) return "s-d";
  return "s-f";
}
