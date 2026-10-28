"""BudgetBuddy: a complete offline student budgeting app made with Tkinter.

Run: python app.py
Python: 3.10+
No external libraries required.
"""
from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from database import (BudgetDatabase, EXPENSE_CATEGORIES, INCOME_CATEGORIES,
                      parse_money, peso, shift_month)

BG = "#F5F7FB"
WHITE = "#FFFFFF"
NAV = "#17283F"
NAV_HOVER = "#263C58"
GREEN = "#16A783"
GREEN_PALE = "#E8F9F3"
RED = "#E65F76"
RED_PALE = "#FFF0F3"
BLUE = "#466BE7"
BLUE_PALE = "#EFF2FF"
TEXT = "#202F45"
SUBTEXT = "#75849A"
BORDER = "#E7ECF2"
COLORS = ["#16A783", "#5476E5", "#EFAB4E", "#DE6C89", "#976CE3",
          "#43A7C8", "#6BBD72", "#EB7C5A", "#8A9CB7", "#BE93C6"]
FONT = "Segoe UI"


def label(parent, text, size=11, color=TEXT, bold=False, **kwargs):
    return tk.Label(parent, text=text, font=(FONT, size, "bold" if bold else "normal"),
                    fg=color, bg=parent.cget("bg"), **kwargs)


def frame(parent, bg=WHITE, **kwargs):
    return tk.Frame(parent, bg=bg, **kwargs)


def action(parent, text, command, primary=True, small=False):
    color = GREEN if primary else "#E9EFF5"
    fg = WHITE if primary else TEXT
    btn = tk.Button(parent, text=text, command=command, bg=color, fg=fg,
                    activebackground="#108B6E" if primary else "#DDE6EE",
                    activeforeground=fg, font=(FONT, 10, "bold"),
                    bd=0, relief="flat", cursor="hand2", padx=15 if small else 20,
                    pady=7 if small else 10, highlightthickness=0)
    return btn


def bordered_card(parent, padx=19, pady=17):
    outer = frame(parent, BORDER)
    inner = frame(outer)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    contents = frame(inner)
    contents.pack(fill="both", expand=True, padx=padx, pady=pady)
    return outer, contents


class TransactionDialog(tk.Toplevel):
    def __init__(self, parent: "BudgetBuddyApp", existing=None):
        super().__init__(parent)
        self.app = parent
        self.existing = existing
        self.title("Edit transaction" if existing else "Add transaction")
        self.configure(bg=WHITE)
        self.geometry("445x555")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.kind = tk.StringVar(value=existing["kind"] if existing else "Expense")
        self.when = tk.StringVar(value=existing["transaction_date"] if existing else date.today().isoformat())
        self.category = tk.StringVar(value=existing["category"] if existing else EXPENSE_CATEGORIES[0])
        self.amount = tk.StringVar(value=f'{existing["amount_cents"]/100:.2f}' if existing else "")
        self.note = tk.StringVar(value=existing["note"] if existing else "")

        body = frame(self)
        body.pack(fill="both", expand=True, padx=30, pady=24)
        label(body, "Edit transaction" if existing else "New transaction", 21, bold=True).pack(anchor="w")
        label(body, "Record your income or expense.", 10, SUBTEXT).pack(anchor="w", pady=(4, 20))
        label(body, "TRANSACTION TYPE", 9, SUBTEXT, bold=True).pack(anchor="w")
        toggle = frame(body)
        toggle.pack(fill="x", pady=(7, 15))
        self.kind_buttons = {}
        for kind in ("Expense", "Income"):
            btn = tk.Button(toggle, text=kind, font=(FONT, 10, "bold"), bd=0,
                            cursor="hand2", pady=10, command=lambda k=kind: self.change_kind(k))
            btn.pack(side="left", expand=True, fill="x", padx=(0, 5) if kind == "Expense" else (5, 0))
            self.kind_buttons[kind] = btn
        self._refresh_kind()

        self._field(body, "DATE (YYYY-MM-DD)")
        self.date_entry = ttk.Entry(body, textvariable=self.when, font=(FONT, 11))
        self.date_entry.pack(fill="x", ipady=8, pady=(5, 13))
        self._field(body, "CATEGORY (YOU CAN TYPE A NEW ONE)")
        self.category_box = ttk.Combobox(body, textvariable=self.category, state="normal", font=(FONT, 11))
        self.category_box.pack(fill="x", ipady=7, pady=(5, 13))
        self._refresh_categories()
        self._field(body, "AMOUNT IN PHP")
        self.amount_entry = ttk.Entry(body, textvariable=self.amount, font=(FONT, 11))
        self.amount_entry.pack(fill="x", ipady=8, pady=(5, 13))
        self._field(body, "NOTE (OPTIONAL)")
        self.note_entry = ttk.Entry(body, textvariable=self.note, font=(FONT, 11))
        self.note_entry.pack(fill="x", ipady=8, pady=(5, 20))
        buttons = frame(body)
        buttons.pack(fill="x")
        action(buttons, "Cancel", self.destroy, primary=False).pack(side="left")
        action(buttons, "Save Transaction", self.save).pack(side="right")
        self.bind("<Return>", lambda _event: self.save())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.amount_entry.focus_set()
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx()+max(0,(parent.winfo_width()-445)//2)}"
                      f"+{parent.winfo_rooty()+max(0,(parent.winfo_height()-555)//2)}")

    def _field(self, parent, title):
        label(parent, title, 9, SUBTEXT, bold=True).pack(anchor="w")

    def _refresh_kind(self):
        for kind, button in self.kind_buttons.items():
            active = self.kind.get() == kind
            button.configure(bg=GREEN if active and kind == "Income" else
                             RED if active else "#EDF1F6", fg=WHITE if active else TEXT)

    def _refresh_categories(self):
        kind = self.kind.get()
        standard = EXPENSE_CATEGORIES if kind == "Expense" else INCOME_CATEGORIES
        used = {tx["category"] for tx in self.app.db.list_transactions(kind=kind)}
        categories = list(standard) + sorted(used - set(standard))
        self.category_box.configure(values=categories)

    def change_kind(self, kind):
        if self.kind.get() != kind:
            self.kind.set(kind)
            self.category.set(EXPENSE_CATEGORIES[0] if kind == "Expense" else INCOME_CATEGORIES[0])
        self._refresh_kind()
        self._refresh_categories()

    def save(self):
        try:
            cents = parse_money(self.amount.get())
            if self.existing:
                self.app.db.update_transaction(self.existing["id"], self.when.get(),
                                               self.kind.get(), self.category.get(), cents, self.note.get())
            else:
                self.app.db.add_transaction(self.when.get(), self.kind.get(),
                                            self.category.get(), cents, self.note.get())
        except ValueError as error:
            messagebox.showerror("Check your entry", str(error), parent=self)
            return
        self.destroy()
        self.app.refresh()


class BudgetDialog(tk.Toplevel):
    def __init__(self, parent: "BudgetBuddyApp", existing=None):
        super().__init__(parent)
        self.app = parent
        self.configure(bg=WHITE)
        self.title("Set monthly budget")
        self.geometry("440x340")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.category = tk.StringVar(value=existing["category"] if existing else EXPENSE_CATEGORIES[0])
        self.amount = tk.StringVar(value=f'{existing["limit_cents"]/100:.2f}' if existing else "")
        content = frame(self)
        content.pack(fill="both", expand=True, padx=28, pady=23)
        label(content, "Monthly spending limit", 20, bold=True).pack(anchor="w")
        label(content, f"Budget for {parent.pretty_month()}", 10, SUBTEXT).pack(anchor="w", pady=(4, 20))
        label(content, "EXPENSE CATEGORY", 9, SUBTEXT, bold=True).pack(anchor="w")
        used = {tx["category"] for tx in parent.db.list_transactions(kind="Expense")}
        categories = EXPENSE_CATEGORIES + sorted(used - set(EXPENSE_CATEGORIES))
        self.combo = ttk.Combobox(content, textvariable=self.category, values=categories,
                                  font=(FONT, 11), state="readonly" if existing else "normal")
        self.combo.pack(fill="x", ipady=8, pady=(6, 17))
        label(content, "LIMIT IN PHP", 9, SUBTEXT, bold=True).pack(anchor="w")
        entry = ttk.Entry(content, textvariable=self.amount, font=(FONT, 11))
        entry.pack(fill="x", ipady=8, pady=(6, 22))
        footer = frame(content)
        footer.pack(fill="x")
        action(footer, "Cancel", self.destroy, primary=False).pack(side="left")
        action(footer, "Save Budget", self.save).pack(side="right")
        entry.focus_set()
        self.bind("<Return>", lambda _event: self.save())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx()+max(0,(parent.winfo_width()-440)//2)}"
                      f"+{parent.winfo_rooty()+max(0,(parent.winfo_height()-340)//2)}")

    def save(self):
        try:
            self.app.db.set_budget(self.app.month, self.category.get(), parse_money(self.amount.get()))
        except ValueError as error:
            messagebox.showerror("Check your budget", str(error), parent=self)
            return
        self.destroy()
        self.app.refresh()


class BudgetBuddyApp(tk.Tk):
    def __init__(self, db=None):
        super().__init__()
        self.db = db or BudgetDatabase()
        self.month = date.today().strftime("%Y-%m")
        self.page = "Dashboard"
        self.search_var = tk.StringVar()
        self.kind_var = tk.StringVar(value="All")
        self.all_months_var = tk.BooleanVar(value=False)
        self.title("BudgetBuddy | Your Money, Made Simple")
        self.configure(bg=BG)
        self.geometry("1190x740")
        self.minsize(940, 620)
        self._configure_styles()
        self._sidebar()
        self.content = frame(self, BG)
        self.content.pack(side="right", fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.refresh()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Budget.Treeview", font=(FONT, 10), rowheight=39,
                        background=WHITE, fieldbackground=WHITE,
                        foreground=TEXT, borderwidth=0)
        style.configure("Budget.Treeview.Heading", font=(FONT, 10, "bold"),
                        background="#F5F7FA", foreground=SUBTEXT, padding=(8, 10),
                        relief="flat")
        style.map("Budget.Treeview", background=[("selected", "#DBF3EC")],
                  foreground=[("selected", TEXT)])
        style.configure("TCombobox", padding=5)

    def _sidebar(self):
        side = frame(self, NAV, width=220)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        brand = frame(side, NAV)
        brand.pack(fill="x", padx=23, pady=(32, 4))
        tk.Label(brand, text="●", fg="#2BD6A7", bg=NAV, font=(FONT, 20, "bold")).pack(side="left", padx=(0, 8))
        tk.Label(brand, text="BudgetBuddy", fg=WHITE, bg=NAV,
                 font=(FONT, 16, "bold")).pack(side="left")
        tk.Label(side, text="YOUR MONEY, MADE SIMPLE", fg="#96AAC2", bg=NAV,
                 font=(FONT, 8, "bold")).pack(anchor="w", padx=30, pady=(0, 41))
        tk.Label(side, text="WORKSPACE", fg="#7F94AE", bg=NAV,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=28, pady=(0, 15))
        self.nav_buttons = {}
        for icon, name in [("▦", "Dashboard"), ("⇄", "Transactions"),
                           ("◎", "Budgets"), ("◕", "Insights")]:
            button = tk.Button(side, text=f" {icon}     {name}", anchor="w",
                               bg=NAV, fg="#CBD9E8", activebackground=NAV_HOVER,
                               activeforeground=WHITE, bd=0, relief="flat",
                               cursor="hand2", font=(FONT, 11, "bold"), padx=23, pady=15,
                               highlightthickness=0,
                               command=lambda n=name: self.open_page(n))
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[name] = button
        bottom = frame(side, NAV)
        bottom.pack(side="bottom", fill="x", padx=24, pady=22)
        tk.Label(bottom, text="100% OFFLINE", bg=NAV, fg="#31D8AC",
                 font=(FONT, 9, "bold")).pack(anchor="w")
        tk.Label(bottom, text="Your data stays on this computer.", bg=NAV,
                 fg="#9FB0C6", font=(FONT, 9), wraplength=170,
                 justify="left").pack(anchor="w", pady=(5, 0))

    def open_page(self, name):
        self.page = name
        self.refresh()

    def pretty_month(self):
        return datetime.strptime(self.month, "%Y-%m").strftime("%B %Y")

    def change_month(self, direction):
        self.month = shift_month(self.month, direction)
        self.refresh()

    def refresh(self):
        for child in self.content.winfo_children():
            child.destroy()
        for name, button in self.nav_buttons.items():
            active = name == self.page
            button.configure(bg=NAV_HOVER if active else NAV,
                             fg=WHITE if active else "#CBD9E8")
        header = frame(self.content, BG)
        header.pack(fill="x", padx=30, pady=(27, 18))
        left = frame(header, BG)
        left.pack(side="left")
        label(left, self.page, 25, TEXT, bold=True).pack(anchor="w")
        subtitles = {
            "Dashboard": "Here's how your money is doing this month.",
            "Transactions": "Keep track of every peso in and out.",
            "Budgets": "Plan your spending and stay in control.",
            "Insights": "See your spending habits at a glance.",
        }
        label(left, subtitles[self.page], 10, SUBTEXT).pack(anchor="w", pady=(4, 0))
        right = frame(header, BG)
        right.pack(side="right", anchor="n", pady=8)
        if self.page != "Transactions":
            self._month_picker(right)
        action(right, "+ Add Transaction", self.add_transaction, small=True).pack(side="right", padx=(0, 12))

        container = frame(self.content, BG)
        container.pack(fill="both", expand=True, padx=30, pady=(0, 26))
        if self.page == "Dashboard":
            self._dashboard(container)
        elif self.page == "Transactions":
            self._transactions(container)
        elif self.page == "Budgets":
            self._budgets(container)
        else:
            self._insights(container)

    def _month_picker(self, parent):
        holder = frame(parent, WHITE)
        holder.pack(side="right")
        for text, command in [("‹", lambda: self.change_month(-1)),
                              ("›", lambda: self.change_month(1))]:
            if text == "›":
                label(holder, self.pretty_month(), 10, TEXT, bold=True).pack(side="left", padx=6)
            button = tk.Button(holder, text=text, command=command, bg=WHITE,
                               fg=TEXT, activebackground=BG, bd=0, cursor="hand2",
                               font=(FONT, 17), padx=10, pady=1)
            button.pack(side="left")

    def add_transaction(self):
        TransactionDialog(self)

    def _stat(self, parent, heading, value, caption, tint=TEXT):
        outer, content = bordered_card(parent, 16, 14)
        label(content, heading, 10, SUBTEXT, bold=True).pack(anchor="w")
        label(content, value, 21, tint, bold=True).pack(anchor="w", pady=(9, 4))
        label(content, caption, 9, SUBTEXT).pack(anchor="w")
        return outer

    def _section_title(self, parent, title, subtitle=""):
        head = frame(parent)
        head.pack(fill="x", pady=(0, 15))
        label(head, title, 14, bold=True).pack(side="left")
        if subtitle:
            label(head, subtitle, 9, SUBTEXT).pack(side="right")

    def _dashboard(self, parent):
        totals = self.db.totals(self.month)
        income, expense = totals["Income"], totals["Expense"]
        net = income - expense
        stats = frame(parent, BG)
        stats.pack(fill="x")
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1, uniform="metric")
        self._stat(stats, "MONTHLY INCOME", peso(income), "Money received", GREEN).grid(
            row=0, column=0, sticky="nsew", padx=(0, 7))
        self._stat(stats, "MONTHLY EXPENSES", peso(expense), "Money spent", RED).grid(
            row=0, column=1, sticky="nsew", padx=7)
        self._stat(stats, "MONTHLY SAVINGS", peso(net), "Income minus expenses", GREEN if net >= 0 else RED).grid(
            row=0, column=2, sticky="nsew", padx=7)
        self._stat(stats, "TOTAL BALANCE", peso(self.db.lifetime_balance()), "Across all months", BLUE).grid(
            row=0, column=3, sticky="nsew", padx=(7, 0))

        recent_card, recent_body = bordered_card(parent, 18, 13)
        recent_card.pack(side="bottom", fill="x")
        recent_head = frame(recent_body)
        recent_head.pack(fill="x", pady=(0, 7))
        label(recent_head, "Recent transactions", 14, bold=True).pack(side="left")
        tk.Button(recent_head, text="View all  →", bg=WHITE, fg=BLUE, font=(FONT, 10, "bold"),
                  bd=0, highlightthickness=0, cursor="hand2",
                  command=lambda: self.open_page("Transactions")).pack(side="right")
        records = self.db.list_transactions(self.month, limit=3)
        for tx in records:
            row = frame(recent_body)
            row.pack(fill="x", pady=5)
            label(row, tx["transaction_date"], 9, SUBTEXT, width=12, anchor="w").pack(side="left")
            summary = tx["category"] + ("  ·  " + tx["note"][:35] if tx["note"] else "")
            label(row, summary, 10, TEXT, anchor="w").pack(side="left", fill="x", expand=True)
            amount = ("+" if tx["kind"] == "Income" else "−") + peso(tx["amount_cents"])
            label(row, amount, 10, GREEN if tx["kind"] == "Income" else RED,
                  bold=True, anchor="e").pack(side="right", padx=(8, 0))
            frame(recent_body, BORDER, height=1).pack(fill="x")
        if not records:
            note = frame(recent_body)
            note.pack(fill="x", pady=8)
            label(note, "Add your first transaction or load sample data to explore the app.",
                  10, SUBTEXT).pack(side="left")
            if self.db.transaction_count() == 0:
                action(note, "Load Demo Data", self.load_demo, small=True).pack(side="right")

        middle = frame(parent, BG)
        middle.pack(fill="both", expand=True, pady=(18, 16))
        middle.grid_columnconfigure(0, weight=3)
        middle.grid_columnconfigure(1, weight=2)
        middle.grid_rowconfigure(0, weight=1)
        chart_card, chart = bordered_card(middle, 18, 16)
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        self._section_title(chart, "Spending activity", "Daily expenses")
        graph = tk.Canvas(chart, bg=WHITE, bd=0, highlightthickness=0, height=135)
        graph.pack(fill="both", expand=True)
        graph.bind("<Configure>", lambda _e: self._bar_chart(graph, self.db.day_expenses(self.month)))
        category_card, category_body = bordered_card(middle, 18, 16)
        category_card.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        self._section_title(category_body, "Top categories")
        self._category_list(category_body, self.db.expense_categories(self.month), max_rows=3)

    def _bar_chart(self, canvas, records):
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 80 or h < 90:
            return
        left, bottom, top, right = 53, h - 30, 16, w - 10
        if not records:
            canvas.create_text(w/2, h/2, text="No expenses for this month yet",
                               fill=SUBTEXT, font=(FONT, 11))
            return
        daily = {int(item["day"][-2:]): item["amount"] for item in records}
        year, mm = map(int, self.month.split("-"))
        count = calendar.monthrange(year, mm)[1]
        max_value = max(daily.values())
        for line in range(4):
            y = top + (bottom - top) * line / 3
            canvas.create_line(left, y, right, y, fill="#ECF0F5", width=1)
            amount = int(max_value * (3-line)/3)
            label_text = (f"₱{amount/1000:.0f}k" if amount >= 100000 else
                          f"₱{amount/100:.0f}")
            canvas.create_text(left-7, y, text=label_text, anchor="e", fill=SUBTEXT,
                               font=(FONT, 8))
        slot = (right-left)/count
        bar = max(3, slot * .58)
        for day in range(1, count+1):
            amount = daily.get(day, 0)
            if amount:
                xmid = left+(day-.5)*slot
                height = (bottom-top)*amount/max_value
                canvas.create_rectangle(xmid-bar/2, bottom-height,
                                        xmid+bar/2, bottom, fill=GREEN, outline="")
        for day in [1, 7, 14, 21, count]:
            canvas.create_text(left+(day-.5)*slot, bottom+14, text=str(day),
                               fill=SUBTEXT, font=(FONT, 8))

    def _category_list(self, parent, records, max_rows=100):
        if not records:
            label(parent, "No expenses to show yet.", 11, SUBTEXT).pack(pady=33)
            return
        grand_total = sum(record["amount"] for record in records)
        for index, record in enumerate(records[:max_rows]):
            line = frame(parent)
            line.pack(fill="x", pady=9)
            label(line, "●", 13, COLORS[index % len(COLORS)]).pack(side="left", padx=(0, 8))
            title = label(line, record["category"], 10)
            title.pack(side="left", fill="x", expand=True)
            label(line, peso(record["amount"]), 10, bold=True).pack(side="right")
            bar_bg = frame(parent, "#F0F3F8", height=5)
            bar_bg.pack(fill="x", pady=(0, 1))
            bar_bg.pack_propagate(False)
            fill = frame(bar_bg, COLORS[index % len(COLORS)])
            fraction = record["amount"] / grand_total if grand_total else 0
            fill.place(relx=0, rely=0, relheight=1, relwidth=fraction)
        if len(records) > max_rows:
            label(parent, f"+ {len(records)-max_rows} more categories", 9, SUBTEXT).pack(pady=(8, 0))

    def _transaction_table(self, parent, records, height=10, short=False):
        cols = ("date", "description", "type", "amount") if short else ("date", "category", "note", "type", "amount")
        table = ttk.Treeview(parent, columns=cols, show="headings", height=height,
                             style="Budget.Treeview", selectmode="browse")
        widths = {"date": 110, "description": 215, "category": 175,
                  "note": 245, "type": 88, "amount": 130}
        for col in cols:
            table.heading(col, text=col.upper() if col != "description" else "CATEGORY / NOTES")
            table.column(col, width=widths[col], stretch=col in ("description", "note", "category"),
                         anchor="e" if col == "amount" else "w", minwidth=70)
        table.tag_configure("income", foreground=GREEN)
        table.tag_configure("expense", foreground=TEXT)
        for tx in records:
            amount = ("+" if tx["kind"] == "Income" else "−") + peso(tx["amount_cents"])
            desc = tx["category"] + ("  ·  " + tx["note"][:35] if tx["note"] else "")
            values = (tx["transaction_date"], desc, tx["kind"], amount) if short else (
                tx["transaction_date"], tx["category"], tx["note"], tx["kind"], amount)
            table.insert("", "end", iid=str(tx["id"]), values=values,
                         tags=("income" if tx["kind"] == "Income" else "expense",))
        if not short:
            scroll = ttk.Scrollbar(parent, orient="vertical", command=table.yview)
            table.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")
        table.pack(fill="both", expand=True)
        return table

    def _transactions(self, parent):
        controls, toolbar = bordered_card(parent, 18, 15)
        controls.pack(fill="x", pady=(0, 17))
        top = frame(toolbar)
        top.pack(fill="x")
        label(top, "Search", 10, SUBTEXT, bold=True).pack(side="left", padx=(0, 8))
        query = ttk.Entry(top, textvariable=self.search_var, width=23, font=(FONT, 10))
        query.pack(side="left", ipady=7, padx=(0, 15))
        query.bind("<Return>", lambda _event: self.refresh())
        label(top, "Type", 10, SUBTEXT, bold=True).pack(side="left", padx=(0, 8))
        type_filter = ttk.Combobox(top, textvariable=self.kind_var,
                                   values=["All", "Income", "Expense"], width=11, state="readonly")
        type_filter.pack(side="left", padx=(0, 15))
        type_filter.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        action(top, "Search", self.refresh, primary=False, small=True).pack(side="left", padx=(0, 8))
        action(top, "Export CSV", self.export_transactions, small=True).pack(side="right")
        second = frame(toolbar)
        second.pack(fill="x", pady=(13, 0))
        tk.Checkbutton(second, text="All months", variable=self.all_months_var,
                       command=self.refresh, bg=WHITE, fg=TEXT,
                       font=(FONT, 10), activebackground=WHITE).pack(side="left")
        if not self.all_months_var.get():
            self._month_picker(second)
        chosen_month = None if self.all_months_var.get() else self.month
        records = self.db.list_transactions(chosen_month, self.kind_var.get(), self.search_var.get())
        card, body = bordered_card(parent, 18, 15)
        card.pack(fill="both", expand=True)
        head = frame(body)
        head.pack(fill="x", pady=(0, 12))
        label(head, f"Transactions ({len(records)})", 15, bold=True).pack(side="left")
        action(head, "Delete Selected", self.delete_selected, primary=False, small=True).pack(side="right")
        action(head, "Edit Selected", self.edit_selected, primary=False, small=True).pack(side="right", padx=(0, 8))
        self.table = self._transaction_table(body, records, height=11)
        self.table.bind("<Double-1>", lambda _event: self.edit_selected())
        if not records:
            label(body, "No matching transactions. Add one or change your filters.",
                  10, SUBTEXT).pack(pady=13)

    def _selected_transaction(self):
        if not hasattr(self, "table") or not self.table.winfo_exists() or not self.table.selection():
            messagebox.showinfo("Select a transaction", "Click a transaction in the table first.", parent=self)
            return None
        return self.db.get_transaction(int(self.table.selection()[0]))

    def edit_selected(self):
        tx = self._selected_transaction()
        if tx:
            TransactionDialog(self, tx)

    def delete_selected(self):
        tx = self._selected_transaction()
        if tx and messagebox.askyesno("Delete transaction", "Delete this transaction permanently?", parent=self):
            self.db.delete_transaction(tx["id"])
            self.refresh()

    def export_transactions(self):
        target = filedialog.asksaveasfilename(title="Export BudgetBuddy transactions",
                                              defaultextension=".csv",
                                              filetypes=[("CSV spreadsheet", "*.csv")],
                                              initialfile=f"BudgetBuddy_{self.month}.csv",
                                              parent=self)
        if not target:
            return
        try:
            count = self.db.export_csv(target,
                                       None if self.all_months_var.get() else self.month,
                                       self.kind_var.get(), self.search_var.get())
        except OSError as error:
            messagebox.showerror("Export failed", str(error), parent=self)
            return
        messagebox.showinfo("Export complete", f"Exported {count} transaction(s) to:\n{target}", parent=self)

    def _budgets(self, parent):
        progress = self.db.budget_progress(self.month)
        allocated = sum(b["limit_cents"] for b in progress)
        spent = sum(b["spent_cents"] for b in progress)
        top = frame(parent, BG)
        top.pack(fill="x", pady=(0, 15))
        for i in range(3):
            top.grid_columnconfigure(i, weight=1, uniform="budget_stat")
        self._stat(top, "TOTAL ALLOCATED", peso(allocated), "Monthly category limits", BLUE).grid(
            row=0, column=0, sticky="ew", padx=(0, 8))
        self._stat(top, "SPENT IN BUDGETS", peso(spent), "Expenses in budgeted categories", RED).grid(
            row=0, column=1, sticky="ew", padx=8)
        self._stat(top, "REMAINING", peso(allocated-spent), "Across budgeted categories",
                   GREEN if allocated >= spent else RED).grid(row=0, column=2, sticky="ew", padx=(8, 0))
        card, body = bordered_card(parent, 22, 19)
        card.pack(fill="both", expand=True)
        heading = frame(body)
        heading.pack(fill="x", pady=(0, 18))
        label(heading, "Category budgets", 15, bold=True).pack(side="left")
        action(heading, "+ Set Budget", lambda: BudgetDialog(self), small=True).pack(side="right")
        if not progress:
            empty = frame(body)
            empty.pack(fill="both", expand=True)
            label(empty, "No budgets for this month yet.", 15, TEXT, bold=True).pack(pady=(65, 6))
            label(empty, "Set a spending limit for Food, School, Transportation, and more.",
                  10, SUBTEXT).pack()
            return
        canvas = tk.Canvas(body, bg=WHITE, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        list_frame = frame(canvas)
        window = canvas.create_window((0, 0), window=list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        list_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for b in progress:
            ratio = b["spent_cents"] / b["limit_cents"]
            category = b["category"]
            item = frame(list_frame)
            item.pack(fill="x", pady=(7, 16))
            top_row = frame(item)
            top_row.pack(fill="x")
            label(top_row, category, 12, bold=True).pack(side="left")
            delete_btn = tk.Button(top_row, text="Remove", fg=RED, bg=WHITE, bd=0,
                                   cursor="hand2", font=(FONT, 9),
                                   command=lambda c=category: self.remove_budget(c))
            delete_btn.pack(side="right", padx=(10, 0))
            edit_btn = tk.Button(top_row, text="Edit", fg=BLUE, bg=WHITE, bd=0,
                                 cursor="hand2", font=(FONT, 9, "bold"),
                                 command=lambda b=b: BudgetDialog(self, b))
            edit_btn.pack(side="right")
            label(top_row, f'{peso(b["spent_cents"])} / {peso(b["limit_cents"])}',
                  10, SUBTEXT).pack(side="right", padx=(0, 15))
            bar = frame(item, "#EEF2F6", height=11)
            bar.pack(fill="x", pady=(11, 6))
            bar.pack_propagate(False)
            frame(bar, RED if ratio >= 1 else GREEN).place(relx=0, rely=0,
                                                           relwidth=min(1, ratio), relheight=1)
            status = f"{ratio*100:.0f}% used"
            if ratio > 1:
                status += "  •  Over budget by " + peso(b["spent_cents"]-b["limit_cents"])
            elif ratio >= .8:
                status += "  •  Close to your limit"
            else:
                status += "  •  " + peso(b["limit_cents"]-b["spent_cents"]) + " left"
            label(item, status, 9, RED if ratio >= 1 else SUBTEXT).pack(anchor="w")
            frame(item, BORDER, height=1).pack(fill="x", pady=(15, 0))

    def remove_budget(self, category):
        if messagebox.askyesno("Remove budget", f"Remove your {category} budget for {self.pretty_month()}?",
                               parent=self):
            self.db.delete_budget(self.month, category)
            self.refresh()

    def _insights(self, parent):
        month_totals = self.db.totals(self.month)
        income, spent = month_totals["Income"], month_totals["Expense"]
        rate = (income-spent)/income * 100 if income else 0
        last = self.db.totals(shift_month(self.month, -1))
        top = frame(parent, BG)
        top.pack(fill="x", pady=(0, 15))
        for i in range(3):
            top.grid_columnconfigure(i, weight=1, uniform="insight")
        self._stat(top, "SAVINGS RATE", f"{rate:.1f}%" if income else "N/A",
                   "Of this month's income", GREEN if rate >= 0 else RED).grid(
                       row=0, column=0, sticky="ew", padx=(0, 8))
        self._stat(top, "LAST MONTH'S SPENDING", peso(last["Expense"]),
                   "For comparison", BLUE).grid(row=0, column=1, sticky="ew", padx=8)
        difference = spent - last["Expense"]
        self._stat(top, "SPENDING CHANGE", ("+" if difference > 0 else "") + peso(difference),
                   "Compared with last month", GREEN if difference <= 0 else RED).grid(
                       row=0, column=2, sticky="ew", padx=(8, 0))
        tip_card, tip = bordered_card(parent, 18, 15)
        tip_card.pack(side="bottom", fill="x", pady=(16, 0))
        label(tip, "BUDGETBUDDY TIP", 10, GREEN, bold=True).pack(anchor="w")
        if not income and not spent:
            suggestion = "Add your income and expenses to get helpful monthly insights."
        elif spent > income:
            suggestion = "You're spending more than you earned this month. Consider reducing optional expenses."
        elif rate >= 20:
            suggestion = "Great job! You're saving at least 20% of your monthly income."
        else:
            suggestion = "Try setting category budgets to put more money toward your savings goals."
        label(tip, suggestion, 11, TEXT).pack(anchor="w", pady=(7, 0))

        middle = frame(parent, BG)
        middle.pack(fill="both", expand=True)
        middle.grid_rowconfigure(0, weight=1)
        middle.grid_columnconfigure(0, weight=3)
        middle.grid_columnconfigure(1, weight=2)
        graph_card, graph_body = bordered_card(middle, 18, 16)
        graph_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._section_title(graph_body, "Where your money went", "Expenses by category")
        categories = self.db.expense_categories(self.month)
        pie = tk.Canvas(graph_body, bg=WHITE, highlightthickness=0, bd=0, height=200)
        pie.pack(fill="both", expand=True)
        pie.bind("<Configure>", lambda _e: self._donut(pie, categories))
        right_card, right_body = bordered_card(middle, 18, 16)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._section_title(right_body, "Spending breakdown")
        self._category_list(right_body, categories, max_rows=5)

    def _donut(self, canvas, records):
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 100 or h < 100:
            return
        total = sum(r["amount"] for r in records)
        if not total:
            canvas.create_text(w/2, h/2, text="No spending data yet", fill=SUBTEXT,
                               font=(FONT, 12))
            return
        diameter = min(w - 40, h - 35, 240)
        cx, cy = w/2, h/2
        rect = (cx-diameter/2, cy-diameter/2, cx+diameter/2, cy+diameter/2)
        start = 90
        for i, record in enumerate(records):
            sweep = 360*record["amount"]/total
            canvas.create_arc(*rect, start=start, extent=-sweep,
                              style="pieslice", fill=COLORS[i % len(COLORS)], outline=WHITE, width=2)
            start -= sweep
        hole = diameter*.58
        canvas.create_oval(cx-hole/2, cy-hole/2, cx+hole/2, cy+hole/2,
                           fill=WHITE, outline=WHITE)
        canvas.create_text(cx, cy-13, text="TOTAL SPENT", fill=SUBTEXT,
                           font=(FONT, 9, "bold"))
        canvas.create_text(cx, cy+10, text=peso(total), fill=TEXT,
                           font=(FONT, 13 if diameter < 210 else 15, "bold"))

    def load_demo(self):
        if not messagebox.askyesno("Load sample data", "Add sample income, expenses and budgets "
                                   "for a classroom demonstration?", parent=self):
            return
        try:
            self.db.seed_demo(self.month)
        except ValueError as error:
            messagebox.showerror("Cannot load demo", str(error), parent=self)
            return
        self.refresh()
        messagebox.showinfo("Sample data added", "Explore Dashboard, Transactions, Budgets and Insights!",
                            parent=self)

    def exit_app(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    BudgetBuddyApp().mainloop()
