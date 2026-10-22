from django.core.management.base import BaseCommand
from django.utils import timezone
from finance.models import ClassificationSuggestion


class Command(BaseCommand):
    help = 'Xóa gợi ý hết hạn chưa dùng; giữ gợi ý đã dùng cùng phản hồi lịch sử.'

    def handle(self, *args, **options):
        count, _ = ClassificationSuggestion.objects.filter(
            consumed_at__isnull=True, expires_at__lte=timezone.now()).delete()
        self.stdout.write(self.style.SUCCESS(f'Đã dọn {count} gợi ý hết hạn chưa dùng.'))
