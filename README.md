# ExpenseTracker — Personal Expense Tracker with ML Forecasting

A Flask expense tracker: log expenses, set a monthly budget, see
spending by category, and forecast next month's spend using two
comparative ML approaches.

## Features
- Auth (Flask-Login, hashed passwords)
- Add/edit/delete expenses (title, amount, category, date, note)
- Monthly budget with a live progress bar and remaining-balance calc
- Dashboard: this month's total, category breakdown chart (Chart.js)
- Full expense list with category filtering
- **Analytics page**: monthly spend bar chart, yearly spend bar chart, all-time category breakdown
- **Spend forecasting**: predicts next month's total spend using
  - Moving average (last up to 3 months) — a stable baseline
  - Linear regression (scikit-learn) on monthly totals — captures trend
  - Confidence level (low/medium/high) based on how many months of
    history are available — the forecast is honest about its own
    reliability instead of showing a falsely precise number with
    only 1-2 months of data
- JSON API at /api/expenses
- Bootstrap and Chart.js are self-hosted in /static (no external CDN dependency, works offline)

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Visit http://127.0.0.1:5000, register, add expenses across a few
different months, then check the Forecast page.

## Why two forecasting methods (report/interview talking point)

- **Moving average** is a stable baseline that's easy to explain
  and resistant to one-off outlier months, but it *lags* behind a
  real trend — if spending is steadily rising, the moving average
  will consistently under-predict.
- **Linear regression** picks up on that trend (the `trend_slope`
  value shows ₹ change per month) and extrapolates it forward, but
  with very little history it can overreact to a single month's
  spike.

Showing both, side by side, with an explicit confidence level tied
to how much history exists, is more honest than picking one method
and hiding its blind spot — and it's a legitimate comparative-
methodology narrative for a report ("baseline vs trend-aware model,
evaluated by how much history each needs to be reliable").

## Structure
```
expensetracker/
├── app.py                # routes
├── models.py              # User, Expense models
├── config.py
├── requirements.txt
├── ml/
│   └── forecast.py        # monthly aggregation + moving avg + linear regression
└── templates/
    ├── ...
    └── forecast.html       # forecast page with comparison chart
```
