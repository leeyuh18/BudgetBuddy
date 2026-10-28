# BudgetBuddy — Your Money, Made Simple

**BudgetBuddy** is a desktop personal-finance tracker created as a Python GUI school project. It helps students record their allowance, track expenses, set monthly spending limits, and understand where their money goes.

## Requirements

- Windows 10/11, macOS, or Linux
- Python **3.10 or newer** with **Tkinter** (Tkinter is included in most Windows Python installations)
- No internet connection, database server, or third-party packages required

## How to launch (Windows)

1. Extract the entire ZIP folder first.
2. Install Python from https://www.python.org/downloads/ if you do not have it. During installation on Windows, select **Add Python to PATH**.
3. Double-click **`Launch_BudgetBuddy.bat`** to run, or double-click **`BudgetBuddy.pyw`** if `.pyw` is associated with Python on your PC.
4. Alternatively, open Command Prompt inside the project folder and run:

```bat
py app.py
```

If `py` does not work, try `python app.py`.

## How to launch (macOS / Linux)

Open Terminal in the extracted project folder and run:

```bash
python3 app.py
```

If Linux reports `No module named tkinter`, install your operating system's Tkinter package (often `python3-tk`).

## Main features

| Screen | What it does |
|---|---|
| Dashboard | Displays total income, expenses, monthly savings, lifetime cash balance, daily spending graph, popular expense categories, and recent transactions. |
| Transactions | Add, edit, delete, search, and filter transactions; export filtered records to CSV. |
| Budgets | Set monthly spending limits by expense category and see progress and overspending warnings. |
| Insights | See a donut chart of spending, savings rate, previous month's expenses, and practical budgeting tips. |

Additional features: Philippine peso (₱) formatting, custom categories, month navigation, automatic local data saving, safe input validation, and built-in sample data for presentation.

## First-time walkthrough

1. Open **Dashboard**.
2. Click **+ Add Transaction** and select **Income**; enter a category such as Allowance, date, and amount.
3. Add an **Expense** such as School or Food & Drinks.
4. Open **Budgets** and set a limit for the selected month. New expenses in the same category count toward that limit.
5. Open **Insights** to see graphs and statistics.
6. Open **Transactions** to edit, delete, search, or export your records.

**For a classroom presentation:** On a brand-new installation, the Dashboard shows a **Load Demo Data** button. It adds example records and category limits to the *current month* for your demonstration. The demo button only works while the database has no transactions; it never automatically overwrites existing data.

## Where is my data saved?

BudgetBuddy creates a local SQLite database automatically:

- Windows: `C:\Users\YOUR_USERNAME\BudgetBuddyData\budgetbuddy.db`
- macOS / Linux: `~/BudgetBuddyData/budgetbuddy.db`

This file stores all your transactions and budgets. Copy the file somewhere safe if you want a backup. To start fresh, **close BudgetBuddy first**, then rename or delete this file. Deleting it permanently removes saved records unless you have a backup.

Your data remains on your computer; the app does not connect to any bank or cloud service.

## Project files

- `app.py` — Tkinter graphical user interface, windows, charts, and navigation
- `database.py` — SQLite database layer, validation, calculations, and CSV export
- `BudgetBuddy.pyw` — double-click windowed launcher for Windows
- `Launch_BudgetBuddy.bat` — Windows batch launcher
- `test_budgetbuddy.py` — automated tests for core calculations and storage
- `PROJECT_REPORT.md` — goals, scope, design, database schema and presentation outline
- `PRESENTATION_SCRIPT.md` — suggested script for a short live demo
- `previews/` — sample screenshots generated using demonstration transactions

## Running automated tests

Open a terminal in this folder and run:

```bash
python -m unittest -v
```

There are 10 automated tests covering currency conversion, invalid input, dates, record editing/deletion, totals, monthly filters, budgets, CSV export, database persistence, and sample data.

## Technical summary

- **Programming language:** Python 3.10+
- **GUI toolkit:** Tkinter + ttk (Python's standard GUI toolkit)
- **Database:** SQLite (via Python's `sqlite3` module)
- **Charts:** Tkinter Canvas (no external charting library)
- **Data export:** Python's `csv` module
- **Money precision:** integer centavos instead of floating-point amounts

## Project limitations

This is a single-user, offline, personal-budgeting application, not a digital wallet or banking app. It does not connect to GCash or real bank accounts, make payments, sync between devices, or send notifications. The income/expense balance is computed only from transactions you enter.
