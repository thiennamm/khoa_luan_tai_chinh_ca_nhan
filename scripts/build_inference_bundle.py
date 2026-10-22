"""Tạo gói suy luận tối thiểu mới; không fit hoặc thay artifact gốc."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finance.classification import CANDIDATE, EXPECTED_SHA256
from finance.classification_modes import VI_CANDIDATE, VI_SHA256


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build(output):
    output = output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError('Gói mô hình cần nằm ngoài thư mục mã dự án.')
    if output.exists():
        raise ValueError('Thư mục đích phải chưa tồn tại; không ghi đè gói cũ.')
    en_meta_path = ROOT / 'docs/metadata/classification-experiment-results.json'
    vi_meta_path = ROOT / 'docs/metadata/vietnamese-classification-experiment-results.json'
    vi_manifest_path = ROOT / 'data/experiments/classification-vietnamese/task10b-vi-v1/artifact-manifest.json'
    en = json.loads(en_meta_path.read_text(encoding='utf-8'))
    vi = json.loads(vi_meta_path.read_text(encoding='utf-8'))
    vi_manifest = json.loads(vi_manifest_path.read_text(encoding='utf-8'))
    en_model = ROOT / f'data/experiments/classification/task06b-v1-final/models/{CANDIDATE}.joblib'
    vi_model = ROOT / f'data/experiments/classification-vietnamese/task10b-vi-v1/models/{VI_CANDIDATE}.joblib'
    if not (en['selected_candidate_id'] == en['selection']['selected_candidate_id'] == CANDIDATE
            and en['selection']['selected_model_sha256'] == en['models'][CANDIDATE]['model_sha256']
            == digest(en_model) == EXPECTED_SHA256):
        raise ValueError('Artifact/metadata EN không khớp phiên bản đã khóa.')
    entry = vi_manifest['files'][f'models/{VI_CANDIDATE}.joblib']
    if not (vi['selected_id'] == VI_CANDIDATE and vi_manifest['experiment'] == 'task10b-vi-v1'
            and vi['models'][VI_CANDIDATE]['model_sha256'] == entry['sha256'] == digest(vi_model) == VI_SHA256
            and entry['bytes'] == vi_model.stat().st_size):
        raise ValueError('Artifact/metadata VI không khớp phiên bản đã khóa.')
    output.mkdir(parents=True)
    write_json(output / 'en/metadata.json', {
        'selected_candidate_id': CANDIDATE,
        'selection': {'selected_candidate_id': CANDIDATE, 'selected_model_sha256': EXPECTED_SHA256},
        'models': {CANDIDATE: {'model_sha256': EXPECTED_SHA256}},
    })
    write_json(output / 'vi/metadata.json', {
        'selected_id': VI_CANDIDATE, 'models': {VI_CANDIDATE: {'model_sha256': VI_SHA256}},
    })
    write_json(output / 'vi/artifact-manifest.json', {
        'experiment': 'task10b-vi-v1',
        'files': {f'models/{VI_CANDIDATE}.joblib': {'sha256': VI_SHA256, 'bytes': vi_model.stat().st_size}},
    })
    shutil.copyfile(en_model, output / 'en/model.joblib')
    shutil.copyfile(vi_model, output / 'vi/model.joblib')
    shutil.copyfile(ROOT / 'requirements.txt', output / 'requirements.txt')
    files = {p.relative_to(output).as_posix(): {'bytes': p.stat().st_size, 'sha256': digest(p)}
             for p in sorted(output.rglob('*')) if p.is_file()}
    write_json(output / 'bundle-manifest.json', {
        'schema': 'inference-bundle-v1', 'files': files,
        'source_metadata_sha256': {p.relative_to(ROOT).as_posix(): digest(p)
                                   for p in [en_meta_path, vi_meta_path, vi_manifest_path]},
        'runtime': {'python_branch': '3.13', 'requirements_sha256': digest(ROOT / 'requirements.txt')},
    })
    verify(output)
    return files


def verify(output):
    output = output.resolve()
    manifest = json.loads((output / 'bundle-manifest.json').read_text(encoding='utf-8'))
    expected = {'en/model.joblib', 'en/metadata.json', 'vi/model.joblib', 'vi/metadata.json',
                'vi/artifact-manifest.json', 'requirements.txt'}
    actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
    if (manifest['schema'] != 'inference-bundle-v1' or set(manifest['files']) != expected
            or actual != expected | {'bundle-manifest.json'}):
        raise ValueError('Gói chứa thiếu/thừa tệp ngoài danh sách suy luận tối thiểu.')
    for name, entry in manifest['files'].items():
        path = output / name
        if path.is_symlink() or not path.resolve().is_relative_to(output):
            raise ValueError('Không chấp nhận symlink/path ra ngoài gói.')
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError(f'Hash/kích thước không khớp: {name}')
    if digest(output / 'en/model.joblib') != EXPECTED_SHA256 or digest(output / 'vi/model.joblib') != VI_SHA256:
        raise ValueError('Hash artifact không khớp mã tích hợp.')
    def pins(path):
        return [line.strip() for line in path.read_text(encoding='utf-8-sig').splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
    if pins(output / 'requirements.txt') != pins(ROOT / 'requirements.txt'):
        raise ValueError('Requirements của gói khác mã đang triển khai.')
    if (manifest['runtime']['python_branch'] != '3.13'
            or manifest['runtime']['requirements_sha256'] != digest(output / 'requirements.txt')):
        raise ValueError('Metadata runtime không khớp requirements của gói.')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if args.verify_only:
        verify(args.output)
    else:
        build(args.output)
    print('Gói suy luận tối thiểu: hash và danh sách tệp hợp lệ.')
