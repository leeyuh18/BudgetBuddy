"""Run with: python -m unittest -v"""
import csv
import tempfile
import unittest
from pathlib import Path

from database import BudgetDatabase, parse_money, peso, shift_month, validate_date


class MoneyTests(unittest.TestCase):
    def test_money_input_and_formatting(self):
        self.assertEqual(parse_money("125.50"), 12550)
        self.assertEqual(parse_money("₱1,234.56"), 123456)
        self.assertEqual(parse_money("0.01"), 1)
        self.assertEqual(peso(123456), "₱1,234.56")
        self.assertEqual(peso(-101), "-₱1.01")

    def test_money_rejects_invalid_values(self):
        for value in ("", "word", "-10", "0", "10.001", "NaN", "Infinity", "100000000"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_money(value)

    def test_dates(self):
        self.assertEqual(validate_date("2026-10-26"), "2026-10-26")
        for value in ("2026-02-30", "26-10-2026", "2026-10-1"):
            with self.assertRaises(ValueError):
                validate_date(value)
        self.assertEqual(shift_month("2026-12", 1), "2027-01")
        self.assertEqual(shift_month("2026-01", -1), "2025-12")


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "budgetbuddy.db"
        self.db = BudgetDatabase(self.path)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_add_update_delete_balance(self):
        income_id = self.db.add_transaction("2026-10-02", "Income", "Allowance", 500000, "Monthly")
        expense_id = self.db.add_transaction("2026-10-03", "Expense", "Food & Drinks", 12550, "Lunch")
        self.assertEqual(self.db.lifetime_balance(), 487450)
        self.assertEqual(self.db.totals("2026-10"), {"Income": 500000, "Expense": 12550})
        self.db.update_transaction(expense_id, "2026-10-04", "Expense", "Transportation", 25000)
        self.assertEqual(self.db.lifetime_balance(), 475000)
        self.assertEqual(self.db.get_transaction(expense_id)["category"], "Transportation")
        self.db.delete_transaction(income_id)
        self.assertEqual(self.db.lifetime_balance(), -25000)
        self.assertIsNone(self.db.get_transaction(income_id))

    def test_month_filter_and_search(self):
        self.db.add_transaction("2026-09-01", "Expense", "School", 10000, "Books")
        self.db.add_transaction("2026-10-01", "Expense", "School", 20000, "Project")
        self.db.add_transaction("2026-10-02", "Income", "Allowance", 30000, "Weekly")
        self.assertEqual(len(self.db.list_transactions("2026-10")), 2)
        self.assertEqual(len(self.db.list_transactions(kind="Expense")), 2)
        self.assertEqual(len(self.db.list_transactions(search="project")), 1)
        self.assertEqual(self.db.totals("2026-09")["Expense"], 10000)
        self.assertEqual(self.db.totals("2026-11")["Expense"], 0)

    def test_budget_progress_and_over_budget(self):
        self.db.set_budget("2026-10", "Food & Drinks", 15000)
        self.db.add_transaction("2026-10-04", "Expense", "Food & Drinks", 10000)
        self.db.add_transaction("2026-10-09", "Expense", "Food & Drinks", 8500)
        self.db.add_transaction("2026-09-09", "Expense", "Food & Drinks", 999999)
        self.db.add_transaction("2026-10-10", "Income", "Food & Drinks", 99999)
        progress = self.db.budget_progress("2026-10")
        self.assertEqual(progress[0]["spent_cents"], 18500)
        self.assertEqual(progress[0]["limit_cents"], 15000)
        self.db.set_budget("2026-10", "Food & Drinks", 20000)
        self.assertEqual(self.db.budget_progress("2026-10")[0]["limit_cents"], 20000)
        self.db.delete_budget("2026-10", "Food & Drinks")
        self.assertEqual(self.db.budget_progress("2026-10"), [])

    def test_export_csv(self):
        self.db.add_transaction("2026-10-01", "Income", "Allowance", 120050, "Gift")
        target = Path(self.temp_dir.name) / "export.csv"
        self.assertEqual(self.db.export_csv(target), 1)
        with target.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows[1], ["2026-10-01", "Income", "Allowance", "1200.5", "Gift"])

    def test_reopen_keeps_data(self):
        self.db.add_transaction("2026-10-01", "Income", "Allowance", 100000)
        self.db.close()
        self.db = BudgetDatabase(self.path)
        self.assertEqual(self.db.lifetime_balance(), 100000)

    def test_demo_data_only_on_empty_database(self):
        self.db.seed_demo("2026-10")
        self.assertEqual(self.db.transaction_count(), 13)
        self.assertEqual(len(self.db.budget_progress("2026-10")), 7)
        with self.assertRaises(ValueError):
            self.db.seed_demo("2026-10")

    def test_reject_bad_transactions(self):
        for args in [
            ("bad-date", "Income", "Salary", 1000),
            ("2026-10-01", "Unknown", "Salary", 1000),
            ("2026-10-01", "Income", "", 1000),
            ("2026-10-01", "Expense", "Food", 0),
        ]:
            with self.assertRaises(ValueError):
                self.db.add_transaction(*args)


if __name__ == "__main__":
    unittest.main()
