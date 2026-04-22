from flask import Flask, render_template, request, jsonify
from stress_test import run_stress_test
from monte_carlo import run_monte_carlo

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stress-test")
def stress_test_page():
    return render_template("stress_test.html")


@app.route("/retirement")
def retirement_page():
    return render_template("retirement.html")


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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
