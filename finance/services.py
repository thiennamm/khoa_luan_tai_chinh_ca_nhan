from decimal import Decimal
from .models import Kind, Transaction


def recorded_totals(rows):
    """Shared Decimal addition; rows contain only recorded (kind, amount) pairs."""
    totals = {"income": Decimal("0"), "expense": Decimal("0")}
    for kind, amount in rows:
        totals[kind] += amount
    return {"income": totals[Kind.INCOME], "expense": totals[Kind.EXPENSE],
            "balance": totals[Kind.INCOME] - totals[Kind.EXPENSE]}


def monthly_totals(user, start, end):
    """Cộng Decimal theo từng dòng để giữ chính xác VND khi dùng SQLite."""
    rows = Transaction.objects.filter(user=user, date__gte=start, date__lt=end)
    return recorded_totals(rows.values_list("kind", "amount").iterator())
