"""Suy luận cục bộ, chỉ đọc artifact được xác minh trước khi giải tuần tự.

Không huấn luyện, ghi mô tả hoặc dùng launcher/patch DLL của thí nghiệm.
"""
import hashlib
import io
import json
import logging
import re
import threading
import unicodedata
from pathlib import Path

from django.conf import settings

from .classification_labels import LABELS

logger = logging.getLogger(__name__)
PREFIX = re.compile(r'^\s*\[(debit|credit)\]\s*', re.I)
CANDIDATE = 'char_linearsvc_C_10p0'
# Khóa đúng artifact đã đánh giá, kể cả nếu metadata vô tình bị thay đổi.
EXPECTED_SHA256 = '362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345'
_cache = None
_lock = threading.Lock()


class ModelUnavailable(Exception):
    pass


def normalize_description(text):
    """Giống body() của audit 06A/06B: bỏ một tiền tố đầu, NFC, casefold, split."""
    return ' '.join(unicodedata.normalize('NFC', PREFIX.sub('', text, count=1)).casefold().split())


def load_model():
    global _cache
    # Chỉ settings phía máy chủ cung cấp đường dẫn; không lấy từ request.
    path = Path(settings.CLASSIFICATION_MODEL_PATH)
    metadata = json.loads(Path(settings.CLASSIFICATION_METADATA_PATH).read_text(encoding='utf-8'))
    if (metadata['selected_candidate_id'] != CANDIDATE
            or metadata['selection']['selected_candidate_id'] != CANDIDATE
            or metadata['selection']['selected_model_sha256'] != EXPECTED_SHA256
            or metadata['models'][CANDIDATE]['model_sha256'] != EXPECTED_SHA256):
        raise ModelUnavailable('Metadata không khớp artifact được chọn.')
    payload = path.read_bytes()
    sha = hashlib.sha256(payload).hexdigest()
    if sha != EXPECTED_SHA256:
        raise ModelUnavailable('SHA-256 mô hình không khớp metadata.')
    # Hash lại mỗi lần gọi, rồi tải chính các byte đã kiểm tra (không mở lại tệp).
    with _lock:
        if _cache is not None and _cache[0] == sha:
            return _cache[1]
        import joblib
        from sklearn.pipeline import Pipeline
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.svm import LinearSVC

        model = joblib.load(io.BytesIO(payload))
        if not isinstance(model, Pipeline) or list(model.named_steps) != ['tfidf', 'classifier']:
            raise ModelUnavailable('Pipeline không đúng cấu trúc.')
        vectorizer, classifier = model.named_steps.values()
        if (not isinstance(vectorizer, TfidfVectorizer)
                or vectorizer.analyzer != 'char_wb' or vectorizer.ngram_range != (3, 5)
                or vectorizer.lowercase is not False
                or not isinstance(classifier, LinearSVC) or classifier.C != 10
                or set(classifier.classes_) != set(LABELS)):
            raise ModelUnavailable('Pipeline không đúng cấu hình được chọn.')
        _cache = (sha, model)
        return model


def suggest_label(description):
    text = normalize_description(description)
    if not text:
        return None
    try:
        model = load_model()
        if model.named_steps['tfidf'].transform([text]).nnz == 0:
            return None
        label = str(model.predict([text])[0])
        if label not in LABELS:
            raise ModelUnavailable('Nhãn không thuộc bộ nhãn đã đánh giá.')
        return label
    except Exception as exc:
        # Không ghi mô tả, dữ liệu giao dịch, đường dẫn hoặc nội dung exception vào log.
        logger.warning('Classification unavailable (%s)', type(exc).__name__)
        raise ModelUnavailable('Gợi ý tạm không sẵn sàng.') from None
