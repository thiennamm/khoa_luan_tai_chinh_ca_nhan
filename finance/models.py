from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Kind(models.TextChoices):
    INCOME = "income", "Thu nhập"
    EXPENSE = "expense", "Chi tiêu"


class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField("Tên danh mục", max_length=80)
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
        self.full_clean()
        return super().save(*args, **kwargs)
