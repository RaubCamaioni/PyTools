# savings, compound interest, investment, growth, calculator

from pathlib import Path
from typing import Literal
import csv


def compound_interest_calculator(
    starting_amount: float = 10000,
    monthly_contribution: float = 200,
    annual_rate_percent: float = 7,
    years: int = 20,
    compounding: Literal["monthly", "yearly", "daily"] = "monthly",
) -> dict:
    """How savings or an investment grow with compound interest and regular monthly
    contributions: final balance, interest earned, the year-by-year table as CSV, and
    the doubling time (rule of 72).
    """
    years = max(1, min(years, 100))
    periods = {"monthly": 12, "yearly": 1, "daily": 365}[compounding]
    rate = max(0.0, annual_rate_percent) / 100 / periods
    balance, contributed, rows = starting_amount, starting_amount, []
    for year in range(1, years + 1):
        for p in range(periods):
            balance *= 1 + rate
            # contributions arrive monthly whatever the compounding period
            if periods == 12:
                deposit = monthly_contribution
            elif periods == 1:
                deposit = monthly_contribution * 12
            else:
                deposit = monthly_contribution if p % 30 == 0 and p < 360 else 0
            balance += deposit
            contributed += deposit
        rows.append([year, round(contributed, 2), round(balance - contributed, 2), round(balance, 2)])
    out = Path("growth_by_year.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "total_contributed", "interest_earned", "balance"])
        writer.writerows(rows)
    return {
        "file": out,
        "final_balance": round(balance, 2),
        "total_contributed": round(contributed, 2),
        "interest_earned": round(balance - contributed, 2),
        "doubling_time_years_rule_of_72": round(72 / annual_rate_percent, 1) if annual_rate_percent > 0 else "never",
    }
