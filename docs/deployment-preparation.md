# TASK 13C — Chuẩn bị triển khai Django

> Bổ sung TASK 14A: cấu hình dành riêng Render Free/PostgreSQL nằm ở [render-deployment.md](render-deployment.md). Profile `config.production` trong tài liệu lịch sử này vẫn dành cho SQLite; không dùng nó trên Render Free. Đã thêm nhánh migration PostgreSQL, nhưng chưa kiểm trên PostgreSQL thật.

Ngày kiểm tra: 22/10/2026. Thực hiện trên **dự án chính** `D:\KHÓA LUẬN TỐT NGHIỆP`; không dùng bản phục hồi cổng 8003. Chưa deploy, chưa tạo dịch vụ, chưa chuyển dữ liệu thật. Đây là cấu hình và kiểm thử chuẩn bị, chưa xác nhận một hosting cụ thể đủ điều kiện vận hành.

## 1. Cấu hình local và production

| Tệp | Vai trò |
|---|---|
| `config/base.py` | Apps, templates, múi giờ, validators và cấu hình dùng chung; không đọc/tạo secret hay mở DB |
| `config/local.py` | Giữ hành vi local: SQLite trong dự án, khóa riêng ở `secrets/` hoặc env, DEBUG mặc định bật |
| `config/settings.py` | Tên tương thích cũ, import local; hướng dẫn local vẫn dùng được |
| `config/production.py` | Cấu hình độc lập, không import local; thiếu cấu hình bắt buộc thì dừng |
| `config/production_wsgi.py` | Entrypoint riêng; từ chối nếu settings được chỉ định là local |
| `.env.example` | Chỉ placeholder; không phải tệp secret hoạt động |

**Django không tự đọc `.env`.** Hosting hoặc trình quản lý tiến trình phải cấp biến môi trường. Không đưa `.env`, secret hoặc file môi trường QA lên Git. Không sao chép khóa local làm khóa production. Các lệnh production cần môi trường `DJANGO_SETTINGS_MODULE=config.production`; riêng entrypoint production cũng kiểm tra điều này.

| Biến bắt buộc | Quy tắc |
|---|---|
| `DJANGO_SECRET_KEY` | Khóa production riêng, ngẫu nhiên mạnh; kiểm tối thiểu 50 ký tự, không tiền tố `django-insecure-` |
| `DJANGO_ALLOWED_HOSTS` | Danh sách host cụ thể cách nhau dấu phẩy; không scheme, port, wildcard |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Danh sách HTTPS origin thuộc các host trên, có thể gồm port; không path/query/wildcard |
| `DJANGO_DATABASE_ENGINE` | Hiện chỉ nhận `sqlite`; không giả vờ hỗ trợ engine khác |
| `DJANGO_DATABASE_PATH` | Đường dẫn tuyệt đối ngoài mã nguồn, thư mục cha đã tồn tại, nằm trên storage riêng tư bền vững |
| `DJANGO_DATABASE_STORAGE` | `persistent`, chỉ khai báo sau khi kiểm điều kiện storage hosting thực tế |
| `DJANGO_STATIC_ROOT` | Đường dẫn tuyệt đối ngoài mã, tách khỏi DB và mô hình; chỉ chứa static công khai |
| `DJANGO_INFERENCE_DIR` | Thư mục gói suy luận riêng tư, tuyệt đối, ngoài mã và ngoài static |

Đường dẫn được cấu hình theo máy triển khai, không ghép ổ `D:` trong cấu hình production. Không có fallback sang DB phát triển, secret local hoặc model trong `data/`. Giá trị placeholder/thiếu bị từ chối. `DJANGO_DEBUG=1` không thể bật DEBUG production.

Production đặt DEBUG=False, cookie session/CSRF Secure, chuyển HTTP sang HTTPS, HSTS 3.600 giây, nosniff, frame DENY và referrer same-origin. Host/origin phải điền đúng tên miền khi đã chọn hosting. Tham khảo [deployment checklist Django 5.2](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

## 2. Database và storage: điều kiện còn phải đáp ứng

**Nhánh này chuẩn bị cho SQLite trên một máy/instance có vùng lưu bền vững.** Migration `finance.0008_budget_category_guards` dùng trigger SQLite; chưa có migration PostgreSQL tương đương. Chưa thể chỉ đổi biến môi trường để dùng PostgreSQL. Không chuyển database trong task này.

`DJANGO_DATABASE_STORAGE=persistent` là lời khai của người cấu hình, **không chứng minh** hosting giữ tệp sau restart/redeploy. Trước triển khai phải kiểm mount/volume thực tế, quyền đọc/ghi, backup/restore và hành vi restart. Không dùng thư mục release tạm, filesystem ephemeral hoặc filesystem mạng không bảo đảm khóa SQLite. Không đặt nhiều replica cùng ghi SQLite. Cần xem lại kiến trúc DB nếu hosting không đáp ứng các điều kiện này.

| Nội dung | Nơi lưu hiện tại | Yêu cầu khi vận hành |
|---|---|---|
| Tài khoản, mật khẩu đã băm, phiên, danh mục, giao dịch | SQLite | Bền vững, riêng tư, sao lưu bằng SQLite backup API |
| Coverage, ngân sách, phiên bản dữ liệu, dự báo cá nhân | SQLite | Chung DB; không để mất sau restart |
| CSV preview | `CsvImportBatch.raw`/bindings trong SQLite | Payload ở máy chủ, TTL 30 phút; cần DB bền vững để tiếp tục xác nhận sau restart |
| Dấu vết đã nhập CSV | `CsvImportReceipt` trong SQLite | Giữ để chặn nhập lại theo tài khoản/hash, kể cả sau khi dọn preview |
| Tệp upload tạm | RAM hoặc thư mục tạm của hệ điều hành qua upload handlers | Thư mục riêng tư, không đưa vào static; có cơ chế dọn tệp tạm của hệ thống |
| Hai model + metadata | Gói suy luận được mount/copy riêng | Giữ đúng hash, chỉ đọc với tiến trình web; release/restart phải cung cấp lại được |
| Static sau collectstatic | `STATIC_ROOT` | Có thể dựng lại; chỉ công khai thư mục này |
| Cache model / demo | RAM của từng process | Mất khi restart; nhiều process không chia sẻ cache; người dùng bấm tính lại demo |
| Cache Django mặc định | LocMemCache, không giữ dữ liệu tài chính làm nguồn chính | Không coi là storage bền vững hoặc cache chung nhiều worker |

Upload CSV vẫn giới hạn 2 MiB/5.000 dòng. Giới hạn request body Waitress và mẫu Nginx là 3 MiB để chừa multipart overhead; giới hạn nghiệp vụ 2 MiB vẫn do ứng dụng kiểm tra. Không thay quy tắc import hoặc forecast.

Hiện cleanup tự động khi tải CSV chỉ dọn lô hết hạn của tài khoản đang thao tác. Cần đặt job của hosting, ví dụ mỗi 10–15 phút, chạy bằng **cùng môi trường production**:

```powershell
python -X utf8 manage.py cleanup_csv_imports --settings=config.production
```

Lệnh xóa lô hết hạn/payload; không xóa giao dịch hay receipt. Task này kiểm lệnh trên DB QA, chưa tạo scheduler. Không ghi body CSV, mô tả giao dịch, cookie hoặc secret vào log. Mẫu Nginx tắt access log để không ghi query tìm kiếm; cần thiết kế logging vận hành phù hợp riêng, không coi đó là đã hoàn tất giám sát.

## 3. Runtime, WSGI và static

Giữ nguyên `requirements.txt` với 14 phiên bản đã khóa, gồm Django 5.2.18, numpy 2.5.4, scipy 1.18.1, pandas 3.0.6, scikit-learn 1.9.1, joblib 1.6.0. Tệp **`requirements-production.txt`** tham chiếu tệp cũ và thêm duy nhất `waitress==3.0.2`. Môi trường local gốc không cài thêm gói.

Chọn WSGI/Waitress; không dùng runserver cho production, chưa thiết lập server ASGI riêng. Waitress có tài liệu hỗ trợ Python 3.13 ở nhánh 3.x; phiên bản được khóa thay vì tự lấy latest khi cài. Nguồn: [Waitress](https://docs.pylonsproject.org/projects/waitress/en/latest/).

Sau khi hosting đã cấp đầy đủ env, từ thư mục mã và bằng Python 3.13 trong venv mới của server:

```powershell
python -X utf8 -m pip install -r requirements-production.txt
python -X utf8 -m pip check
python -X utf8 manage.py check --deploy --settings=config.production
python -X utf8 manage.py check_inference_models --settings=config.production
python -X utf8 manage.py migrate --plan --settings=config.production
# Chỉ thực hiện migrate sau backup và xác minh DB đích của lần triển khai thực tế.
python -X utf8 manage.py collectstatic --noinput --settings=config.production
python -X utf8 scripts/serve_production.py
```

`collectstatic` dùng ManifestStaticFilesStorage, tạo tên file có hash và `staticfiles.json`. Mẫu `deploy/nginx.conf.example` phục vụ **chỉ STATIC_ROOT** tại `/static/`; Waitress không phục vụ static. Không dùng Django runserver/static view ở production. Quy trình theo [Django static deployment](https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/).

`serve_production.py` chỉ bind loopback `127.0.0.1`; `DJANGO_WSGI_PORT` mặc định 8000, có thể cấu hình. Hai profile:

- `direct` (mặc định): HTTP nội bộ, không trust proxy header; Django redirect sang HTTPS. Dùng kiểm startup/redirect, **không phải TLS endpoint phục vụ người dùng**.
- `nginx-loopback-tls`: chỉ dành cho Nginx kết thúc TLS trên cùng máy rồi chuyển tới backend loopback riêng tư. Bắt buộc `DJANGO_PROXY_PROFILE_CONFIRMED=1` sau khi xác minh topology. Waitress gán scheme HTTPS cố định cho kênh nội bộ này; không đọc `X-Forwarded-*`. Nginx mẫu redirect port 80 sang 443, gỡ forwarding headers trước khi proxy. Không mở port backend ra mạng. Các process khác trên máy phải nằm trong ranh giới tin cậy.

`SECURE_PROXY_SSL_HEADER=None`, `USE_X_FORWARDED_HOST=False`, `trusted_proxy=None`; không tự tin mọi IP hoặc header do client gửi. **Chưa có hosting được chọn nên chưa bật profile TLS proxy thực tế**. PaaS, container nhiều proxy hoặc TLS ở máy khác cần rà topology và cấu hình riêng; không bật cờ xác nhận một cách máy móc. Xem [Waitress runner/proxy options](https://docs.pylonsproject.org/projects/waitress/en/latest/runner.html).

Mẫu Nginx còn placeholder domain/chứng chỉ/static path, chưa chạy `nginx -t`, chưa kiểm TLS/renewal thực tế. Cần quản lý khởi động lại tiến trình, TLS, volume, backup và cleanup bằng công cụ hosting sau khi chọn nơi triển khai; chưa tạo các dịch vụ đó.

## 4. Gói suy luận tối thiểu

Tạo từ artifact và metadata hiện có; không huấn luyện, refit, sửa định dạng, chuẩn hóa hoặc kết quả thí nghiệm. Ví dụ PowerShell, thay đường dẫn placeholder bằng thư mục riêng **chưa tồn tại**, ngoài dự án:

```powershell
& .\.venv\Scripts\python.exe -X utf8 scripts/build_inference_bundle.py --output '<thu-muc-rieng-tuyet-doi-chua-ton-tai>'
& .\.venv\Scripts\python.exe -X utf8 scripts/build_inference_bundle.py --output '<thu-muc-goi-da-tao>' --verify-only
```

Script xác minh selection/hash nguồn trước khi copy, từ chối ghi đè và đích trong mã nguồn. Manifest chứa kích thước/SHA-256 từng tệp, SHA metadata nguồn và hash requirements. Metadata dẫn xuất chỉ giữ trường mà loader cần; không mang theo lỗi mẫu, câu mơ hồ, dataset hoặc toàn bộ báo cáo nghiên cứu. Nguồn và artifact gốc giữ nguyên.

Gói đã tạo ngoài Git tại:
`D:\SAO LUU KHOA LUAN\preparation-13c-20261022-082259\inference-bundle`

| Tệp trong gói | Kích thước byte |
|---|---:|
| `en/model.joblib` | 3.800.561 |
| `en/metadata.json` | 384 |
| `vi/model.joblib` | 765.200 |
| `vi/metadata.json` | 194 |
| `vi/artifact-manifest.json` | 218 |
| `requirements.txt` | 342 |
| `bundle-manifest.json` | Manifest tự liệt kê các tệp còn lại; không tự hash chính nó |

Hash model EN: `362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345`.

Hash model VI: `19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55`.

`check_inference_models` kiểm danh sách tệp/hash, Python nhánh 3.13, toàn bộ 14 phiên bản requirements, đường dẫn cấu hình trong gói, rồi tải thật cả hai Pipeline bằng loader hiện có. Hai loader tiếp tục kiểm metadata/hash/cấu trúc trước suy luận. Đây là artifact đáng tin cậy của dự án; không nhận file/model path từ request. Không đưa adapter DLL của CLI vào server.

Khi chuẩn bị server chỉ cần mã ứng dụng, migrations, templates, static nguồn, requirements production, script phục vụ và gói suy luận này. Không copy `.venv`, `data/`, DB local, backup, secret local, dataset, mô hình thử khác hoặc thư mục thí nghiệm đầy đủ. Cấp cấu hình/DB/gói suy luận bằng đường riêng. Nếu thiếu/lỗi model khi ứng dụng đang chạy, chức năng gợi ý vẫn báo không sẵn sàng theo cơ chế cũ và cho nhập tay; preflight trước phát hành phải phát hiện lỗi.

## 5. Kết quả kiểm tra thực tế

Tất cả kiểm tra production dùng venv **mới**, secret QA ngẫu nhiên và **SQLite mới** ở `D:\SAO LUU KHOA LUAN\preparation-13c-20261022-082259\state\qa.sqlite3`. Không kết nối DB thật trong kiểm tra production. Tệp env QA để riêng trong thư mục QA, không đưa nội dung vào báo cáo.

Runtime QA: Python **3.13.16 AMD64 / Windows**, đường dẫn `D:\SAO LUU KHOA LUAN\preparation-13c-20261022-082259\.venv\Scripts\python.exe`. Cài đúng 14 phiên bản cũ + Waitress 3.0.2; `pip check` đạt. Lần cài đầu gặp lỗi console Unicode; việc khởi động lại pip trước khi tiến trình cũ kết thúc gây thêm khóa tệp. Đã chờ hoàn tất, cài thành công với `-X utf8 --progress-bar off`, kiểm phiên bản và tải thật hai model; không nâng phiên bản hay sửa venv gốc.

| Kiểm tra | Kết quả |
|---|---|
| Hồi quy Django sau tách cấu hình dùng chung | **203/203 đạt**, 70,221 giây; DB test riêng do Django tạo/xóa |
| Kiểm thử cấu hình production sau siết đường dẫn cuối cùng | **5/5 đạt**; thiếu env, host/origin sai, DB local/relative, storage sai, static/model chồng đường dẫn, entrypoint local, proxy chưa xác minh đều bị chặn |
| Local system check | Không lỗi/cảnh báo, 0 silenced |
| Production `check --deploy` | Chỉ còn **security.W005 và security.W021**, 0 silenced; chi tiết bên dưới |
| Production migrations | Áp dụng tất cả migrations vào DB QA mới, gồm ngân sách/trigger; `migrate --check` đạt |
| `makemigrations --check --dry-run` | No changes detected; không đổi schema |
| `collectstatic` | 4 tệp copy, 4 post-process; manifest và CSS có hash tồn tại |
| Preflight models | EN và VI đúng hash/runtime, tải Pipeline thành công; không fit |
| HTTPS bằng Django test client | Host lạ 400, thiếu CSRF 403, cookie Secure, HSTS; render 10 trang khi đăng nhập, URL CSS dùng manifest |
| Waitress thật trên loopback 8012 | HTTP → HTTPS 301; giả `X-Forwarded-Proto`/`Forwarded` vẫn không vượt redirect; đây là kiểm HTTP/WSGI, không phải TLS thực tế |
| CSV qua hai process QA | Preview còn đọc được, xác nhận thành công; dọn lô hết hạn giữ receipt/giao dịch |
| QA SQLite integrity | `PRAGMA integrity_check` = `ok` qua connection Django có đăng ký hàm SQLite |
| Linux/Unix | **Chưa xác minh**: WSL chưa cài, không có Docker khả dụng; chưa kiểm wheel/native library/pickle trên Linux |

Kiểm tra integrity bằng sqlite3 thuần ban đầu gặp `unknown function: django_date_extract()` vì CHECK constraint dùng hàm Django; đã thực hiện lại bằng connection Django và đạt `ok`. Đây là điều chỉnh công cụ QA, không sửa schema/dữ liệu dự án.

Hai cảnh báo còn lại được giữ công khai:

- **W005**: chưa bật HSTS cho mọi subdomain. Chỉ quyết định sau khi xác minh toàn bộ subdomain đều dùng HTTPS.
- **W021**: chưa bật HSTS preload. Chưa xác minh tên miền, thời hạn HSTS/chính sách preload; không bật chỉ để hết cảnh báo.

Không có `SILENCED_SYSTEM_CHECKS`. `check --deploy` đạt các kiểm khác không chứng minh server Internet đã an toàn/hoạt động. Chưa kiểm trình duyệt trên domain công khai, Nginx/TLS thật, restart/redeploy của hosting hoặc đa instance. Không tuyên bố tương thích Linux chỉ từ kiểm thử Windows.

## 6. Phạm vi còn lại trước triển khai

1. Chọn hosting có storage bền vững phù hợp SQLite hoặc làm task chuyển DB/migrations riêng; xác minh topology TLS, domain/CSRF, giới hạn quyền và cài runtime Linux nếu dùng Linux.
2. Trên môi trường staging riêng: kiểm Nginx/static/TLS thật, tải hai model, CSV qua restart/redeploy, quyền volume, giám sát không lộ dữ liệu, cleanup và backup/restore.
3. Chỉ sau đó cấp secret production riêng, rà lại HSTS/subdomain/preload và chạy lại preflight theo cấu hình thực. Chưa deploy hoặc mua dịch vụ trong task này.

Các log kiểm tra nằm ngoài Git trong thư mục QA nêu trên. Đối chiếu SHA-256 trước/sau **227 tệp** (DB thật, requirements gốc, dữ liệu/artifact và mã nghiệp vụ/migrations hiện có): **không tệp nào thay đổi**. Kết quả ở `preservation-result.json` ngoài Git. Đã dừng Waitress QA cổng 8012 sau kiểm tra; không đổi server local hoặc bản phục hồi 8003. Không đưa model hoặc dữ liệu lên Git; không commit/push trong task này.
