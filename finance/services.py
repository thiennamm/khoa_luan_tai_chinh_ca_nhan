from calendar import monthrange
from decimal import Decimal, localcontext
from django.db import connections
from django.db.models import Aggregate, CharField, Count, DateField, Q
from django.db.models.functions import TruncMonth
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


class _SQLiteDecimalSum:
    """SQLite SUM uses float/64-bit integers; keep exact VND inside its engine."""
    def __init__(self):
        self.total = Decimal('0')

    def step(self, value):
        if value is not None:
            with localcontext() as context:
                context.prec = 64
                self.total += Decimal(value)

    def finalize(self):
        return str(self.total)


class _RecordedSum(Aggregate):
    function = 'SUM'
    output_field = CharField()

    def as_sqlite(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection,
            template='finance_vnd_sum(CAST(%(expressions)s AS TEXT))', **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection,
            template='CAST(SUM(%(expressions)s) AS TEXT)', **extra_context)


def recorded_month_groups(user, months, today):
    """One bounded GROUP BY, keyed by category ID; never fetch transaction text."""
    months = sorted(set(months))
    if not months or len(months) > 12 or any(month.day != 1 for month in months):
        raise ValueError('Khoảng tổng hợp tháng không hợp lệ.')
    scope = Q()
    for month in months:
        scope |= Q(date__gte=month, date__lte=month.replace(day=monthrange(month.year, month.month)[1]))
    rows = Transaction.objects.filter(scope, user=user, category__user=user).order_by()
    connection = connections[rows.db]
    if connection.vendor == 'sqlite':
        connection.ensure_connection()
        connection.connection.create_aggregate('finance_vnd_sum', 1, _SQLiteDecimalSum)
    groups = rows.annotate(month=TruncMonth('date', output_field=DateField())).values(
        'month', 'kind', 'category_id', 'category__name').annotate(
            total=_RecordedSum('amount'), count=Count('pk'),
            future_count=Count('pk', filter=Q(date__gt=today)))
    for item in groups.iterator():
        item['total'] = Decimal(item['total'])
        yield item
