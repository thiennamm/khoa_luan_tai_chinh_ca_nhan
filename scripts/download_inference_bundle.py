"""Chỉ tải asset từ repository đã định danh; không log token hoặc URL ký tạm."""
import hashlib
import json
from contextlib import contextmanager
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
from config.configuration_errors import configuration_error, describe_configuration_error
from django.core.exceptions import ImproperlyConfigured

REPOSITORY = 'thiennamm/khoa_luan_tai_chinh_ca_nhan'
ASSET_NAME = 'inference-vi-en-v1.zip'
MAX_BYTES = 32 * 1024 * 1024
EXPECTED_FILES = {'en/model.joblib', 'en/metadata.json', 'vi/model.joblib', 'vi/metadata.json',
                  'vi/artifact-manifest.json', 'requirements.txt', 'bundle-manifest.json'}
CDN_HOSTS = {'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


BUNDLE_MESSAGES = {
    'RELEASE_INPUT_INVALID': 'Kiểm DJANGO_MODEL_RELEASE_TAG và định dạng GITHUB_ARTIFACT_TOKEN.',
    'RELEASE_HTTP': 'Không đọc được release metadata từ GitHub.',
    'RELEASE_METADATA_SIZE': 'Release metadata vượt giới hạn kích thước.',
    'RELEASE_ASSET_SELECTION': 'Cần release đã publish và đúng một asset mang tên đã khóa.',
    'RELEASE_ASSET_STATE': 'Asset chưa uploaded hoặc kích thước không hợp lệ.',
    'ASSET_INPUT_INVALID': 'Asset ID hoặc định dạng token không hợp lệ.',
    'REDIRECT_REJECTED': 'GitHub chuyển hướng không an toàn; không chuyển token hoặc bỏ kiểm tra.',
    'ASSET_HTTP': 'Không tải được private release asset; kiểm quyền đọc/tag/asset.',
    'ASSET_SIZE': 'Asset vượt giới hạn 32 MiB.',
    'REDIRECT_LIMIT': 'Asset chuyển hướng quá nhiều lần.',
    'ARCHIVE_HASH_CONFIG': 'DJANGO_MODEL_BUNDLE_SHA256 cần đúng 64 ký tự hex viết thường.',
    'ARCHIVE_HASH_MISMATCH': 'SHA-256/kích thước ZIP không khớp; chưa giải nén.',
    'BUNDLE_EXISTS': 'Đích đã có gói; cần build sạch, không ghi đè hoặc tái dùng cache cũ.',
    'ZIP_ENTRIES': 'ZIP có tên tệp thiếu/thừa/trùng hoặc bị chuẩn hóa; từ chối giải nén.',
    'ZIP_SIZE': 'Kích thước giải nén vượt giới hạn.',
    'ZIP_PATH': 'Đường dẫn hoặc kiểu tệp ZIP không an toàn.',
    'ZIP_ENTRY_SIZE': 'Một tệp giải nén vượt giới hạn.',
}


class BundleError(Exception):
    def __init__(self, code):
        self.code = code if type(code) is str and code in BUNDLE_MESSAGES else 'BUNDLE_INVALID'
        super().__init__(BUNDLE_MESSAGES.get(self.code, 'Bundle không hợp lệ; không in nội dung lỗi gốc.'))


STAGES = {'django_config', 'artifact_config', 'build_storage', 'release_lookup',
          'asset_download', 'archive_hash', 'zip_extract', 'bundle_verify'}


@contextmanager
def diagnostic_stage(stage):
    try:
        yield
    except Exception as exc:
        current = getattr(exc, '_bundle_stage', None)
        if type(current) is not str or current not in STAGES:
            exc._bundle_stage = stage if stage in STAGES else 'unknown'
        raise


def failure_message(error):
    """Chỉ enum/tên biến allowlist/HTTP status, tuyệt đối không str(exception)."""
    stage = getattr(error, '_bundle_stage', None)
    stage = stage if type(stage) is str and stage in STAGES else 'unknown'
    cause = error
    if isinstance(cause, ImproperlyConfigured):
        code, detail = describe_configuration_error(cause)
    elif isinstance(cause, urllib.error.HTTPError):
        status = cause.code if type(cause.code) is int and 100 <= cause.code <= 599 else None
        code = f'GITHUB_HTTP_{status}' if status else 'GITHUB_HTTP'
        detail = 'GitHub/CDN từ chối yêu cầu; kiểm token, quyền đọc đúng repo, tag/asset và giới hạn API.'
    elif isinstance(cause, (urllib.error.URLError, TimeoutError)):
        code, detail = 'NETWORK_ERROR', 'Lỗi kết nối hoặc timeout tới GitHub/CDN; không in URL hay response body.'
    elif isinstance(cause, BundleError):
        code = cause.code
        detail = BUNDLE_MESSAGES.get(code, 'Bundle không hợp lệ; không in nội dung lỗi gốc.')
    elif isinstance(cause, zipfile.BadZipFile):
        code, detail = 'ZIP_INVALID', 'ZIP không hợp lệ hoặc kiểm CRC thất bại.'
    elif isinstance(cause, (json.JSONDecodeError, UnicodeError, KeyError, TypeError, ValueError)):
        code = 'BUNDLE_VERIFY_FAILED' if stage == 'bundle_verify' else 'METADATA_INVALID'
        detail = ('Kiểm manifest/hash model/requirements thất bại; không bỏ qua kiểm tra.'
                  if stage == 'bundle_verify' else 'Metadata không đúng định dạng/schema; không in nội dung phản hồi.')
    elif isinstance(cause, OSError):
        code, detail = 'BUILD_STORAGE_ERROR', 'Không đọc/ghi được tệp build; kiểm quyền và vùng lưu tạm.'
    else:
        code, detail = 'UNEXPECTED_ERROR', 'Lỗi không dự kiến; không hiển thị exception hoặc traceback có thể chứa bí mật.'
    return f'Không chuẩn bị được inference bundle [{code}; bước={stage}]: {detail} Dừng build.'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def resolve_asset_id(tag, token, opener=None):
    if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', tag)
            or not token or any(c in token for c in '\r\n')):
        raise BundleError('RELEASE_INPUT_INVALID')
    opener = opener or urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(f'https://api.github.com/repos/{REPOSITORY}/releases/tags/{tag}',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'SoThuChi-inference-build'})
    # Không theo redirect metadata và không dùng browser_download_url do response cung cấp.
    with opener.open(request, timeout=30) as response:
        if response.code != 200:
            raise BundleError('RELEASE_HTTP')
        payload = response.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise BundleError('RELEASE_METADATA_SIZE')
    release = json.loads(payload)
    matches = [a for a in release.get('assets', []) if a.get('name') == ASSET_NAME]
    if release.get('draft') is not False or len(matches) != 1:
        raise BundleError('RELEASE_ASSET_SELECTION')
    asset = matches[0]
    if (type(asset.get('id')) is not int or asset['id'] <= 0 or asset.get('state') != 'uploaded'
            or not 0 < asset.get('size', 0) <= MAX_BYTES):
        raise BundleError('RELEASE_ASSET_STATE')
    return str(asset['id'])


def download_asset(asset_id, token, destination, opener=None):
    if not re.fullmatch(r'[1-9][0-9]*', asset_id) or not token or any(c in token for c in '\r\n'):
        raise BundleError('ASSET_INPUT_INVALID')
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
                    raise BundleError('REDIRECT_REJECTED')
                url = location
                # Tuyệt đối không chuyển PAT sang CDN hoặc vào URL.
                headers = {'Accept': 'application/octet-stream', 'User-Agent': 'SoThuChi-inference-build'}
                continue
            if response.code != 200:
                if isinstance(response, urllib.error.HTTPError):
                    # Giữ status để CLI phân biệt 401/403/404; không đọc body.
                    raise response
                raise BundleError('ASSET_HTTP')
            total = 0
            with destination.open('xb') as output:
                while chunk := response.read(64 * 1024):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise BundleError('ASSET_SIZE')
                    output.write(chunk)
            return
        finally:
            response.close()
    raise BundleError('REDIRECT_LIMIT')


def install_archive(archive_path, expected_sha256, output):
    with diagnostic_stage('archive_hash'):
        validate_archive(archive_path, expected_sha256)
    with diagnostic_stage('zip_extract'):
        extract_archive(archive_path, output)


def validate_archive(archive_path, expected_sha256):
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise BundleError('ARCHIVE_HASH_CONFIG')
    if archive_path.stat().st_size > MAX_BYTES or hashlib.sha256(archive_path.read_bytes()).hexdigest() != expected_sha256:
        raise BundleError('ARCHIVE_HASH_MISMATCH')


def extract_archive(archive_path, output):
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise BundleError('BUNDLE_EXISTS')
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
                raise BundleError('ZIP_ENTRIES')
            if sum(e.file_size for e in entries) > MAX_BYTES:
                raise BundleError('ZIP_SIZE')
            for entry in entries:
                name = PurePosixPath(entry.filename)
                mode = entry.external_attr >> 16
                target = temp / entry.filename
                if (name.is_absolute() or '..' in name.parts or '\\' in entry.filename
                        or ':' in entry.filename or entry.is_dir() or entry.flag_bits & 1
                        or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                        or not target.resolve().is_relative_to(temp.resolve())):
                    raise BundleError('ZIP_PATH')
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, target.open('xb') as sink:
                    remaining = MAX_BYTES
                    while chunk := source.read(min(64 * 1024, remaining + 1)):
                        remaining -= len(chunk)
                        if remaining < 0:
                            raise BundleError('ZIP_ENTRY_SIZE')
                        sink.write(chunk)
                target.chmod(0o600)
        # Kiểm hash từng file/model trước khi đưa gói vào đường dẫn loader.
        with diagnostic_stage('bundle_verify'):
            verify(temp)
        temp.rename(output)
        # TemporaryDirectory cleanup không xóa đích đã đổi tên.


def main():
    with diagnostic_stage('django_config'):
        if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render' or os.environ.get('RENDER') != 'true':
            raise configuration_error('RENDER_CONTEXT_INVALID', 'DJANGO_SETTINGS_MODULE', 'RENDER')
        from django.conf import settings
        from config.production_shared import required
        # LazySettings nạp config.render và kiểm DATABASE_URL tại đây, không mở DB.
        output = Path(settings.INFERENCE_ROOT)
    with diagnostic_stage('artifact_config'):
        token = required('GITHUB_ARTIFACT_TOKEN')
        tag = required('DJANGO_MODEL_RELEASE_TAG')
        expected_sha256 = required('DJANGO_MODEL_BUNDLE_SHA256')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', tag) or any(c in token for c in '\r\n'):
            raise BundleError('RELEASE_INPUT_INVALID')
        if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
            raise BundleError('ARCHIVE_HASH_CONFIG')
    with diagnostic_stage('build_storage'):
        if output.exists():
            raise BundleError('BUNDLE_EXISTS')
        output.parent.mkdir(parents=True, exist_ok=True)
    with diagnostic_stage('build_storage'), tempfile.TemporaryDirectory(prefix='bundle-download-', dir=output.parent) as temp:
        path = Path(temp) / 'bundle.zip'
        with diagnostic_stage('release_lookup'):
            asset_id = resolve_asset_id(tag, token)
        with diagnostic_stage('asset_download'):
            download_asset(asset_id, token, path)
        install_archive(path, expected_sha256, output)
    print('Private inference bundle: SHA-256 ZIP và các artifact hợp lệ; đã cài gói tối thiểu.')


def run_cli():
    try:
        main()
    except Exception as exc:
        try:
            message = failure_message(exc)
        except Exception:
            message = 'Không chuẩn bị được inference bundle [DIAGNOSTIC_ERROR]; không in lỗi gốc. Dừng build.'
        print(message, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli())
