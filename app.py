import os

from flask import Flask, render_template, request, jsonify, send_from_directory

from bank_rec import reconcile
from benford import run_benford
from financial_statements import run_financial_statements
from ledger_utils import InputError
from monte_carlo import run_monte_carlo
from about_me import PROFILE, has_placeholders
from stress_test import run_stress_test

app = Flask(__name__)
MAX_INPUT_CHARS = 2_000_000  # ~20k ledger rows; keeps one request from hogging the dyno


@app.context_processor
def inject_profile():
    resume = os.path.exists(os.path.join(app.static_folder, "resume.pdf"))
    return {
        "profile": PROFILE,
        "profile_incomplete": has_placeholders(),
        "resume_url": "/static/resume.pdf" if resume else None,
    }


def _payload():
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        raise InputError("Request body must be a JSON object.")
    for v in data.values():
        if isinstance(v, str) and len(v) > MAX_INPUT_CHARS:
            raise InputError("Input too large — trim the file and try again.")
    return data


@app.route("/service-worker.js")
def service_worker():
    # Served from the root so its scope covers the whole site.
    response = send_from_directory(
        app.static_folder, "service-worker.js", mimetype="application/javascript"
    )
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(
        app.static_folder,
        "manifest.webmanifest",
        mimetype="application/manifest+json",
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stress-test")
def stress_test_page():
    return render_template("stress_test.html")


@app.route("/retirement")
def retirement_page():
    return render_template("retirement.html")


@app.route("/financial-statements")
def financial_statements_page():
    return render_template("financial_statements.html")


@app.route("/bank-reconciliation")
def bank_rec_page():
    return render_template("bank_rec.html")


@app.route("/audit-analytics")
def audit_analytics_page():
    return render_template("audit_analytics.html")


@app.route("/methodology")
def methodology_page():
    return render_template("methodology.html")


@app.route("/api/stress-test", methods=["POST"])
def api_stress_test():
    data = request.get_json(force=True)
    try:
        result = run_stress_test(
            monthly_income=float(data["monthly_income"]),
            monthly_fixed_expenses=float(data["monthly_fixed_expenses"]),
            monthly_variable_expenses=float(data.get("monthly_variable_expenses", 0)),
            liquid_savings=float(data["liquid_savings"]),
            invested_assets=float(data.get("invested_assets", 0)),
            total_debt=float(data.get("total_debt", 0)),
            monthly_debt_payments=float(data.get("monthly_debt_payments", 0)),
        )
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400
    return jsonify(result)


@app.route("/api/monte-carlo", methods=["POST"])
def api_monte_carlo():
    data = request.get_json(force=True)
    try:
        result = run_monte_carlo(
            current_age=int(data["current_age"]),
            retirement_age=int(data["retirement_age"]),
            current_savings=float(data["current_savings"]),
            annual_contribution=float(data["annual_contribution"]),
            expected_return=float(data["expected_return"]),
            volatility=float(data["volatility"]),
            inflation=float(data.get("inflation", 0.025)),
            goal=float(data.get("goal", 0)),
            num_simulations=int(data.get("num_simulations", 10000)),
        )
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400
    return jsonify(result)


@app.route("/api/financial-statements", methods=["POST"])
def api_financial_statements():
    try:
        data = _payload()
        result = run_financial_statements(
            data.get("csv", ""),
            entity=str(data.get("entity", ""))[:120],
            period_end=str(data.get("period_end", ""))[:60],
        )
    except InputError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)


@app.route("/api/bank-reconciliation", methods=["POST"])
def api_bank_rec():
    try:
        data = _payload()
        window = int(data.get("window_days", 7))
        if not 0 <= window <= 60:
            raise InputError("Matching window must be between 0 and 60 days.")
        result = reconcile(
            data.get("book_csv", ""), data.get("bank_csv", ""),
            data.get("book_balance", ""), data.get("bank_balance", ""),
            window_days=window,
        )
    except (InputError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)


@app.route("/api/audit-analytics", methods=["POST"])
def api_audit_analytics():
    try:
        data = _payload()
        result = run_benford(data.get("csv", ""), approval_limit=data.get("approval_limit", 5000))
    except InputError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
