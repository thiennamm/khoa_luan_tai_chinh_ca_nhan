from django.core.management.base import BaseCommand
from finance.csv_import import cleanup_batches


class Command(BaseCommand):
    help = 'Xóa payload/lô CSV hết hạn; giữ dấu vết hash thành công để chặn nhập lại.'

    def handle(self, *args, **options):
        count = cleanup_batches()
        self.stdout.write(self.style.SUCCESS(f'Đã dọn {count} lô CSV hết hạn. Không xóa giao dịch hoặc dấu vết hash thành công.'))
