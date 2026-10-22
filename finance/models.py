from decimal import Decimal
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, router, transaction
from django.db.models.functions import Round
from django.utils import timezone
from .classification_labels import MAPPING_CHOICES, compatible_kind
from .coverage_calendar import current_month
from .coverage_state import lock_coverage_writes, reset_months
from .transaction_queries import TransactionQuerySet
from .forecast_state import bump_forecast_version


class Kind(models.TextChoices):
    INCOME = "income", "Thu nhập"
    EXPENSE = "expense", "Chi tiêu"


class ClassificationSuggestion(models.Model):
    """Server-side receipt; no transaction description or model score."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    input_digest = models.CharField(max_length=64)
    kind = models.CharField(max_length=7, choices=Kind.choices)
    mode = models.CharField(max_length=2, choices=[('vi', 'Tiếng Việt'), ('en', 'Tiếng Anh')])
    predicted_label = models.CharField(max_length=32)
    model_name = models.CharField(max_length=64)
    model_sha256 = models.CharField(max_length=64)
    seal = models.CharField(max_length=64)
    source_transaction = models.ForeignKey('Transaction', null=True, blank=True,
        on_delete=models.CASCADE, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True)
    applied_at = models.DateTimeField(null=True)
    applied_category = models.ForeignKey('Category', null=True, on_delete=models.SET_NULL, related_name='+')
    consumed_at = models.DateTimeField(null=True)
    saved_transaction = models.ForeignKey('Transaction', null=True, on_delete=models.CASCADE, related_name='+')


class ClassificationFeedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='classification_feedback')
    suggestion = models.OneToOneField(ClassificationSuggestion, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    mode = models.CharField(max_length=2, choices=[('vi', 'Tiếng Việt'), ('en', 'Tiếng Anh')])
    model_name = models.CharField(max_length=64)
    model_sha256 = models.CharField(max_length=64)
    predicted_label = models.CharField(max_length=32)
    final_category = models.ForeignKey('Category', null=True, on_delete=models.SET_NULL, related_name='+')
    final_category_name = models.CharField(max_length=80)
    final_label = models.CharField(max_length=32)
    applied = models.BooleanField(default=False)
    same_label = models.BooleanField()

    class Meta:
        ordering = ['-created_at', '-pk']
        indexes = [models.Index(fields=['user', '-created_at'], name='feedback_user_created')]


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
            if (original.kind != self.kind or original.user_id != self.user_id) and self.recurring_rules.exists():
                raise ValidationError({'kind': 'Danh mục đang dùng cho giao dịch định kỳ. Hãy chuyển danh mục của quy tắc trước khi đổi loại hoặc chủ sở hữu.'})
            if (original.kind != self.kind or original.user_id != self.user_id) and self.budgets.exists():
                raise ValidationError({'kind': 'Danh mục đang có ngân sách. Hãy xóa hoặc chuyển ngân sách trước khi đổi loại hoặc chủ sở hữu.'})
            if (original.kind != self.kind or original.user_id != self.user_id) and self.transactions.exists():
                raise ValidationError({"kind": "Danh mục đã có giao dịch. Chỉ được đổi tên, không được đổi loại hoặc chủ sở hữu."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    month = models.DateField('Tháng')
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT,
        related_name='budgets', verbose_name='Danh mục chi',
        help_text='Để trống để đặt ngân sách tổng. Ngân sách tổng và danh mục là hai mức theo dõi riêng.')
    amount = models.DecimalField('Hạn mức (VND)', max_digits=15, decimal_places=0,
        validators=[MinValueValidator(Decimal('1'))])

    class Meta:
        ordering = ['month', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['user', 'month'], condition=models.Q(category__isnull=True),
                name='budget_unique_total_month', violation_error_message='Tháng này đã có ngân sách tổng.'),
            models.UniqueConstraint(fields=['user', 'month', 'category'], condition=models.Q(category__isnull=False),
                name='budget_unique_category_month', violation_error_message='Danh mục này đã có ngân sách trong tháng.'),
            models.CheckConstraint(condition=models.Q(month__day=1), name='budget_month_first_day'),
            models.CheckConstraint(condition=models.Q(amount__gt=0, amount__lte=999999999999999)
                & models.Q(amount=Round('amount', precision=0)), name='budget_positive_integer_vnd'),
        ]

    def __str__(self):
        scope = self.category.name if self.category_id else 'Ngân sách tổng'
        return f'{scope} · {self.month:%m/%Y}'

    def clean(self):
        super().clean()
        if self.month and self.month.day != 1:
            raise ValidationError({'month': 'Tháng phải là ngày đầu tháng.'})
        if self.category_id:
            try:
                category = self.category
            except Category.DoesNotExist:
                raise ValidationError({'category': 'Danh mục không hợp lệ.'})
            if category.user_id != self.user_id or category.kind != Kind.EXPENSE:
                raise ValidationError({'category': 'Chỉ chọn danh mục chi của chính bạn.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class RecurringRule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField('Tên khoản', max_length=80)
    kind = models.CharField('Loại', max_length=7, choices=Kind.choices)
    amount = models.DecimalField('Số tiền dự kiến (VND)', max_digits=15, decimal_places=0,
        validators=[MinValueValidator(Decimal('1'))])
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='recurring_rules', verbose_name='Danh mục')
    due_day = models.PositiveSmallIntegerField('Ngày đến hạn')
    start_month = models.DateField('Tháng bắt đầu')
    end_month = models.DateField('Tháng kết thúc', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(kind__in=Kind.values), name='recurring_rule_kind'),
            models.CheckConstraint(condition=models.Q(due_day__gte=1, due_day__lte=31), name='recurring_rule_day'),
            models.CheckConstraint(condition=models.Q(amount__gt=0, amount__lte=999999999999999)
                & models.Q(amount=Round('amount', precision=0)), name='recurring_rule_integer_vnd'),
            models.CheckConstraint(condition=models.Q(start_month__day=1), name='recurring_rule_start'),
            models.CheckConstraint(condition=models.Q(end_month__isnull=True)
                | (models.Q(end_month__day=1) & models.Q(end_month__gte=models.F('start_month'))), name='recurring_rule_end'),
        ]

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        errors = {}
        if not self.name:
            errors['name'] = 'Nhập tên khoản.'
        if self.due_day is not None and not 1 <= self.due_day <= 31:
            errors['due_day'] = 'Ngày đến hạn từ 1 đến 31.'
        if self.start_month and self.start_month.day != 1:
            errors['start_month'] = 'Chọn tháng hợp lệ.'
        if self.end_month and (self.end_month.day != 1 or (self.start_month and self.end_month < self.start_month)):
            errors['end_month'] = 'Tháng kết thúc không được trước tháng bắt đầu.'
        if self.category_id and (self.category.user_id != self.user_id or self.category.kind != self.kind):
            errors['category'] = 'Chọn danh mục của bạn, đúng loại thu/chi.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class RecurringRevision(models.Model):
    rule = models.ForeignKey(RecurringRule, on_delete=models.CASCADE, related_name='revisions')
    effective_month = models.DateField()
    active = models.BooleanField()
    snapshot = models.JSONField()

    class Meta:
        ordering = ['effective_month', 'pk']
        constraints = [models.UniqueConstraint(fields=['rule', 'effective_month'], name='recurring_revision_month'),
            models.CheckConstraint(condition=models.Q(effective_month__day=1), name='recurring_revision_first_day')]


class RecurringOccurrence(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Chưa xử lý'
        RECORDED = 'recorded', 'Đã ghi nhận'
        SKIPPED = 'skipped', 'Đã bỏ qua'
        DELETED = 'deleted', 'Giao dịch đã xóa — cần mở lại'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rule = models.ForeignKey(RecurringRule, on_delete=models.CASCADE, related_name='occurrences')
    month = models.DateField()
    due_date = models.DateField()
    snapshot = models.JSONField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    transaction = models.OneToOneField('Transaction', null=True, on_delete=models.SET_NULL, related_name='recurring_occurrence')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['rule', 'month'], name='recurring_occurrence_once'),
            models.CheckConstraint(condition=models.Q(month__day=1), name='recurring_occurrence_first_day'),
            models.CheckConstraint(condition=(models.Q(status='recorded', transaction__isnull=False)
                | models.Q(status__in=['open', 'skipped', 'deleted'], transaction__isnull=True)), name='recurring_occurrence_state')]


class RecurringEvent(models.Model):
    occurrence = models.ForeignKey(RecurringOccurrence, on_delete=models.CASCADE, related_name='events')
    action = models.CharField(max_length=12, choices=[('record', 'Ghi nhận'), ('skip', 'Bỏ qua'),
        ('reopen', 'Mở lại'), ('delete', 'Giao dịch bị xóa')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']


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
