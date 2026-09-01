from datetime import date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

CATEGORIES = ["Food", "Transport", "Rent", "Utilities", "Shopping",
              "Entertainment", "Health", "Education", "Other"]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    monthly_budget = db.Column(db.Float, default=0.0)

    expenses = db.relationship("Expense", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), default="Other")
    note = db.Column(db.String(255), default="")
    expense_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.Date, default=date.today)
