from decimal import Decimal
from .models import Kind, Transaction


def monthly_totals(user, start, end):
    """Cộng Decimal theo từng dòng để giữ chính xác VND khi dùng SQLite."""
    totals = {"income": Decimal("0"), "expense": Decimal("0")}
    rows = Transaction.objects.filter(user=user, date__gte=start, date__lt=end)
    for kind, amount in rows.values_list("kind", "amount").iterator():
        totals[kind] += amount
    return {"income": totals[Kind.INCOME], "expense": totals[Kind.EXPENSE],
            "balance": totals[Kind.INCOME] - totals[Kind.EXPENSE]}
