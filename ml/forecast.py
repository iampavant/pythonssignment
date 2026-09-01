"""
Forecasts next month's total spend from a user's expense history.

Two methods are computed and shown side by side, which is the
actual point of the exercise for a report/viva:

  - Moving average (naive baseline): average of the last N months.
    Simple, stable, but can't react to a clear upward/downward trend.

  - Linear regression: fits spend-over-time as a straight line
    (month index -> total spend) using scikit-learn, and
    extrapolates one step forward. Captures a trend the moving
    average misses, but is more sensitive to outlier months when
    history is short.

With very little history (1-2 months) neither method has enough
signal to be meaningful - this is disclosed to the user rather
than hidden behind a confident-looking number.
"""
from collections import OrderedDict
from datetime import date
import numpy as np
from sklearn.linear_model import LinearRegression


def get_monthly_totals(expenses):
    """
    expenses: list of Expense objects (any order).
    Returns an OrderedDict of {"YYYY-MM": total} sorted chronologically,
    including months with zero expenses in between (no gaps).
    """
    if not expenses:
        return OrderedDict()

    totals = {}
    for e in expenses:
        key = e.expense_date.strftime("%Y-%m")
        totals[key] = totals.get(key, 0.0) + e.amount

    months_sorted = sorted(totals.keys())
    first_year, first_month = map(int, months_sorted[0].split("-"))
    last_year, last_month = map(int, months_sorted[-1].split("-"))

    filled = OrderedDict()
    y, m = first_year, first_month
    while (y, m) <= (last_year, last_month):
        key = f"{y:04d}-{m:02d}"
        filled[key] = round(totals.get(key, 0.0), 2)
        m += 1
        if m > 12:
            m = 1
            y += 1
    return filled


def forecast_next_month(monthly_totals: "OrderedDict[str, float]"):
    """
    Returns a dict with both forecasting methods' predictions, plus
    metadata about how much history was available (so the UI can be
    honest about confidence rather than just showing a number).
    """
    months = list(monthly_totals.keys())
    values = list(monthly_totals.values())
    n = len(values)

    result = {
        "history_months": n,
        "moving_average": None,
        "linear_regression": None,
        "next_month_label": _next_month_label(months[-1]) if months else None,
        "confidence": "low",
    }

    if n == 0:
        return result

    # --- Moving average (last up-to-3 months) ---
    window = values[-3:] if n >= 3 else values
    result["moving_average"] = round(sum(window) / len(window), 2)

    # --- Linear regression (needs at least 2 points to fit a line) ---
    if n >= 2:
        X = np.arange(n).reshape(-1, 1)
        y = np.array(values)
        model = LinearRegression()
        model.fit(X, y)
        next_x = np.array([[n]])
        pred = model.predict(next_x)[0]
        result["linear_regression"] = round(max(0.0, float(pred)), 2)
        result["trend_slope"] = round(float(model.coef_[0]), 2)

    if n >= 6:
        result["confidence"] = "high"
    elif n >= 3:
        result["confidence"] = "medium"
    else:
        result["confidence"] = "low"

    return result


def _next_month_label(last_month_key: str) -> str:
    y, m = map(int, last_month_key.split("-"))
    m += 1
    if m > 12:
        m = 1
        y += 1
    return f"{y:04d}-{m:02d}"
