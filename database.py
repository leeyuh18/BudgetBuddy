"""SQLite persistence and money-safe helpers for BudgetBuddy.

All monetary amounts are stored as INTEGER centavos to avoid floating-point errors.
"""
from __future__ import annotations

import csv
import sqlite3
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

INCOME_CATEGORIES = ["Allowance", "Salary", "Freelance", "Gifts", "Other Income"]
EXPENSE_CATEGORIES = [
    "Food & Drinks", "Transportation", "School", "Groceries", "Bills",
    "Shopping", "Health", "Entertainment", "Personal Care", "Other Expense",
]


def parse_money(raw: str) -> int:
    """Validate a user-entered positive amount and return whole centavos."""
    cleaned = str(raw).strip().replace(",", "").replace("₱", "")
    try:
        value = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        raise ValueError("Enter a valid amount, such as 125.50.") from None
    if not value.is_finite() or value <= 0:
        raise ValueError("Amount must be greater than zero.")
    if value > Decimal("99999999.99"):
        raise ValueError("Amount is too large.")
    if value.as_tuple().exponent < -2 and value != value.quantize(Decimal("0.01")):
        raise ValueError("Use no more than two decimal places.")
    return int(value * 100)


def peso(centavos: int) -> str:
    negative = centavos < 0
    absolute = abs(int(centavos))
    return f"{'-' if negative else ''}₱{absolute // 100:,}.{absolute % 100:02d}"


def validate_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Enter the date as YYYY-MM-DD (example: 2026-10-26).") from None
    return parsed.isoformat()


def validate_month(value: str) -> str:
    if len(value) != 7:
        raise ValueError("Month must look like YYYY-MM.")
    validate_date(value + "-01")
    return value


def shift_month(month: str, amount: int) -> str:
    year, mm = map(int, validate_month(month).split("-"))
    n = year * 12 + (mm - 1) + amount
    return f"{n // 12:04d}-{n % 12 + 1:02d}"


class BudgetDatabase:
    def __init__(self, path: Optional[str | Path] = None):
        if path is None:
            path = Path.home() / "BudgetBuddyData" / "budgetbuddy.db"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('Income', 'Expense')),
                category TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(transaction_date);
            CREATE TABLE IF NOT EXISTS budgets (
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                limit_cents INTEGER NOT NULL CHECK(limit_cents > 0),
                PRIMARY KEY (month, category)
            );
        """)
        self.connection.commit()

    def close(self):
        self.connection.close()

    def _row(self, query, params=()):
        result = self.connection.execute(query, params).fetchone()
        return dict(result) if result else None

    def _rows(self, query, params=()):
        return [dict(r) for r in self.connection.execute(query, params).fetchall()]

    def add_transaction(self, when: str, kind: str, category: str,
                        amount_cents: int, note: str = "") -> int:
        when = validate_date(when)
        if kind not in ("Income", "Expense"):
            raise ValueError("Choose Income or Expense.")
        category = category.strip()
        if not category or len(category) > 50:
            raise ValueError("Category must be 1–50 characters.")
        if not isinstance(amount_cents, int) or not (0 < amount_cents <= 9999999999):
            raise ValueError("Invalid transaction amount.")
        if len(note) > 200:
            raise ValueError("Notes must be 200 characters or less.")
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO transactions(transaction_date,kind,category,amount_cents,note) "
                "VALUES (?,?,?,?,?)", (when, kind, category, amount_cents, note.strip()))
        return cursor.lastrowid

    def update_transaction(self, tx_id: int, when: str, kind: str, category: str,
                           amount_cents: int, note: str = ""):
        validate_date(when)
        if kind not in ("Income", "Expense") or not category.strip() or len(category.strip()) > 50:
            raise ValueError("Check the transaction type and category.")
        if not isinstance(amount_cents, int) or not (0 < amount_cents <= 9999999999):
            raise ValueError("Invalid transaction amount.")
        if len(note) > 200:
            raise ValueError("Notes must be 200 characters or less.")
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE transactions SET transaction_date=?,kind=?,category=?,amount_cents=?,note=? "
                "WHERE id=?", (when, kind, category.strip(), amount_cents, note.strip(), tx_id))
        if cursor.rowcount == 0:
            raise ValueError("Transaction not found.")

    def delete_transaction(self, tx_id: int):
        with self.connection:
            self.connection.execute("DELETE FROM transactions WHERE id=?", (tx_id,))

    def get_transaction(self, tx_id: int):
        return self._row("SELECT * FROM transactions WHERE id=?", (tx_id,))

    def list_transactions(self, month: Optional[str] = None, kind: str = "All",
                          search: str = "", limit: Optional[int] = None):
        clauses, args = [], []
        if month:
            clauses.append("transaction_date LIKE ?")
            args.append(validate_month(month) + "-%")
        if kind in ("Income", "Expense"):
            clauses.append("kind=?")
            args.append(kind)
        if search.strip():
            clauses.append("(category LIKE ? OR note LIKE ? OR transaction_date LIKE ?)")
            term = "%" + search.strip() + "%"
            args.extend([term, term, term])
        sql = "SELECT * FROM transactions"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY transaction_date DESC,id DESC"
        if limit is not None:
            sql += " LIMIT ?"
            args.append(int(limit))
        return self._rows(sql, args)

    def totals(self, month: Optional[str] = None):
        where, args = "", []
        if month:
            where = " WHERE transaction_date LIKE ?"
            args = [validate_month(month) + "-%"]
        rows = self._rows("SELECT kind,COALESCE(SUM(amount_cents),0) AS amount "
                          "FROM transactions" + where + " GROUP BY kind", args)
        totals = {"Income": 0, "Expense": 0}
        for row in rows:
            totals[row["kind"]] = row["amount"]
        return totals

    def lifetime_balance(self) -> int:
        totals = self.totals()
        return totals["Income"] - totals["Expense"]

    def expense_categories(self, month: str):
        return self._rows(
            "SELECT category,SUM(amount_cents) AS amount FROM transactions "
            "WHERE kind='Expense' AND transaction_date LIKE ? "
            "GROUP BY category ORDER BY amount DESC,category", (validate_month(month) + "-%",))

    def day_expenses(self, month: str):
        return self._rows(
            "SELECT transaction_date AS day, SUM(amount_cents) AS amount "
            "FROM transactions WHERE kind='Expense' AND transaction_date LIKE ? "
            "GROUP BY transaction_date ORDER BY transaction_date", (validate_month(month) + "-%",))

    def set_budget(self, month: str, category: str, limit_cents: int):
        validate_month(month)
        category = category.strip()
        if not category or len(category) > 50:
            raise ValueError("Enter a valid category.")
        if not isinstance(limit_cents, int) or not (0 < limit_cents <= 9999999999):
            raise ValueError("Budget must be greater than zero.")
        with self.connection:
            self.connection.execute(
                "INSERT INTO budgets(month,category,limit_cents) VALUES(?,?,?) "
                "ON CONFLICT(month,category) DO UPDATE SET limit_cents=excluded.limit_cents",
                (month, category, limit_cents))

    def delete_budget(self, month: str, category: str):
        with self.connection:
            self.connection.execute("DELETE FROM budgets WHERE month=? AND category=?",
                                    (validate_month(month), category))

    def budget_progress(self, month: str):
        return self._rows("""
            SELECT b.category, b.limit_cents,
                   COALESCE(SUM(t.amount_cents),0) AS spent_cents
            FROM budgets b
            LEFT JOIN transactions t ON t.kind='Expense'
                AND t.category=b.category AND t.transaction_date LIKE b.month || '-%'
            WHERE b.month=?
            GROUP BY b.category,b.limit_cents
            ORDER BY b.category
        """, (validate_month(month),))

    def transaction_count(self):
        return self._row("SELECT COUNT(*) AS count FROM transactions")["count"]

    def export_csv(self, destination: str | Path, month: Optional[str] = None,
                   kind: str = "All", search: str = "") -> int:
        rows = self.list_transactions(month, kind, search)
        with open(destination, "w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["Date", "Type", "Category", "Amount (PHP)", "Notes"])
            for tx in rows:
                value = Decimal(tx["amount_cents"]) / Decimal(100)
                writer.writerow([tx["transaction_date"], tx["kind"], tx["category"],
                                 str(value), tx["note"]])
        return len(rows)

    def seed_demo(self, month: Optional[str] = None):
        """Add presentation-friendly demo data ONLY to an empty database."""
        if self.transaction_count():
            raise ValueError("Demo data can only be added when there are no transactions.")
        month = validate_month(month or date.today().strftime("%Y-%m"))
        year, mm = map(int, month.split("-"))
        entries = [
            (1, "Income", "Allowance", 650000, "Monthly allowance"),
            (2, "Expense", "School", 85000, "Supplies and printing"),
            (3, "Expense", "Food & Drinks", 17500, "Lunch with classmates"),
            (5, "Expense", "Transportation", 8000, "Jeepney fare"),
            (7, "Expense", "Groceries", 39000, "Weekend groceries"),
            (9, "Income", "Freelance", 120000, "Layout commission"),
            (11, "Expense", "Food & Drinks", 22000, "Snacks and meals"),
            (13, "Expense", "Shopping", 45000, "Notebook and accessories"),
            (15, "Expense", "Bills", 55000, "Mobile data and utilities"),
            (17, "Expense", "Transportation", 12000, "Commute"),
            (19, "Expense", "Entertainment", 18000, "Movie night"),
            (21, "Expense", "Food & Drinks", 28000, "Meals"),
            (23, "Expense", "School", 23000, "Project materials"),
        ]
        for day, kind, cat, amount, note in entries:
            try:
                when = date(year, mm, day)
            except ValueError:
                continue
            self.add_transaction(when.isoformat(), kind, cat, amount, note)
        for category, amount in [
            ("Food & Drinks", 95000), ("Transportation", 35000),
            ("School", 120000), ("Groceries", 60000), ("Bills", 65000),
            ("Shopping", 40000), ("Entertainment", 30000),
        ]:
            self.set_budget(month, category, amount)
