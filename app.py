import calendar
import os
import sys
from datetime import datetime, date
from collections import defaultdict

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user
)

from config import Config
from models import db, User, Expense, CATEGORIES


sys.path.append(os.path.join(os.path.dirname(__file__), "ml"))
from forecast import get_monthly_totals, forecast_next_month


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


    # ---------------- AUTH ----------------

    @app.route("/register", methods=["GET", "POST"])
    def register():

        if request.method == "POST":

            email = request.form["email"].strip().lower()
            password = request.form["password"]

            if User.query.filter_by(email=email).first():
                flash(
                    "An account with that email already exists.",
                    "error"
                )
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


            flash(
                "Invalid email or password.",
                "error"
            )


        return render_template("login.html")



    @app.route("/logout")
    @login_required
    def logout():

        logout_user()

        return redirect(url_for("login"))



    # ---------------- HOME ----------------

    @app.route("/")
    def index():

        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        return redirect(url_for("login"))



    # ---------------- DASHBOARD ----------------


    @app.route("/dashboard")
    @login_required
    def dashboard():

        today = date.today()

        month_start = today.replace(day=1)


        month_expenses = Expense.query.filter(
            Expense.user_id == current_user.id,
            Expense.expense_date >= month_start
        ).order_by(
            Expense.expense_date.desc()
        ).all()



        recent_expenses = Expense.query.filter_by(
            user_id=current_user.id
        ).order_by(
            Expense.expense_date.desc(),
            Expense.id.desc()
        ).limit(10).all()



        total_month = round(
            sum(e.amount for e in month_expenses),
            2
        )


        budget = current_user.monthly_budget or 0


        remaining = round(
            budget-total_month,
            2
        )


        percent_used = (
            round((total_month / budget)*100, 1)
            if budget > 0
            else None
        )


        category_totals = defaultdict(float)


        for e in month_expenses:
            category_totals[e.category] += e.amount



        chart_labels = list(category_totals.keys())

        chart_values = [
            round(v,2)
            for v in category_totals.values()
        ]



        return render_template(
            "dashboard.html",
            recent_expenses=recent_expenses,
            total_month=total_month,
            budget=budget,
            remaining=remaining,
            percent_used=percent_used,
            chart_labels=chart_labels,
            chart_values=chart_values,
            month_name=calendar.month_name[today.month]
        )



    # ---------------- BUDGET ----------------


    @app.route("/budget", methods=["POST"])
    @login_required
    def set_budget():

        amount = request.form.get(
            "monthly_budget",
            "0"
        )


        try:

            current_user.monthly_budget = float(amount)

            db.session.commit()

            flash(
                "Monthly budget updated.",
                "success"
            )


        except ValueError:

            flash(
                "Enter valid budget.",
                "error"
            )


        return redirect(url_for("dashboard"))



    # ---------------- EXPENSES ----------------


    @app.route("/expenses")
    @login_required
    def list_expenses():

        expenses = Expense.query.filter_by(
            user_id=current_user.id
        ).order_by(
            Expense.expense_date.desc()
        ).all()


        total = round(
            sum(e.amount for e in expenses),
            2
        )


        return render_template(
            "expenses.html",
            expenses=expenses,
            total=total,
            categories=CATEGORIES
        )



    @app.route("/expenses/add", methods=["GET","POST"])
    @login_required
    def add_expense():


        if request.method=="POST":


            expense = Expense(

                user_id=current_user.id,

                title=request.form["title"],

                amount=float(
                    request.form["amount"]
                ),

                category=request.form["category"],

                note=request.form.get("note",""),

                expense_date=datetime.strptime(
                    request.form["expense_date"],
                    "%Y-%m-%d"
                ).date()

            )


            db.session.add(expense)

            db.session.commit()


            flash(
                "Expense added",
                "success"
            )


            return redirect(
                url_for("dashboard")
            )



        return render_template(
            "add_edit.html",
            expense=None,
            categories=CATEGORIES,
            today=date.today()
        )



    # ---------------- ANALYTICS ----------------


    @app.route("/analytics")
    @login_required
    def analytics():

        expenses = Expense.query.filter_by(
            user_id=current_user.id
        ).all()


        monthly_totals = get_monthly_totals(
            expenses
        )


        return render_template(
            "analytics.html",
            monthly_totals=monthly_totals
        )



    # ---------------- FORECAST ----------------


    @app.route("/forecast")
    @login_required
    def forecast():


        expenses = Expense.query.filter_by(
            user_id=current_user.id
        ).all()


        monthly_totals = get_monthly_totals(
            expenses
        )


        result = forecast_next_month(
            monthly_totals
        )


        return render_template(
            "forecast.html",
            result=result,
            monthly_totals=monthly_totals
        )



    # ---------------- API ----------------


    @app.route("/api/expenses")
    @login_required
    def api_expenses():


        expenses = Expense.query.filter_by(
            user_id=current_user.id
        ).all()


        return jsonify([

            {
                "id":e.id,
                "title":e.title,
                "amount":e.amount,
                "category":e.category,
                "date":e.expense_date.isoformat()
            }

            for e in expenses

        ])



    with app.app_context():

        db.create_all()



    return app



# IMPORTANT FOR GUNICORN
app = create_app()



if __name__ == "__main__":

    app.run(
        debug=True
    )
