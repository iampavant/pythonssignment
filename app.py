import calendar
import os
import sys
from datetime import datetime, date
from collections import defaultdict
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import (
    LoginManager, login_user, login_required, logout_user, current_user
)
app = Flask(__name__)

from config import Config
from models import db, User, Expense, CATEGORIES

sys.path.append(os.path.join(os.path.dirname(__file__), "ml"))
from forecast import get_monthly_totals, forecast_next_month  # noqa: E402


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ---------- auth ----------

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            password = request.form["password"]

            if User.query.filter_by(email=email).first():
                flash("An account with that email already exists.", "error")
                return redirect(url_for("register"))

            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("dashboard"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            password = request.form["password"]
            user = User.query.filter_by(email=email).first()

            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "error")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    # ---------- dashboard ----------

    @app.route("/dashboard")
    @login_required
    def dashboard():
        today = date.today()
        month_start = today.replace(day=1)

        month_expenses = Expense.query.filter(
            Expense.user_id == current_user.id,
            Expense.expense_date >= month_start,
        ).order_by(Expense.expense_date.desc()).all()

        recent_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(
            Expense.expense_date.desc(), Expense.id.desc()
        ).limit(10).all()

        total_month = round(sum(e.amount for e in month_expenses), 2)
        budget = current_user.monthly_budget or 0
        remaining = round(budget - total_month, 2)
        percent_used = round((total_month / budget) * 100, 1) if budget > 0 else None

        category_totals = defaultdict(float)
        for e in month_expenses:
            category_totals[e.category] += e.amount
        chart_labels = list(category_totals.keys())
        chart_values = [round(v, 2) for v in category_totals.values()]

        return render_template(
            "dashboard.html",
            recent_expenses=recent_expenses,
            total_month=total_month,
            budget=budget,
            remaining=remaining,
            percent_used=percent_used,
            chart_labels=chart_labels,
            chart_values=chart_values,
            month_name=calendar.month_name[today.month],
        )

    @app.route("/budget", methods=["POST"])
    @login_required
    def set_budget():
        amount = request.form.get("monthly_budget", "0")
        try:
            current_user.monthly_budget = float(amount)
            db.session.commit()
            flash("Monthly budget updated.", "success")
        except ValueError:
            flash("Enter a valid number for budget.", "error")
        return redirect(url_for("dashboard"))

    # ---------- expenses CRUD ----------

    @app.route("/expenses")
    @login_required
    def list_expenses():
        category_filter = request.args.get("category", "")
        query = Expense.query.filter_by(user_id=current_user.id)
        if category_filter:
            query = query.filter_by(category=category_filter)
        expenses = query.order_by(Expense.expense_date.desc(), Expense.id.desc()).all()
        total = round(sum(e.amount for e in expenses), 2)
        return render_template(
            "expenses.html", expenses=expenses, total=total,
            categories=CATEGORIES, active_category=category_filter
        )

    @app.route("/expenses/add", methods=["GET", "POST"])
    @login_required
    def add_expense():
        if request.method == "POST":
            title = request.form["title"].strip()
            amount = float(request.form["amount"])
            category = request.form["category"]
            note = request.form.get("note", "").strip()
            expense_date = datetime.strptime(request.form["expense_date"], "%Y-%m-%d").date()

            expense = Expense(
                user_id=current_user.id, title=title, amount=amount,
                category=category, note=note, expense_date=expense_date,
            )
            db.session.add(expense)
            db.session.commit()
            flash(f"Added expense: {title}.", "success")
            return redirect(url_for("dashboard"))

        return render_template("add_edit.html", expense=None, categories=CATEGORIES, today=date.today())

    @app.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_expense(expense_id):
        expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()

        if request.method == "POST":
            expense.title = request.form["title"].strip()
            expense.amount = float(request.form["amount"])
            expense.category = request.form["category"]
            expense.note = request.form.get("note", "").strip()
            expense.expense_date = datetime.strptime(request.form["expense_date"], "%Y-%m-%d").date()
            db.session.commit()
            flash(f"Updated {expense.title}.", "success")
            return redirect(url_for("list_expenses"))

        return render_template("add_edit.html", expense=expense, categories=CATEGORIES, today=date.today())

    @app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
    @login_required
    def delete_expense(expense_id):
        expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
        db.session.delete(expense)
        db.session.commit()
        flash(f"Deleted {expense.title}.", "success")
        return redirect(url_for("list_expenses"))

    # ---------- analytics ----------

    @app.route("/analytics")
    @login_required
    def analytics():
        all_expenses = Expense.query.filter_by(user_id=current_user.id).all()
        monthly_totals = get_monthly_totals(all_expenses)

        yearly_totals = defaultdict(float)
        for e in all_expenses:
            yearly_totals[str(e.expense_date.year)] += e.amount
        yearly_totals = dict(sorted(yearly_totals.items()))
        yearly_totals = {k: round(v, 2) for k, v in yearly_totals.items()}

        category_totals = defaultdict(float)
        for e in all_expenses:
            category_totals[e.category] += e.amount
        category_totals = {k: round(v, 2) for k, v in sorted(
            category_totals.items(), key=lambda kv: -kv[1]
        )}

        return render_template(
            "analytics.html",
            monthly_totals=monthly_totals,
            yearly_totals=yearly_totals,
            category_totals=category_totals,
        )

    # ---------- forecasting ----------

    @app.route("/forecast")
    @login_required
    def forecast():
        all_expenses = Expense.query.filter_by(user_id=current_user.id).all()
        monthly_totals = get_monthly_totals(all_expenses)
        result = forecast_next_month(monthly_totals)

        return render_template(
            "forecast.html",
            monthly_totals=monthly_totals,
            result=result,
        )

    # ---------- JSON API ----------

    @app.route("/api/expenses")
    @login_required
    def api_expenses():
        expenses = Expense.query.filter_by(user_id=current_user.id).all()
        return jsonify([
            {
                "id": e.id, "title": e.title, "amount": e.amount,
                "category": e.category, "date": e.expense_date.isoformat(),
            }
            for e in expenses
        ])

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
