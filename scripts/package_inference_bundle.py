"""Đóng ZIP xác định được từ gói đã kiểm; không upload hoặc đọc token."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_inference_bundle import verify


def package(bundle, output):
    bundle, output = bundle.resolve(), output.resolve()
    verify(bundle)
    sidecar = output.with_suffix(output.suffix + '.metadata.json')
    if output.is_relative_to(ROOT) or output.exists() or sidecar.exists():
        raise ValueError('ZIP phải ở ngoài mã nguồn và chưa tồn tại.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream, zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(bundle).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100600 << 16
                archive.writestr(info, path.read_bytes())
    result = {'asset_name': output.name, 'bytes': output.stat().st_size,
              'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'repository': 'thiennamm/khoa_luan_tai_chinh_ca_nhan'}
    with sidecar.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.bundle, args.output), ensure_ascii=False))
