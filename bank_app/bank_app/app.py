import os
import sqlite3
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

SCHEMA = """
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    balance_cents INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    type TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    balance_after_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def parse_amount(raw):
    """Return amount in cents, or raise ValueError with a user-friendly message."""
    try:
        value = Decimal((raw or "").strip())
    except InvalidOperation:
        raise ValueError("Enter a valid number.")
    if not value.is_finite():
        raise ValueError("Enter a valid number.")
    if value <= 0:
        raise ValueError("Amount must be greater than zero.")
    if value != value.quantize(Decimal("0.01")):
        raise ValueError("Use at most 2 decimal places.")
    return int(value * 100)


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    app.config["DATABASE"] = db_path or os.environ.get("BANK_DB", "bank.db")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def reset_db():
        """(Re)create tables and seed the demo user: demo / demo123, $1000."""
        db = sqlite3.connect(app.config["DATABASE"])
        db.executescript(SCHEMA)
        db.execute("INSERT INTO users (username, password_hash, balance_cents) "
                   "VALUES (?, ?, ?)",
                   ("demo", generate_password_hash("demo123"), 100000))
        db.commit()
        db.close()

    app.reset_db = reset_db
    if not os.path.exists(app.config["DATABASE"]):
        reset_db()

    @app.template_filter("money")
    def money(cents):
        return f"${cents / 100:,.2f}"

    def login_required(view):
        @wraps(view)
        def wrapped(*a, **kw):
            if "user_id" not in session:
                return redirect(url_for("login"))
            return view(*a, **kw)
        return wrapped

    def current_user():
        return get_db().execute("SELECT * FROM users WHERE id = ?",
                                (session["user_id"],)).fetchone()

    @app.route("/")
    def index():
        return redirect(url_for("dashboard" if "user_id" in session else "login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user = get_db().execute("SELECT * FROM users WHERE username = ?",
                                    (request.form.get("username", "").strip(),)).fetchone()
            if user and check_password_hash(user["password_hash"],
                                            request.form.get("password", "")):
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html", user=current_user())

    def transact(kind):
        try:
            cents = parse_amount(request.form.get("amount"))
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("dashboard"))

        db = get_db()
        user = current_user()
        if kind == "withdraw" and cents > user["balance_cents"]:
            flash("Insufficient funds.", "error")
            return redirect(url_for("dashboard"))

        new_balance = user["balance_cents"] + (cents if kind == "deposit" else -cents)
        db.execute("UPDATE users SET balance_cents = ? WHERE id = ?",
                   (new_balance, user["id"]))
        db.execute("INSERT INTO transactions (user_id, type, amount_cents, balance_after_cents) "
                   "VALUES (?, ?, ?, ?)", (user["id"], kind, cents, new_balance))
        db.commit()
        flash(f"{kind.capitalize()} of ${cents / 100:,.2f} successful.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/deposit", methods=["POST"])
    @login_required
    def deposit():
        return transact("deposit")

    @app.route("/withdraw", methods=["POST"])
    @login_required
    def withdraw():
        return transact("withdraw")

    @app.route("/history")
    @login_required
    def history():
        rows = get_db().execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC",
            (session["user_id"],)).fetchall()
        return render_template("history.html", rows=rows)

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
