"""Everything personal on the site lives here — edit this one file.

Any value still wrapped in [square brackets] is a placeholder. While
placeholders remain, the site shows a yellow "unfinished profile" banner so
nothing half-done slips in front of a recruiter.

Rule of thumb: only list what you can talk about for two minutes in an
interview. Recruiters and interviewers *will* ask.
"""

PROFILE = {
    "name": "Andrew Vick",
    "headline": "Accounting student with hands-on bookkeeping experience",
    "degree": "BBA in Accounting",
    "school": "C.T. Bauer College of Business, University of Houston",
    "graduation": "Expected Fall 2028",
    "gpa": "",              # e.g. "3.6 / 4.0" — leave "" to hide (common advice: show if ≥ 3.5)
    "location": "Houston, TX",
    "open_to": "Accounting internships and entry-level roles in staff accounting, AP/AR, audit, and tax",
    "email": "andrew.vick@outlook.com",
    "linkedin": "https://www.linkedin.com/in/andrew-m-vick",
    "github": "https://github.com/SirBajaBlast",

    # Shown under the main degree on the homepage.
    "other_education": [
        {"credential": "AA in Business", "school": "Houston Community College", "date": "Fall 2026"},
        {"credential": "Certificate, Data Analytics & Visualization", "school": "Rice University", "date": "October 2024"},
    ],

    # CPA path. Not started yet, so it is stated as a plan. Adding a concrete
    # target (e.g. "First section: FAR, Summer 2028") reads stronger.
    "cpa": {
        "status": "Planning to pursue CPA licensure",
        "target": "",        # e.g. "First section: FAR — Summer 2028" — "" hides it
        "credit_hours": "",  # e.g. "On track for 150 credit hours by Fall 2028" — "" hides it
    },

    # Courses you have completed or are taking now. Empty list hides the section.
    "coursework": [
        # "Principles of Financial Accounting",
        # "Principles of Managerial Accounting",
    ],

    "skills": {
        "Accounting": [
            "Bank & cash reconciliation",
            "Payroll",
            "Accounts payable",
            "Sales tax",
            "P&L & budgeting",
            "Financial statement preparation",
            "Closing entries",
            "Audit data analytics (Benford, duplicates, threshold testing)",
        ],
        "Software": ["Microsoft Excel", "SQL", "Python", "Tableau", "Power BI"],
        "Development": ["Flask", "NumPy", "Git"],
    },

    "experience": [
        {
            "role": "Manager",
            "org": "Morningside Thai Restaurant",
            "location": "Houston, TX",
            "dates": "2015–2017, 2020–Present",
            "points": [
                "Reconcile daily cash and credit card sales, prepare bank deposits, and close out the POS system.",
                "Process payroll and tip reporting; review vendor invoices and process payments.",
                "Prepare sales tax filings with the restaurant's CPA and manage labor costs against budget targets.",
                "Oversee daily operations, including staffing, scheduling, inventory, and customer experience.",
            ],
        },
        {
            "role": "Owner",
            "org": "Zabs Asian Bistro",
            "location": "Houston, TX",
            "dates": "2018–2020",
            "points": [
                "Launched and operated a full-service restaurant with full P&L responsibility, including budgeting and food and labor cost targets.",
                "Handled core bookkeeping (cash reconciliation, payroll, accounts payable) and sales tax filings in coordination with a CPA.",
            ],
        },
        {
            "role": "Data Analyst",
            "org": "Indigena Capital",
            "location": "Houston, TX",
            "dates": "2024–Present",
            "points": [
                "Cleaned and reconciled six seasons (2019–2025) of harvest records across multiple crops and sites into a reliable reporting dataset.",
                "Built yield forecasts and interactive Tableau dashboards that stakeholders use for production planning.",
            ],
        },
    ],
}


def has_placeholders(value=PROFILE) -> bool:
    if isinstance(value, str):
        return value.startswith("[") and value.endswith("]")
    if isinstance(value, dict):
        return any(has_placeholders(v) for v in value.values())
    if isinstance(value, list):
        return any(has_placeholders(v) for v in value)
    return False
