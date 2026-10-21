"""Định tuyến tường minh; không huấn luyện hoặc tự đổi ngôn ngữ khi lỗi."""
import hashlib
import io
import json
import logging
import threading
from pathlib import Path

from django.conf import settings

from . import classification as english
from .classification import ModelUnavailable, normalize_description
from .classification_labels import LABELS

MODES = [('vi', 'Tiếng Việt — thử nghiệm'), ('en', 'Tiếng Anh — thử nghiệm')]
VI_CANDIDATE = 'char_linearsvc_C_10'
VI_SHA256 = '19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55'
_cache = None
_lock = threading.Lock()
logger = logging.getLogger(__name__)


def load_vietnamese_model():
    global _cache
    metadata = json.loads(Path(settings.VI_CLASSIFICATION_METADATA_PATH).read_text(encoding='utf-8'))
    manifest = json.loads(Path(settings.VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH).read_text(encoding='utf-8'))
    entry = manifest['files'][f'models/{VI_CANDIDATE}.joblib']
    if (metadata['selected_id'] != VI_CANDIDATE
            or metadata['models'][VI_CANDIDATE]['model_sha256'] != VI_SHA256
            or manifest['experiment'] != 'task10b-vi-v1'
            or entry['sha256'] != VI_SHA256):
        raise ModelUnavailable('Metadata không khớp artifact tiếng Việt đã chọn.')
    payload = Path(settings.VI_CLASSIFICATION_MODEL_PATH).read_bytes()
    sha = hashlib.sha256(payload).hexdigest()
    if sha != VI_SHA256 or len(payload) != entry['bytes']:
        raise ModelUnavailable('Artifact tiếng Việt không khớp SHA-256.')
    # Kiểm lại metadata/hash cả khi cache tồn tại; tải đúng byte đã kiểm tra.
    with _lock:
        if _cache is not None and _cache[0] == sha:
            return _cache[1]
        import joblib
        from sklearn.pipeline import Pipeline
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.svm import LinearSVC

        model = joblib.load(io.BytesIO(payload))
        if not isinstance(model, Pipeline) or list(model.named_steps) != ['tfidf', 'classifier']:
            raise ModelUnavailable('Pipeline tiếng Việt không đúng cấu trúc.')
        vectorizer, classifier = model.named_steps.values()
        if (not isinstance(vectorizer, TfidfVectorizer)
                or vectorizer.analyzer != 'char_wb' or vectorizer.ngram_range != (3, 5)
                or vectorizer.lowercase is not False or vectorizer.strip_accents is not None
                or vectorizer.min_df != 1 or vectorizer.sublinear_tf is not True
                or not isinstance(classifier, LinearSVC) or classifier.C != 10
                or set(classifier.classes_) != set(LABELS)):
            raise ModelUnavailable('Pipeline tiếng Việt không đúng cấu hình.')
        _cache = (sha, model)
        return model


def suggest_label(description, *, mode):
    if mode == 'en':
        return english.suggest_label(description)
    if mode != 'vi':
        raise ModelUnavailable('Chế độ gợi ý không hợp lệ.')
    text = normalize_description(description)
    if not text:
        return None
    try:
        model = load_vietnamese_model()
        if model.named_steps['tfidf'].transform([text]).nnz == 0:
            return None
        label = str(model.predict([text])[0])
        if label not in LABELS:
            raise ModelUnavailable('Nhãn không hợp lệ.')
        return label
    except Exception as exc:
        logger.warning('Vietnamese classification unavailable (%s)', type(exc).__name__)
        raise ModelUnavailable('Không có gợi ý: mô hình tiếng Việt tạm không sẵn sàng.') from None
