# TASK 14A — Chuẩn bị Render Free

Ngày rà: **22/10/2026**, dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`. Chỉ chuẩn bị mã, gói suy luận và hướng dẫn. **Chưa tạo Postgres/Web Service, Release hoặc token; chưa upload, deploy hay phát sinh phí.** Không chuyển dữ liệu local lên server.

## 1. Thông số triển khai đã chuẩn bị

| Mục | Giá trị |
|---|---|
| Service | Web Service, runtime **Python**, instance **Free**, một instance |
| Database | Render Postgres **Free**, cùng region và tài khoản với web |
| Python | **3.13.16**; `.python-version` và `PYTHON_VERSION` phải thống nhất |
| Build Command | **`bash deploy/render-build.sh`** |
| Start Command | **`bash deploy/render-start.sh`** |
| Settings | **`config.render`** |
| WSGI | Waitress **3.0.2**, **1 process / 2 thread**, connection limit 32 |
| HTTP | Bind **`0.0.0.0:$PORT`**, không chạy runserver/Nginx riêng |
| Static | WhiteNoise + CompressedManifestStaticFilesStorage, collectstatic khi build |
| Pre-deploy Command | **Để trống**; migrations chạy lúc start |
| Health Check Path | `/tai-khoan/dang-nhap/` — kiểm web, không đại diện DB/model hoạt động đầy đủ |
| Auto-deploy ban đầu | Nên tắt, phát hành thủ công sau khi rà thay đổi và backup |

Script được gọi bằng `bash`, không cần executable bit. `.gitattributes` giữ LF cho hai shell script. Waitress là server đã chọn ở TASK 13C; không thêm Gunicorn/Uvicorn. `WEB_CONCURRENCY`, `GUNICORN_CMD_ARGS`, `FORWARDED_ALLOW_IPS` của môi trường khác không được dùng để tự đổi cấu hình Waitress.

Render yêu cầu bind `0.0.0.0` và cung cấp `PORT`; public HTTP được chuyển sang HTTPS ở edge, sau đó TLS kết thúc trước backend. Backend port không trực tiếp public. Profile này dùng `wsgi.url_scheme=https` cố định tại Waitress, `trusted_proxy=None`, xóa forwarding headers và không tin forwarded host/IP. `SECURE_PROXY_SSL_HEADER=None`. Chỉ áp dụng khi `RENDER=true` và settings đúng; không dùng profile này trên máy chủ công khai thông thường. Không dùng wildcard proxy tùy tiện. Nguồn: [Render Web Services — ports/TLS](https://render.com/docs/web-services).

Render Free web hiện có **512 MB RAM / 0,1 CPU**. Hai thread và BLAS/OMP một thread là lựa chọn hạn chế tài nguyên, **chưa chứng minh** hai model + dự báo luôn vừa RAM hoặc đạt thời gian đáp ứng của Free. Hai model được nạp chung một process; không nhân bản theo nhiều worker. Nguồn cấu hình gói: [Render Compute Plans](https://render.com/docs/compute-plans).

## 2. Biến môi trường

Mẫu không có secret thật: `deploy/render.env.example`. Django không tự đọc `.env`; nhập biến trong Render Dashboard → Environment. Không dùng chung các biến SQLite của `config.production` cho Render.

| Tên | Nơi lấy / cách đặt |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.render`; shell scripts cũng đặt tường minh |
| `PYTHON_VERSION` | `3.13.16`; không dùng default Python của hosting |
| `DJANGO_SECRET_KEY` | Secret riêng do người vận hành tạo bằng trình sinh ngẫu nhiên an toàn; tối thiểu 50 ký tự, không dùng khóa local; chỉ placeholder `REPLACE_WITH_SEPARATE_RANDOM_SECRET` trong tài liệu |
| `DJANGO_ALLOWED_HOSTS` | Host chính xác của service, ví dụ placeholder `REPLACE_WITH_SERVICE.onrender.com`; không scheme/port/wildcard |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | HTTPS origin tương ứng, ví dụ `https://REPLACE_WITH_SERVICE.onrender.com`; custom domain sau này phải cấu hình cả hai danh sách |
| `DATABASE_URL` | **Internal Database URL** trong mục Connect của Postgres cùng region; là secret, placeholder `REPLACE_WITH_INTERNAL_POSTGRES_URL` |
| `DJANGO_MODEL_RELEASE_TAG` | Tag của Release đã publish trong repo Private, đề xuất `inference-vi-en-v1`; không phải URL |
| `DJANGO_MODEL_BUNDLE_SHA256` | SHA-256 ZIP tính ở máy chuẩn bị, không lấy hash tùy ý từ file tải về |
| `GITHUB_ARTIFACT_TOKEN` | Token chỉ đọc Release trong đúng repository; chỉ đặt ở env máy chủ, không dán vào chat/source/URL/log |
| `RENDER`, `PORT`, `RENDER_EXTERNAL_HOSTNAME` | Render tự cấp; không giả lập để chạy production ngoài Render |

Trong build/start, script đặt `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `BLIS_NUM_THREADS` bằng `1`. Không cần nhập riêng các biến này.

`config.render` luôn DEBUG=False; bắt buộc PostgreSQL URL đầy đủ và driver `django.db.backends.postgresql`. Thiếu/sai URL hoặc không kết nối được thì dừng, **không tạo SQLite dự phòng**. Nội dung lỗi parser/DB không được in bởi startup wrapper. Kết nối internal dùng `sslmode=require`, timeout 10 giây, `CONN_MAX_AGE=0`, health checks bật. Chế độ TLS này theo [Render Postgres internal SSL](https://render.com/docs/postgresql-creating-connecting#ssl-modes-for-internal-connections); không tuyên bố verify-full cho chứng chỉ internal tự ký.

Tên host chỉ được lấy từ cấu hình rõ ràng, không dùng `*`. Cookie Secure, HTTPS redirect và HSTS 3.600 giây được giữ. W005/W021 vẫn được báo vì chưa bật HSTS toàn subdomain/preload; chưa tắt cảnh báo hoặc đăng ký preload.

Nguồn tham chiếu: [Render environment variables](https://render.com/docs/environment-variables), [Python version](https://render.com/docs/python-version). Tên miền thực tế và khả năng cấp Python 3.13.16 trên runtime Render **chưa được thử**; không tự đổi phiên bản ML để vượt lỗi build.

## 3. Dependency và khác biệt với TASK 13C

`requirements.txt` giữ nguyên 14 phiên bản. `requirements-production.txt` vẫn chỉ bổ sung Waitress. Tệp **`requirements-render.txt`** tham chiếu chúng và khóa thêm:

```text
dj-database-url==3.1.2
psycopg==3.3.6
psycopg-binary==3.3.6
whitenoise==6.12.0
```

Đã cài các phiên bản này vào **venv QA mới ngoài dự án**, không cài thêm vào `.venv` local. Không refit/huấn luyện/đổi định dạng model. `check_inference_models` vẫn kiểm Python 3.13, đúng toàn bộ phiên bản runtime ML và hash cả EN/VI.

`config/production_shared.py` gom kiểm secret/host/origin và bảo mật của TASK 13C để tránh sao chép. `config.production` vẫn là profile SQLite trên storage bền vững; **không dùng nó trên Render Free**. Local vẫn dùng `config.settings`/`config.local` như cũ.

### Migration PostgreSQL

- `0008_budget_category_guards`: giữ nguyên SQL SQLite, đổi sang thao tác có kiểm vendor. SQLite đã áp dụng 0008 không chạy lại; PostgreSQL mới bỏ qua cú pháp SQLite.
- `0009_postgresql_budget_guards`: tạo function/trigger PostgreSQL bảo vệ chủ sở hữu/loại danh mục ngân sách và chặn đổi loại/chủ danh mục đang có ngân sách. Khóa dòng danh mục khi ghi ngân sách. Trên SQLite, migration mới không chạy SQL/schema hay sửa bản ghi.
- Chưa chạy migration nào vào SQLite thật. **0009 chưa đánh dấu áp dụng ở DB local**; đây là trạng thái dự kiến của task, không phải thao tác bị bỏ quên. Migrations mới đã chạy trong DB test riêng của Django.
- PostgreSQL thật chưa có trong môi trường này, nên **chưa xác minh thực thi PL/pgSQL, rollback, khóa đồng thời hoặc toàn bộ nghiệp vụ trên PostgreSQL**. Kiểm thử vendor/SQL không thay thế kiểm thử DB thật. Đây là mục bắt buộc kiểm trên môi trường thử trước khi dùng dữ liệu có giá trị; không báo đã tương thích hoàn toàn chỉ vì cấu hình import được.

## 4. Chuẩn bị private Release (chưa thực hiện upload)

Gói tối thiểu TASK 13C vẫn giữ nguyên. ZIP đã chuẩn bị tại:

```text
D:\SAO LUU KHOA LUAN\preparation-14a-20261022-085600\inference-vi-en-v1.zip
```

Kích thước **4.081.000 byte**, SHA-256:

```text
08884ddf9a7b90ed8ebd23cc96f0121dfde3c0342f300ce7e19e7d8e46f17eeb
```

Sidecar `inference-vi-en-v1.zip.metadata.json` cùng thư mục ghi tên, kích thước/hash và repo. Đây là giá trị để đặt `DJANGO_MODEL_BUNDLE_SHA256` cho **đúng ZIP này**.

ZIP chỉ có 7 tệp: `en/model.joblib`, `en/metadata.json`, `vi/model.joblib`, `vi/metadata.json`, `vi/artifact-manifest.json`, `requirements.txt`, `bundle-manifest.json`. Không có dataset, giao dịch, DB, secret, script adapter DLL hoặc toàn bộ kết quả nghiên cứu.

| Model | SHA-256 được khóa trong mã/metadata |
|---|---|
| EN | `362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345` |
| VI | `19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55` |

Lệnh đóng gói lại, với đích mới chưa tồn tại ngoài dự án:

```powershell
& .\.venv\Scripts\python.exe -X utf8 scripts/package_inference_bundle.py `
  --bundle 'D:\SAO LUU KHOA LUAN\preparation-13c-20261022-082259\inference-bundle' `
  --output '<duong-dan-moi-ngoai-du-an>\inference-vi-en-v1.zip'
```

ZIP cố định thứ tự/timestamp thành viên; không thử model mới. Nếu đóng lại bằng runtime/zlib khác, dùng hash thực tế của ZIP mới và kiểm lại; không giả định byte ZIP luôn giống giữa mọi nền tảng.

Các bước cho lần triển khai được cho phép sau này:

1. Giữ repository **`thiennamm/khoa_luan_tai_chinh_ca_nhan` Private**. Release kế thừa quyền truy cập của repo; không đổi repo sang Public.
2. Tạo Release tag `inference-vi-en-v1`, đính kèm **đúng tên** `inference-vi-en-v1.zip`, publish Release. Có thể ghi hash không bí mật trong release notes; giá trị env phải đối chiếu hash ở máy chuẩn bị.
3. Tạo **fine-grained personal access token**: resource owner `thiennamm`, chọn **Only select repositories → đúng repo trên**, quyền **Contents: Read-only** (Metadata read theo mặc định). Đặt hạn dùng ngắn phù hợp buổi demo; không cấp write/admin hoặc quyền toàn bộ repo.
4. Đặt token vào `GITHUB_ARTIFACT_TOKEN` trong Render Environment. Không đặt vào lệnh shell, URL tải, README hoặc Git; không gửi qua chat. Task này **chưa tạo token**.
5. Đặt tag và hash ZIP vào env. Không cần lấy asset ID thủ công: build gọi GitHub API theo tag trên **repo cố định**, tìm đúng một asset có tên cố định đã upload, rồi tải qua API asset ID.

Quyền Contents read và cách API trả 200/redirect cho binary được mô tả tại [GitHub Release assets REST API](https://docs.github.com/en/rest/releases/assets). Không dùng token classic có quyền repo rộng khi fine-grained đáp ứng được.

### Kiểm tra tải và giải nén

`download_inference_bundle.py` không nhận URL tùy ý. Token chỉ ở Authorization header đến `api.github.com`; khi redirect sang các host CDN GitHub được cho phép, Authorization bị bỏ. Không in URL ký tạm hoặc exception mạng có thể chứa dữ liệu nhạy cảm. Không theo HTTP/host lạ. Token không được đưa vào URL.

Script giới hạn ZIP/giải nén 32 MiB, kiểm SHA ZIP **trước khi mở ZIP**, chỉ nhận đúng 7 tên tệp nguyên gốc, chặn tên trùng, đường dẫn vượt đích/absolute/ổ đĩa/backslash, symlink và entry bất thường. Sau đó kiểm manifest/hash từng tệp, hash model đã khóa và requirements; chỉ khi đạt mới đưa thư mục tạm vào đường dẫn suy luận. Không tải joblib không xác minh để thử.

Gói được lưu trong **`.render-private/inference` của build artifact**, ngoài static, bị Git ignore. Khác TASK 13C dùng model ngoài thư mục mã, Render cần mang gói đã tải cùng build image để có lại sau restart. Đây là bản sao bất biến dựng lúc build, **không phải nơi lưu tài chính bền vững**. Script từ chối đích đã tồn tại; nếu môi trường build giữ thư mục cũ, dùng build sạch/clear build cache rồi tải lại, không tái dùng model cache không khớp release.

## 5. Trình tự build và start trên Free

Build: cài requirements Render → pip check → tải/kiểm bundle → collectstatic → check --deploy → preflight tải thật hai model. Không migrate ở build, không truy cập SQLite local. Static có hash/gzip và manifest; WhiteNoise chỉ phục vụ STATIC_ROOT, không phục vụ `.render-private`. Cách bố trí middleware/storage theo [WhiteNoise Django](https://whitenoise.readthedocs.io/en/stable/django.html).

Start: kiểm settings/model → kết nối PostgreSQL → lấy **session advisory lock** riêng cho migration → `migrate --noinput` → kiểm không còn migration thiếu → dọn CSV hết hạn → nhả khóa/đóng kết nối startup → phục vụ Waitress trong cùng process giữ cache model. DB lỗi, model lỗi hoặc khóa đang bận thì dừng; không seed, không tự tạo tài khoản, không chuyển sang SQLite. Deployment đang trùng cần chờ rồi retry, không xóa bảng migration.

Migrate lúc start phù hợp giới hạn không shell/pre-deploy trả phí. Nhược điểm: startup/cold start chậm hơn; migration chưa xong thì chưa bind port; release cũ có thể còn phục vụ khi release mới migrate. Các migration tương lai phải tương thích với release cũ, có backup và có kế hoạch rollback riêng. Không coi rollback mã là tự rollback DB. Nguồn: [Render deploy phases](https://render.com/docs/deploys).

## 6. Các bước tạo dịch vụ sau khi được phép triển khai

1. Rà/commit/push mã được phép lên repo Private bằng task Git riêng; giữ model, dataset, SQLite, cấu hình thật và `.venv` ngoài Git. Gói model đi qua Release riêng, không commit ZIP.
2. Render Dashboard → **New → Postgres**: chọn **Free**, cùng region dự định chạy web; giữ dung lượng gói Free, không bật nâng gói/autoscaling tính phí. Lưu ngày hết hạn. Chọn region có Free khả dụng ở thời điểm tạo.
3. Khi DB sẵn sàng, lấy **Internal Database URL** ở Connect. Không dán URL chứa mật khẩu vào chat/log. Lựa chọn cùng region theo [Render Postgres](https://render.com/docs/postgresql-creating-connecting).
4. **New → Web Service** → liên kết GitHub, chỉ cho Render quyền repo cần dùng → chọn repo/nhánh đã rà. Chọn runtime Python, instance **Free**, region trùng DB. Không chọn public-repository mode để vượt quyền repo Private.
5. Điền Build/Start/Health Check đúng bảng đầu; để pre-deploy trống. Nhập các env ở mục 2, gồm secret riêng, DB URL và token chỉ đọc. Kiểm hostname/origin trước khi tạo; chưa có custom domain thì dùng host `onrender.com` chính xác được cấp.

   Nếu Dashboard chỉ hiển thị hostname chính xác sau khi tạo service, để build đầu dừng khi thiếu cấu hình, điền host/origin từ service rồi Manual Deploy. Không dùng wildcard hoặc đoán domain để bỏ qua kiểm tra.
6. Chỉ khi được phép deploy mới bấm tạo/chạy. Rà nhãn **Free** cho cả hai dịch vụ và Billing/spend limit; không tạo thêm disk, worker hoặc cron trả phí. Task hiện tại không thực hiện các nút này.
7. Đọc log theo từng bước; thiếu runtime/wheel, GitHub 401/404/403, hash lệch, thiếu artifact hoặc lỗi migrations thì dừng xử lý nguyên nhân. Không bỏ kiểm hash, sửa điểm thí nghiệm, đổi SECRET_KEY local hay dùng SQLite để cố chạy.
8. Sau deploy thử: đăng ký tài khoản QA mới bằng giao diện (không seed), kiểm CRUD/CSV/coverage/ngân sách/dự báo và cả hai chế độ gợi ý. PostgreSQL thật phải chạy kiểm thử hồi quy và guard migrations trên DB thử riêng trước khi dùng dữ liệu có giá trị. Chưa làm các bước này trong TASK 14A.

## 7. Dữ liệu và kiểm tra sau restart

PostgreSQL giữ tài khoản, session DB, danh mục, giao dịch, coverage, ngân sách, kết quả dự báo, CSV preview/receipt. Không có tệp SQLite của web. Preview vẫn hết hạn sau 30 phút; payload nằm DB, không ở cookie/filesystem. Cleanup toàn cục chạy lúc startup, thêm cơ chế cũ khi upload; Free hiện **chưa có job dọn định kỳ**. TTL ngăn xác nhận muộn, không chứng minh payload được xóa vật lý đúng phút thứ 30 nếu service không chạy cleanup.

Sau này kiểm bằng tài khoản QA: ghi lại ID/số lượng/tổng tiền của vài giao dịch, ngân sách/coverage; tải CSV để ở trạng thái preview. Restart web trên Dashboard, đăng nhập lại và so sánh đúng ID/nội dung/tổng; thử preview còn hạn, xác nhận một lần rồi kiểm chặn nhập lại. Kiểm hai model/gợi ý và hashed static còn hoạt động sau restart/redeploy. Cache demo RAM mất là dự kiến; không coi mất cache là mất giao dịch. Không dùng khoảng ngày CSV làm bằng chứng lịch sử đầy đủ.

Mô hình/static được cung cấp lại từ build artifact; dữ liệu tài chính không ghi vào image. Secret production giữ ổn định qua restart để phiên/chữ ký không bị thay vô cớ. Hỏng hoặc mất Postgres là tình huống khác với restart web, cần backup riêng.

### Giới hạn Free cần biết

Web ngủ sau 15 phút không có traffic; file runtime mất qua restart/redeploy/spin-down; không có persistent disk, shell hoặc one-off jobs. Có 750 giờ Free/workspace/tháng. Postgres Free: 1 DB/workspace, 1 GB, hết hạn sau 30 ngày; 14 ngày gia hạn để nâng gói trước khi xóa, không phải 14 ngày tiếp tục dùng miễn phí. Không có backup được quản lý/pooling. Băng thông và build minutes vượt quota có thể tính thêm khi có phương thức thanh toán; cần kiểm Billing/spend limit, không coi nhãn Free là cam kết mọi sử dụng không phát sinh phí. Nguồn: [Render Free](https://render.com/docs/free).

Lên kế hoạch backup thủ công **trước hết hạn** từ máy tin cậy bằng pg_dump qua external URL có TLS; dùng PGSERVICEFILE/PGPASSFILE riêng tư để tránh password trên command line. Chưa có DB nên chưa thực hiện hoặc kiểm phục hồi Postgres. CSV export không phải backup đầy đủ tài khoản/coverage/ngân sách/receipt. Không dùng Free làm nơi giữ duy nhất dữ liệu tài chính có giá trị lâu dài.

## 8. Kiểm tra thực tế và giới hạn

QA nằm tại `D:\SAO LUU KHOA LUAN\preparation-14a-20261022-085600`, Python venv mới riêng. Render profile được mô phỏng trong bản sao mã QA; URL PostgreSQL trỏ loopback cổng không có DB, không phải database thật. Không copy SQLite thật vào QA Render.

| Kiểm tra | Kết quả |
|---|---|
| Cài dependency, pip check | 14 phiên bản cũ + Waitress và 4 gói Render đúng pin; pip check đạt |
| Hồi quy Django cuối | **215/215 đạt**, 64,675 giây, DB test riêng; gồm 12 kiểm thử Render và các luồng website có sẵn |
| ZIP thật đóng gói → kiểm hash → giải nén → verify | Đạt, đúng 7 tệp và hai hash model |
| Tải Release riêng tư qua mạng | **Chưa kiểm**: chưa có Release/token; dùng mock HTTP để kiểm redirect/header/quyền thất bại |
| Cấu hình Render / DB URL | Từ chối thiếu/sai/SQLite; không connect khi import; runtime không fallback khi DB mất |
| collectstatic | 4 tệp copy, 8 post-process (hash/gzip), không cần Nginx |
| WhiteNoise/Waitress QA thật trên Windows | Trang đăng nhập và CSS hashed/gzip trả đúng nội dung; forwarding header giả không thay host/scheme; đường dẫn artifact riêng trả 404 |
| Preflight EN/VI | Tải thật đúng hash, Pipeline và phiên bản; không adapter DLL |
| check --deploy Render QA | W005/W021 còn công khai, 0 silenced; không có cảnh báo khác |
| Bash scripts | `bash -n` đạt bằng Git Bash trên Windows; start ngoài Render bị chặn; **không phải kiểm Linux** |
| PostgreSQL migrations | Đã kiểm nhánh vendor và SQL được chọn bằng mock; SQLite fresh migrations/guards nằm trong hồi quy. **Chưa chạy PostgreSQL thật** |
| Full Linux / full Render build-start / TLS / cold start / RAM 512 MB | **Chưa xác minh**: WSL chưa cài, không có Docker/Linux/PostgreSQL khả dụng; chưa tạo dịch vụ |

Kiểm thử ban đầu phát hiện kiểm tên ZIP có thể bị Windows chuẩn hóa trước khi kiểm; đã sửa sang tên nguyên gốc `orig_filename` và kiểm lại. Không sửa model hoặc dữ liệu để đạt kiểm thử. Các test runtime Render được bỏ qua có thông báo khi chạy venv local chưa cài dependency deploy; khi chạy venv QA đủ requirements-render, cả 12 test đều chạy. Không cần cài các gói deploy vào local chỉ để mở website.

Đối chiếu SHA-256 **168 tệp** DB thật/requirements gốc/data/artifact: **không thay đổi**. Rà 184 đường dẫn đã theo dõi và chưa theo dõi được Git cho phép: không có DB/model/dataset/secret file, không thấy token/private-key theo mẫu có tín hiệu cao; rà đối chiếu khóa local riêng không in nội dung. `git diff --check` đạt (chỉ có thông báo Git chuẩn hóa LF/CRLF của một số tệp cũ). Hai thư mục build được ignore hẹp; `.env`/SQLite/model vẫn bị loại trừ. Đây là rà mã/cấu hình, không phải bảo đảm phát hiện mọi dạng bí mật có thể có.

Đã dừng server QA cổng 8014 sau kiểm tra. Server local và bản phục hồi cũ không bị đổi cấu hình/dữ liệu. Chưa commit/push, chưa upload Release, tạo token, dịch vụ hoặc deploy. Log và kết quả đối chiếu giữ trong thư mục QA ngoài Git.

## 9. TASK 14B — Phát hành mã và bundle riêng tư

Ngày thực hiện: **22/10/2026**. Các ghi nhận “chưa upload/commit” ở trên thuộc mốc 14A; mục này bổ sung kết quả phát hành sau đó.

Preflight bằng đăng nhập Git Credential Manager hiện có: API xác nhận tài khoản **thiennamm**, repo **thiennamm/khoa_luan_tai_chinh_ca_nhan**, `private=true`, `visibility=private`, có quyền push. Remote origin vẫn là URL repo này; nhánh main ban đầu đồng bộ remote. Chưa tồn tại tag/Release `inference-vi-en-v1` khi kiểm tra trước tạo. Không thay remote hoặc quyền truy cập.

ZIP nguồn đúng đường dẫn mục 4, **4.081.000 byte**, SHA-256 **08884ddf9a7b90ed8ebd23cc96f0121dfde3c0342f300ce7e19e7d8e46f17eeb**. Đã kiểm trước giải nén, danh sách đúng 7 tệp, manifest và hash cả hai model trùng tài liệu/mã. Hai joblib và năm tệp metadata/khóa runtime; không có DB, giao dịch, dataset, secret hoặc launcher DLL.

Rà **184 tệp ứng viên**, kể cả **123 tệp đã theo dõi**: không có đường dẫn dữ liệu/model/secret bị cấm, không thấy token/private key theo mẫu hoặc khóa local thật. Secret chỉ so sánh trong bộ nhớ, không in nội dung. Mã website đã hoàn thành nhưng chưa sao lưu từ mốc 11A cũng được đưa vào mốc mã để bảo đảm đủ module/templates/migrations cần chạy. Không sửa nghiệp vụ, dữ liệu hoặc kết quả ML trong task này; tận dụng hồi quy 215/215 của 14A vì mã không đổi.

Release dùng tag **`inference-vi-en-v1`**, ghim commit mã đã push. Biên nhận URL/asset và lần tải kiểm lại được bổ sung sau khi thao tác thành công; cập nhật tài liệu sau đó dùng commit riêng, không di chuyển tag.
