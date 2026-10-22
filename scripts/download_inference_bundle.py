"""Chỉ tải asset từ repository đã định danh; không log token hoặc URL ký tạm."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_inference_bundle import verify

REPOSITORY = 'thiennamm/khoa_luan_tai_chinh_ca_nhan'
ASSET_NAME = 'inference-vi-en-v1.zip'
MAX_BYTES = 32 * 1024 * 1024
EXPECTED_FILES = {'en/model.joblib', 'en/metadata.json', 'vi/model.joblib', 'vi/metadata.json',
                  'vi/artifact-manifest.json', 'requirements.txt', 'bundle-manifest.json'}
CDN_HOSTS = {'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


class BundleError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def resolve_asset_id(tag, token, opener=None):
    if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', tag)
            or not token or any(c in token for c in '\r\n')):
        raise BundleError('Release tag hoặc token không hợp lệ.')
    opener = opener or urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(f'https://api.github.com/repos/{REPOSITORY}/releases/tags/{tag}',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'SoThuChi-inference-build'})
    # Không theo redirect metadata và không dùng browser_download_url do response cung cấp.
    with opener.open(request, timeout=30) as response:
        if response.code != 200:
            raise BundleError('Không đọc được release metadata.')
        payload = response.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise BundleError('Release metadata vượt giới hạn.')
    release = json.loads(payload)
    matches = [a for a in release.get('assets', []) if a.get('name') == ASSET_NAME]
    if release.get('draft') is not False or len(matches) != 1:
        raise BundleError('Cần release đã publish và đúng một asset có tên đã khóa.')
    asset = matches[0]
    if (type(asset.get('id')) is not int or asset['id'] <= 0 or asset.get('state') != 'uploaded'
            or not 0 < asset.get('size', 0) <= MAX_BYTES):
        raise BundleError('Asset chưa sẵn sàng hoặc kích thước không hợp lệ.')
    return str(asset['id'])


def download_asset(asset_id, token, destination, opener=None):
    if not re.fullmatch(r'[1-9][0-9]*', asset_id) or not token or any(c in token for c in '\r\n'):
        raise BundleError('Asset ID hoặc cấu hình token không hợp lệ.')
    opener = opener or urllib.request.build_opener(NoRedirect)
    url = f'https://api.github.com/repos/{REPOSITORY}/releases/assets/{asset_id}'
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/octet-stream',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'SoThuChi-inference-build'}
    for _ in range(4):
        try:
            response = opener.open(urllib.request.Request(url, headers=headers), timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            if response.code in (301, 302, 303, 307, 308):
                location = response.headers.get('Location', '')
                try:
                    target = urllib.parse.urlsplit(location)
                    allowed = (target.scheme == 'https' and target.hostname in CDN_HOSTS
                               and target.port in (None, 443) and not target.username and not target.password)
                except ValueError:
                    allowed = False
                if not allowed or token in location:
                    raise BundleError('GitHub chuyển hướng đến host không được phép.')
                url = location
                # Tuyệt đối không chuyển PAT sang CDN hoặc vào URL.
                headers = {'Accept': 'application/octet-stream', 'User-Agent': 'SoThuChi-inference-build'}
                continue
            if response.code != 200:
                raise BundleError('Không tải được private release asset; kiểm quyền/asset ID.')
            total = 0
            with destination.open('xb') as output:
                while chunk := response.read(64 * 1024):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise BundleError('Asset vượt giới hạn 32 MiB.')
                    output.write(chunk)
            return
        finally:
            response.close()
    raise BundleError('Asset chuyển hướng quá nhiều lần.')


def install_archive(archive_path, expected_sha256, output):
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise BundleError('Thiếu SHA-256 bundle hợp lệ đã khóa từ máy chuẩn bị.')
    if archive_path.stat().st_size > MAX_BYTES or hashlib.sha256(archive_path.read_bytes()).hexdigest() != expected_sha256:
        raise BundleError('SHA-256/kích thước ZIP không khớp; chưa giải nén.')
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise BundleError('Thư mục cài gói đã tồn tại; không ghi đè.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bundle-extract-', dir=output.parent) as temp:
        temp = Path(temp)
        with zipfile.ZipFile(archive_path) as archive:
            entries = archive.infolist()
            # ZipInfo có thể chuẩn hóa dấu phân cách/NUL trên Windows. Kiểm tên
            # nguyên gốc trong archive để chính sách không đổi giữa Windows/Linux.
            if (len(entries) != len(EXPECTED_FILES)
                    or {e.orig_filename for e in entries} != EXPECTED_FILES
                    or any(e.filename != e.orig_filename for e in entries)):
                raise BundleError('ZIP có tệp thiếu/thừa/trùng; từ chối giải nén.')
            if sum(e.file_size for e in entries) > MAX_BYTES:
                raise BundleError('Kích thước giải nén vượt giới hạn.')
            for entry in entries:
                name = PurePosixPath(entry.filename)
                mode = entry.external_attr >> 16
                target = temp / entry.filename
                if (name.is_absolute() or '..' in name.parts or '\\' in entry.filename
                        or ':' in entry.filename or entry.is_dir() or entry.flag_bits & 1
                        or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                        or not target.resolve().is_relative_to(temp.resolve())):
                    raise BundleError('Đường dẫn hoặc kiểu tệp ZIP không an toàn.')
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, target.open('xb') as sink:
                    remaining = MAX_BYTES
                    while chunk := source.read(min(64 * 1024, remaining + 1)):
                        remaining -= len(chunk)
                        if remaining < 0:
                            raise BundleError('Tệp giải nén vượt giới hạn.')
                        sink.write(chunk)
                target.chmod(0o600)
        # Kiểm hash từng file/model trước khi đưa gói vào đường dẫn loader.
        verify(temp)
        temp.rename(output)
        # TemporaryDirectory cleanup không xóa đích đã đổi tên.


def main():
    if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render' or os.environ.get('RENDER') != 'true':
        raise BundleError('Chỉ tải bundle trong build Render đã cấu hình.')
    from django.conf import settings
    from config.production_shared import required
    output = Path(settings.INFERENCE_ROOT)
    if output.exists():
        raise BundleError('Đã có gói tại đích; cần build sạch, không dùng cache model cũ.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bundle-download-', dir=output.parent) as temp:
        path = Path(temp) / 'bundle.zip'
        token = required('GITHUB_ARTIFACT_TOKEN')
        asset_id = resolve_asset_id(required('DJANGO_MODEL_RELEASE_TAG'), token)
        download_asset(asset_id, token, path)
        install_archive(path, required('DJANGO_MODEL_BUNDLE_SHA256'), output)
    print('Private inference bundle: SHA-256 ZIP và các artifact hợp lệ; đã cài gói tối thiểu.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Không traceback exception mạng: có thể chứa URL ký tạm hoặc header nhạy cảm.
        print(f'Không chuẩn bị được inference bundle ({type(exc).__name__}); dừng build.', file=sys.stderr)
        raise SystemExit(1) from None
