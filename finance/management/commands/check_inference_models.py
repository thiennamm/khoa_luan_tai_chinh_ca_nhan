"""Preflight CLI: chỉ tải hai pipeline đã khóa, không huấn luyện."""
import importlib.metadata
import sys
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from finance.classification import load_model
from finance.classification_modes import load_vietnamese_model
from scripts.build_inference_bundle import verify


class Command(BaseCommand):
    help = 'Kiểm gói suy luận production, phiên bản thư viện và tải cả EN/VI.'

    def handle(self, *args, **options):
        try:
            root = Path(settings.INFERENCE_ROOT)
            verify(root)
            if sys.version_info[:2] != (3, 13):
                raise ValueError('Cần Python nhánh 3.13 đã dùng cho artifact.')
            for line in (root / 'requirements.txt').read_text(encoding='utf-8-sig').splitlines():
                if line.strip() and not line.startswith('#'):
                    name, version = line.split('==')
                    if importlib.metadata.version(name) != version:
                        raise ValueError(f'Phiên bản thư viện không khớp: {name}')
            expected = {
                'CLASSIFICATION_MODEL_PATH': 'en/model.joblib',
                'CLASSIFICATION_METADATA_PATH': 'en/metadata.json',
                'VI_CLASSIFICATION_MODEL_PATH': 'vi/model.joblib',
                'VI_CLASSIFICATION_METADATA_PATH': 'vi/metadata.json',
                'VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH': 'vi/artifact-manifest.json',
            }
            if any(Path(getattr(settings, key)).resolve() != (root / name).resolve()
                   for key, name in expected.items()):
                raise ValueError('Đường dẫn suy luận nằm ngoài gói đã kiểm.')
            load_model()
            load_vietnamese_model()
        except Exception as exc:
            # Không in giá trị cấu hình hoặc nội dung exception từ thư viện.
            raise CommandError(f'Preflight mô hình thất bại ({type(exc).__name__}); kiểm cấu hình/hash/runtime.') from None
        self.stdout.write(self.style.SUCCESS('EN và VI: đúng hash, runtime và tải Pipeline thành công; không fit.'))
