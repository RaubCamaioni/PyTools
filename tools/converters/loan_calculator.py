# loan, mortgage, payment, amortization, interest, calculator

from pathlib import Path
import csv


def loan_calculator(
    amount: float = 250000, annual_rate_percent: float = 6.5, years: float = 30, extra_monthly_payment: float = 0
) -> dict:
    """Monthly payment, total interest and payoff date for a loan or mortgage, with the
    full amortisation schedule as a CSV. Add an extra monthly payment to see how much
    it saves.
    """
    months = int(max(1.0, years) * 12)
    r = max(0.0, annual_rate_percent) / 100 / 12
    payment = amount / months if r == 0 else amount * r / (1 - (1 + r) ** -months)
    balance, total_interest, rows = amount, 0.0, []
    month = 0
    while balance > 0.005 and month < 1200:
        month += 1
        interest = balance * r
        principal = min(balance, payment + max(0.0, extra_monthly_payment) - interest)
        balance -= principal
        total_interest += interest
        rows.append(
            [
                month,
                round(payment + max(0.0, extra_monthly_payment) if balance > 0 else principal + interest, 2),
                round(principal, 2),
                round(interest, 2),
                round(max(0.0, balance), 2),
            ]
        )
    out = Path("amortization_schedule.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "payment", "principal", "interest", "balance"])
        writer.writerows(rows)
    base_interest = payment * months - amount
    return {
        "file": out,
        "monthly_payment": round(payment, 2),
        "months_to_pay_off": month,
        "years_to_pay_off": round(month / 12, 1),
        "total_paid": round(amount + total_interest, 2),
        "total_interest": round(total_interest, 2),
        "interest_saved_by_extra_payments": (
            round(base_interest - total_interest, 2) if extra_monthly_payment > 0 else 0
        ),
        "months_saved_by_extra_payments": months - month if extra_monthly_payment > 0 else 0,
    }
