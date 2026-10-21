from decimal import Decimal
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, router, transaction
from django.utils import timezone
from .classification_labels import MAPPING_CHOICES, compatible_kind
from .coverage_calendar import current_month
from .coverage_state import lock_coverage_writes, reset_months
from .transaction_queries import TransactionQuerySet
from .forecast_state import bump_forecast_version


class Kind(models.TextChoices):
    INCOME = "income", "Thu nhập"
    EXPENSE = "expense", "Chi tiêu"


class ForecastDataVersion(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.CASCADE)
    version = models.PositiveBigIntegerField(default=0)


class ForecastResult(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    target_month = models.DateField()
    fingerprint = models.CharField(max_length=64)
    history_count = models.PositiveIntegerField()
    history_start = models.DateField()
    history_end = models.DateField()
    method = models.CharField(max_length=32)
    # SQLite NUMERIC/DecimalField có thể làm mất chữ số khi tổng >15 chữ số.
    # Lưu chuỗi số nguyên chính xác, khôi phục Decimal để dùng/hiển thị.
    estimate = models.CharField(max_length=30, validators=[RegexValidator(r'\A[0-9]{1,30}\Z')])
    details = models.JSONField(default=dict)
    configuration = models.JSONField(default=dict)
    calculated_at = models.DateTimeField(auto_now=True)

    @property
    def estimate_decimal(self):
        return Decimal(self.estimate)


class MonthlyCoverage(models.Model):
    class Status(models.TextChoices):
        UNKNOWN = 'unknown', 'Chưa xác nhận'
        INCOMPLETE = 'incomplete', 'Chưa đầy đủ'
        COMPLETE = 'complete', 'Đã xác nhận đầy đủ'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    month = models.DateField('Tháng')
    status = models.CharField('Trạng thái', max_length=12, choices=Status.choices, default=Status.UNKNOWN)
    confirmed_at = models.DateTimeField('Thời điểm xác nhận', null=True, blank=True)

    class Meta:
        ordering = ['month']
        constraints = [
            models.UniqueConstraint(fields=['user', 'month'], name='coverage_unique_user_month'),
            models.CheckConstraint(condition=models.Q(month__day=1), name='coverage_month_first_day'),
            models.CheckConstraint(condition=models.Q(status__in=['unknown', 'incomplete', 'complete']), name='coverage_valid_status'),
            models.CheckConstraint(condition=(
                models.Q(status='complete', confirmed_at__isnull=False)
                | models.Q(status__in=['unknown', 'incomplete'], confirmed_at__isnull=True)
            ), name='coverage_confirmation_timestamp'),
        ]

    def clean(self):
        super().clean()
        if self.month and self.month.day != 1:
            raise ValidationError({'month': 'Tháng phải được lưu bằng ngày đầu tháng.'})
        if self.month and self.status == self.Status.COMPLETE and self.month >= current_month():
            raise ValidationError({'month': 'Chỉ xác nhận đầy đủ tháng đã kết thúc theo giờ Việt Nam.'})
        if (self.status == self.Status.COMPLETE) != (self.confirmed_at is not None):
            raise ValidationError({'confirmed_at': 'Thời điểm xác nhận chỉ có khi trạng thái đã xác nhận đầy đủ.'})

    def save(self, *args, **kwargs):
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            self.full_clean()
            result = super().save(*args, **kwargs)
            bump_forecast_version([self.user_id], using)
            return result


class CsvImportBatch(models.Model):
    """Payload tạm ở SQLite phía máy chủ, không đặt trong session/cookie."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    sha256 = models.CharField(max_length=64)
    raw = models.BinaryField()
    category_bindings = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=12, default='pending', choices=[
        ('pending', 'Chờ xác nhận'), ('processing', 'Đang xử lý'), ('completed', 'Đã nhập')])


class CsvImportReceipt(models.Model):
    """Dấu vết tối thiểu để chặn lại tệp thành công, không giữ mô tả."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    sha256 = models.CharField(max_length=64)
    batch = models.OneToOneField(CsvImportBatch, null=True, on_delete=models.SET_NULL)
    imported_at = models.DateTimeField(auto_now_add=True)
    transaction_count = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'sha256'], name='csv_import_once_per_user_hash')]


class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField("Tên danh mục", max_length=80)
    canonical_label = models.CharField(
        "Nhãn gợi ý thử nghiệm", max_length=32, blank=True, default='',
        choices=MAPPING_CHOICES,
        help_text="Không bắt buộc. Bạn tự chọn ánh xạ; không suy từ tên. Income chỉ dùng cho thu, các nhãn còn lại cho chi. Transfer luôn cần xem lại và không ánh xạ.",
    )
    kind = models.CharField("Loại", max_length=7, choices=Kind.choices)

    class Meta:
        ordering = ["kind", "name", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["user", "kind", "name"], name="category_unique_per_user_kind"),
            models.CheckConstraint(condition=models.Q(kind__in=Kind.values), name="category_valid_kind"),
        ]

    def __str__(self):
        return f"{self.name} · {self.get_kind_display()}"

    def clean(self):
        if self.canonical_label and compatible_kind(self.canonical_label) != self.kind:
            raise ValidationError({'canonical_label': 'Nhãn gợi ý không phù hợp với loại thu/chi.'})
        super().clean()
        self.name = self.name.strip()
        if self.user_id and self.name:
            duplicates = Category.objects.filter(user_id=self.user_id, kind=self.kind, name__iexact=self.name)
            if self.pk:
                duplicates = duplicates.exclude(pk=self.pk)
            if duplicates.exists():
                raise ValidationError({"name": "Bạn đã có danh mục cùng tên và loại này."})
        if self.pk:
            original = Category.objects.get(pk=self.pk)
            if (original.kind != self.kind or original.user_id != self.user_id) and self.transactions.exists():
                raise ValidationError({"kind": "Danh mục đã có giao dịch. Chỉ được đổi tên, không được đổi loại hoặc chủ sở hữu."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Transaction(models.Model):
    objects = TransactionQuerySet.as_manager()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField("Loại giao dịch", max_length=7, choices=Kind.choices)
    amount = models.DecimalField(
        "Số tiền (VND)", max_digits=15, decimal_places=0,
        validators=[MinValueValidator(Decimal("1"))],
        help_text="Nhập số nguyên đồng, lớn hơn 0, không dùng dấu phân cách. Ví dụ: 150000.",
    )
    date = models.DateField("Ngày giao dịch", default=timezone.localdate)
    category = models.ForeignKey(Category, verbose_name="Danh mục", related_name="transactions", on_delete=models.PROTECT)
    description = models.CharField("Mô tả", max_length=500, blank=True)

    class Meta:
        ordering = ["-date", "-pk"]
        indexes = [models.Index(fields=["user", "date"], name="transaction_user_date")]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="transaction_positive_amount"),
            models.CheckConstraint(condition=models.Q(kind__in=Kind.values), name="transaction_valid_kind"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.amount} VND · {self.date}"

    def clean(self):
        super().clean()
        if self.category_id:
            try:
                category = self.category
            except Category.DoesNotExist:
                raise ValidationError({"category": "Danh mục không tồn tại."})
            if self.user_id and category.user_id != self.user_id:
                raise ValidationError({"category": "Danh mục không thuộc tài khoản của bạn."})
            if category.kind != self.kind:
                raise ValidationError({"category": "Danh mục phải phù hợp với loại thu hoặc chi."})

    def save(self, *args, **kwargs):
        if kwargs.get('update_fields') is not None and not kwargs['update_fields']:
            return super().save(*args, **kwargs)
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            lock_coverage_writes([self.user_id], using)
            previous = type(self).objects.using(using).filter(pk=self.pk).values_list('user_id', 'date').first() if self.pk else None
            self.full_clean()
            result = super().save(*args, **kwargs)
            current = type(self).objects.using(using).filter(pk=self.pk).values_list('user_id', 'date').get()
            reset_months(([previous] if previous else []) + [current], using)
            return result
