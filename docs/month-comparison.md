# TASK 22A — So sánh thu–chi giữa hai tháng

**Trạng thái bàn giao — 01/11/2026:** người dùng chấp nhận bàn giao dựa trên kiểm thử nghiệp vụ, ảnh desktop/mobile và các thao tác thủ công đã xác nhận, đồng thời cho phép commit/push `main`. Các mục thiếu bằng chứng vẫn là **Chưa xác minh**: phép đo viewport nội dung, overflow/focus/Tab/phân trang tại đúng hai kích thước và phạm vi JavaScript-off còn thiếu. Không kết luận QA hoàn tất toàn bộ. Các đoạn “chưa commit/push” bên dưới là biên bản các lượt trước quyết định này; không phải yêu cầu tiếp tục hoãn bàn giao. Push có thể kích hoạt Render auto-deploy, nhưng bước bàn giao không truy cập production hoặc chạy migration.

Ngày kiểm chứng: **30/10/2026**. Dự án chính, nhánh **main**, commit nền `61532704c11c95c612312878b2836e9f4efa763e`; working tree sạch lúc bắt đầu. Không tìm thấy AGENTS.md trong repository hoặc thư mục cha trực tiếp. Chưa commit/push/deploy TASK 22A.

## Cách dùng

1. Từ Tổng quan, mở **Báo cáo & so sánh tháng**. Mở rộng ngay `/bao-cao-thang/` đã có, không tạo trang/dịch vụ so sánh song song.
2. Chọn **Tháng gốc A**, **Tháng đối chiếu B**, bấm **Xem báo cáo**. Mặc định B là tháng hiện tại theo Asia/Ho_Chi_Minh; A là tháng trước B. Liên kết từ Tổng quan giữ B đang chọn. Hai tháng có thể không liền nhau, đảo thứ tự hoặc trùng nhau.
3. Xem phần **So sánh thu–chi giữa hai tháng**, bảng tổng, biểu đồ cột và **Chi đã ghi nhận theo danh mục**. Báo cáo chính/cơ cấu/chi tiết giao dịch vẫn thuộc tháng B. Chọn ô chi tiết nếu muốn đưa toàn bộ giao dịch B vào báo cáo; không giới hạn 20 dòng ở phần chi tiết này.
4. Bấm số tiền A/B trong một dòng danh mục để mở Giao dịch với `period=month`, đúng `month`, `kind=expense` và ID category. Phân trang và gửi bộ lọc giữ cặp tháng; **Trở về so sánh hai tháng đã chọn** quay lại đúng A/B. Xóa bộ lọc là thao tác chủ động về mặc định của danh sách, không duy trì ngầm phạm vi cũ.

GET dùng `base_month=YYYY-MM` và `month=YYYY-MM`. Truyền rỗng/sai trả HTTP 400, lỗi theo trường, không thay bằng báo cáo tháng khác/toàn bộ dữ liệu. Năm 0001–9999 được hỗ trợ: khi B=01/0001 và không có A, không tự lùi ra năm 0; có thể chọn A tường minh, kể cả A=B.

## Định nghĩa số liệu

| Nội dung | Quy tắc |
|---|---|
| Phạm vi | Tất cả Transaction đã lưu trong trọn tháng, gồm ngày đầu/cuối; transaction và category cùng tài khoản đang đăng nhập |
| Thu, chi, hiệu | Income, expense và income − expense bằng Decimal; không phải số dư ngân hàng hoặc tiền tiết kiệm |
| Khoản dự kiến/phân bổ | Không lấy RecurringRule/Occurrence chưa ghi nhận hoặc SavingsEntry vào tổng |
| Giao dịch ngày tương lai | Giữ chính sách báo cáo hiện có: vẫn tính nếu đã lưu trong tháng. Đếm riêng số bản ghi sau ngày hôm nay Việt Nam ở mỗi tháng; hiện số lượng/phạm vi, không tự sửa/xóa hoặc bỏ khỏi tổng |
| Chênh lệch tiền | B − A; chữ **Tăng / Giảm / Không đổi** kèm tiền có dấu; không chỉ dựa vào màu |
| Tỷ lệ | (B − A) / A × 100 chỉ khi A > 0, Decimal và ROUND_HALF_UP đến 2 chữ số. A=0: “Không tính tỷ lệ: tháng gốc bằng 0”; A<0: “Không tính tỷ lệ: tháng gốc âm” |
| Hiệu thu trừ chi | Có thể âm; không áp dụng tỷ lệ khi A âm hoặc 0. Nếu A dương, tỷ lệ chỉ mô tả hiệu thu trừ chi, không gọi là tăng trưởng số dư |
| Danh mục | Hợp hai tập category ID có expense ở A/B; chỉ một tháng vẫn có dòng. Tháng không có bản ghi cho ID đó có tổng **đã ghi** là 0. Sắp theo chênh lệch chi giảm dần, hòa theo ID tăng dần |
| Tên/trạng thái category | Dùng tên hiện tại, không gộp chỉ vì trùng tên. Schema chưa có cờ active và Transaction.category là FK NOT NULL + PROTECT; xóa category đang được dùng bị chặn. Không bịa “danh mục đã xóa”; giữ lọc chủ category như thống kê cũ, không sửa liên kết bất thường |
| Coverage | Trạng thái riêng từng tháng; tháng hiện tại ghi **Tháng đang diễn ra** ở phần so sánh và thời điểm cập nhật Việt Nam. Chưa kết thúc/chưa complete thì có cảnh báo có thể thiếu |
| Diễn giải | Chỉ mô tả số đã ghi; không suy nguyên nhân, không gọi công thức là ML, không kết luận chi giảm là quản lý tốt hơn |

Không có bản ghi không chứng minh không phát sinh thu/chi ngoài website. Zero thống kê không thay quy tắc `forecast_expense=None` cho tháng chưa xác nhận; không tự xác nhận coverage hoặc tính/lưu dự báo.

## Triển khai và quyền riêng tư

- Dùng lại `MonthlyReportForm`, `monthly_report` và `report_data`. Giữ URL, GET-only, login_required, never_cache/private/no-store, autoescape. Không nhận user_id để truy xuất tài khoản khác.
- `finance.services.recorded_month_groups` tổng hợp **tại database** theo tháng/loại/category ID/tên: SUM, COUNT và count ngày tương lai; chỉ hai tháng được chọn. `finance.statistics.recorded_month_statistics` dùng chung cho Tổng quan 6/12 tháng và báo cáo, không viết bộ quy tắc thu–chi riêng.
- PostgreSQL dùng SUM numeric rồi chuyển text → Decimal. SQLite đăng ký aggregate `finance_vnd_sum` trên **kết nối**, cộng Decimal từ CAST(amount AS TEXT), precision 64; không dùng SUM float hoặc tổng INTEGER 64-bit làm phép cộng tiền. Không tạo bảng, extension hoặc SQL function bền vững; không cần quyền DDL bổ sung trong ứng dụng.
- Python chỉ xử lý các **nhóm đã tổng hợp**, ghép danh mục, hiệu/tỷ lệ và chiều cao cột; không tải mô tả/toàn bộ lịch sử giao dịch để so sánh. Hai tháng xa nhau không khiến truy vấn đọc cả khoảng giữa.
- Biểu đồ HTML/CSS local và bảng lấy cùng cấu trúc số liệu. Trục có đơn vị VND rút gọn; bảng luôn có số đầy đủ dạng `50.000 VND`. Không thêm JS, CDN hoặc dependency.
- Link quay lại là URL nội bộ được dựng từ hai tháng đã validate; không nhận return URL tùy ý. `comparison_a/comparison_b` được giữ khi lọc/phân trang, không mở quyền truy vấn category của người khác. Export tiếp tục tái dùng bộ lọc cũ; CSV/nhập nhanh không đổi.
- GET không tạo giao dịch/kỳ/coverage/ngân sách/forecast/feedback. Không cache số liệu riêng trong cache chung hoặc ghi nội dung vào log mới. Không thay schema, model ML, dependency hay thí nghiệm.

Giới hạn nhất quán: tổng hợp giao dịch và coverage là hai truy vấn đọc, không phải snapshot bất biến khóa người khác ghi. Nếu có cập nhật đồng thời, tải lại để đối chiếu trước khi chia sẻ/in. Không kiểm tải lớn hoặc mọi cấu hình database khác SQLite/PostgreSQL.

## Môi trường và kết quả kỹ thuật

Tất cả bằng chứng dưới đây là **local QA với dữ liệu mô phỏng**, không phải online hoặc dữ liệu người dùng thật. Thư mục **ngoài repository/Git**: `D:\POSTGRESQL QA\task22a-20261030-150132`. Đây là **tham chiếu local**, người đọc GitHub không truy cập được các tệp ở đường dẫn này.

- Runtime QA có sẵn Python 3.13.16/Django 5.2.18; không cài thư viện. Cấu hình ngoài Git kế thừa `config.base`, không import local thật hoặc đọc .env/URL Render.
- SQLite mới `qa.sqlite3` trong thư mục trên, migrate tới 0014; tài khoản A/B mới, dữ liệu giả. SQLite local thật **không mở**; chỉ đối chiếu size/mtime bằng metadata filesystem trước/sau, không gọi đó là kiểm SHA/integrity database thật.
- PostgreSQL portable **18.6**, cluster mới `pgdata` trong cùng thư mục QA, chỉ `127.0.0.1:55432`. Không dùng cluster phục hồi chứa dữ liệu cũ. Trước kết nối kiểm host/port/database/data_directory/listen_addresses/system identifier/server version; connection signal tiếp tục chặn đích khác trong test. Database `qa_task22a_tests` do Django tạo và xóa, chỉ có fixture kiểm thử; không kết nối Render.
- Đo `report_data(..., include_details=False)` bằng CaptureQueriesContext: **2 truy vấn của phần tổng hợp** (tổng hợp các nhóm + coverage), cả khi có 3 và 33 danh mục trong hợp A/B. SQL PostgreSQL có thể được driver khai báo dạng cursor SELECT khi dùng iterator; đây là số entry do Django đo, không phải số round-trip FETCH ở tầng driver. Không có truy vấn cho từng category; chưa kiểm tải hàng triệu bản ghi. **Chưa đo tổng số truy vấn của toàn bộ trang**: xác thực/session và các phần khác không nằm trong con số 2; không được gọi toàn trang chỉ có 2 truy vấn.

| Nhóm kiểm tra | Kết quả thực tế | Không cộng trùng |
|---|---|---|
| Hồi quy `finance` trên PostgreSQL QA | **458 bài duy nhất: 451 đạt lượt đầu, 7 lỗi cấu hình cookie QA**; sửa riêng tên cookie trong settings test và chạy lại **đúng 7 bài: 7/7 đạt** | Không gọi 458/458 trong một lượt hoặc cộng thêm 7 thành 465 |
| Nhóm liên quan PostgreSQL QA | **58/58 đạt**: 17 mới + thống kê/báo cáo/bộ lọc cũ | Là **tập con của 458 bài PostgreSQL duy nhất**, không cộng thành 516 |
| Lượt riêng SQLite QA | **58/58 đạt**, cùng nhóm kiểm thử liên quan chạy trên backend SQLite | Ghi riêng lượt/backend; không cộng thành số bài duy nhất mới hoặc cộng với 458 PostgreSQL |
| Sau chỉnh nhãn chi tiết tháng B cuối cùng | **31/31 SQLite QA** (so sánh + báo cáo), rồi kiểm UI trên template đã khởi động lại | Tập con của nhóm 58, không cộng thành tổng mới |
| JavaScript hồi quy | **43/43 đạt**; không có JS sản phẩm mới | Tách khỏi số bài Django |
| System check | 0 vấn đề trên QA; production static QA cũng đạt | Không kiểm production database |
| `makemigrations --check --dry-run` | **No changes detected**, không cần migration | Không migrate SQLite thật/production |
| collectstatic production QA | **11 tệp copied, 22 post-processed**, WhiteNoise compressed manifest, DEBUG=False; kiểm đường dẫn/hash/gzip asset gồm CSS báo cáo; chặn mọi kết nối database | Windows packaging, không phải build Linux/deploy |

7 lỗi cookie là các bài CSRF có sẵn truy cập tên `csrftoken`, trong khi cấu hình QA riêng ban đầu dùng `qa22_csrf`; không phải lỗi CSRF sản phẩm và không bỏ bảo vệ để đạt. Hai lượt liên quan ban đầu còn phát hiện lỗi fixture tên dài quá giới hạn 80 ký tự và giả định mọi entry SQL PostgreSQL phải bắt đầu bằng SELECT; đã sửa **kiểm thử** cho dữ liệu hợp lệ và cursor đọc. Không báo các lỗi QA này là sự cố production.

17 bài mới kiểm: A/B hợp lệ/sai/mặc định, giờ Việt Nam và đổi năm, năm nhuận/ngày biên, cùng tháng, empty/chỉ thu/chỉ chi, A=0/âm, Decimal lớn và HALF_UP, hợp category theo ID/rename/tie, coverage/current/future, owner/login/cache/POST, escape HTML/tên dài, kế hoạch/tiết kiệm loại khỏi tổng, GET không đổi toàn bộ model finance, links/phân trang đầy đủ và query count không tăng theo danh mục.

Lệnh đã thực hiện dùng Python QA và `manage_qa.py` **ngoài Git**, không sao chép sang `manage.py` local thật:

```powershell
$qaRoot = 'D:\POSTGRESQL QA\task22a-20261030-150132'
$qaPython = 'D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe'
& $qaPython -X utf8 "$qaRoot\manage_qa.py" test finance --settings qa22_pg_test_settings
& $qaPython -X utf8 "$qaRoot\manage_qa.py" test finance.test_month_comparison finance.test_statistics finance.test_monthly_report finance.test_transaction_filters --settings qa22_pg_test_settings
& $qaPython -X utf8 "$qaRoot\manage_qa.py" check --settings qa22_sqlite_settings
& $qaPython -X utf8 "$qaRoot\manage_qa.py" makemigrations --check --dry-run --settings qa22_sqlite_settings
node --test scripts/test_*.js
```

Credential QA được dọn ở bước kết thúc; các settings tham chiếu tệp đó không còn đủ cấu hình để chạy ngay, nên đây là biên bản lệnh, không phải bộ cấu hình tái chạy sẵn. Lượt SQLite liên quan đổi `--settings qa22_sqlite_settings`; lượt 7 bài CSRF chỉ gọi đúng 7 tên được lưu trong log retry, không chạy lại cả suite. Xem log ngoài Git để tra đầy đủ.

## Trình duyệt và bằng chứng

Đã thao tác thật bằng trình duyệt trong ứng dụng, chỉ tới `http://127.0.0.1:8022`, database SQLite QA. Không thay bằng HTTP 200 để gọi là kiểm UI.

| Kịch bản | Kết quả đã quan sát |
|---|---|
| Mở từ Tổng quan | B=10/2026, A=09/2026; thu A/B 12.000.000 / 13.000.000 VND; chi 5.500.000 / 2.770.000 VND; hiệu 6.500.000 / 10.230.000 VND |
| Đối chiếu số liệu | 4 bản ghi A, 26 B; chi B − A = −2.730.000 VND (−49,64%). Danh mục chỉ A/B, tên dài, coverage A complete/B unknown và 1 ngày tương lai ở B hiển thị đúng |
| Mở danh mục và phân trang | Ăn uống B có 23 giao dịch, tổng 1.720.000 VND; trang 2 có 3 dòng, quay lại giữ 09/2026–10/2026 |
| Hai tài khoản | Đăng xuất A, đăng nhập B: chỉ có chi B 987.654 VND/1 giao dịch, không có danh mục A. URL dùng category ID của A bị báo danh mục không hợp lệ, không lộ tên/dữ liệu A |
| Cùng tháng / tháng trống | A=B=10/2026 cho mọi chênh lệch 0; A=B=08/2026 có trạng thái trống và không chia mẫu số 0 |
| Bàn phím | Enter gửi form; region bảng có focus-visible và ArrowRight cuộn ngang; menu mobile dùng Enter mở/đóng |
| Không chạy script trang | QA thêm CSP `script-src 'none'`: nút in vẫn hidden, form GET chọn tháng, bảng, menu details và link mở giao dịch/quay lại hoạt động. Đây là chặn script trang bằng CSP trong QA, **không phải đã bật tùy chọn tắt JavaScript toàn trình duyệt** |

**Giới hạn viewport/ảnh:** đã yêu cầu 1280×900 và 390×844. Công cụ viewport chịu tỷ lệ hiển thị Windows; đo lại trong DOM sau hiệu chỉnh cho desktop **1281×900**, mobile **390×845**, sai khác 1 px, không gọi là đã kiểm chính xác tuyệt đối hai khung yêu cầu. Không tràn ngang toàn trang ở các kích thước đo được; bảng rộng cuộn trong vùng riêng. Ảnh viewport ban đầu bị cắt/vùng nền trống; ảnh toàn trang đọc được nội dung nhưng vẫn có lỗi ghép/sidebar và vùng trống do công cụ. Không coi ảnh này là lỗi bố cục sản phẩm đã xác minh. Lệnh mở Edge QA riêng bị cơ chế duyệt tự động chặn (“blocked by policy”), không đổi cách thực thi để vượt chặn.

Đã chỉnh riêng form mobile để A/B xuống hàng, tránh cắt chữ năm trong ô chọn tháng; không đổi validation. Chưa kiểm điện thoại vật lý, trình duyệt khác, in/PDF mới, Linux/Render, tắt JavaScript bằng cài đặt browser, hoặc tải lớn. Cần kiểm lại ảnh và đúng viewport bằng trình duyệt không gặp lỗi chụp trước khi tuyên bố QA giao diện đầy đủ.

Các tệp bằng chứng trong thư mục local nêu trên: `database-identity.json`, `fixture-summary.json`, `sqlite-handoff.log`, `postgresql-regression.log`, `postgresql-seven-cookie-retry.log`, `postgresql-handoff.log`, `final-template-related.log`, `javascript.log`, `static-report.json`, `browser-checks.json`, `desktop-final-report.jpg`, `mobile-final-report.jpg`, `mobile-full-no-scripts-final.jpg` và biên bản kết thúc. Các ảnh viewport/ảnh toàn trang ban đầu không phải ảnh cuối. Không đưa database, dump, cluster, session, ảnh/PDF riêng tư, credential hoặc cấu hình QA vào Git.

## Tệp sản phẩm thay đổi và bàn giao

- `finance/services.py`, `finance/statistics.py`: tổng hợp database chính xác và cấu trúc thống kê chung.
- `finance/monthly_report.py`, `finance/monthly_report_views.py`: chọn A/B, hiệu/tỷ lệ/category union, cùng URL báo cáo.
- `finance/views.py`, `templates/finance/transaction_list.html`: giữ A/B trên danh sách/phân trang và link quay lại, không đổi bộ lọc nghiệp vụ.
- `templates/finance/monthly_report.html`, `templates/finance/includes/month_comparison.html`, `templates/finance/dashboard.html`, `static/css/monthly-report.css`: chọn tháng, bảng/biểu đồ, hướng dẫn và responsive.
- `finance/test_month_comparison.py`, `README.md`, `docs/monthly-report.md`, `docs/financial-statistics.md`, tài liệu này: kiểm thử và hướng dẫn; giữ nguyên số liệu QA/PDF lịch sử TASK 19B/11C.

Không cần migration, chưa commit/push/deploy. Trạng thái dừng server, dọn credential và bảo toàn tệp được xác nhận trong biên bản kết thúc QA ngoài Git; không công khai bí mật hoặc dữ liệu tài chính thật.

### Kết thúc QA ngày 30/10/2026

- Web QA **8022** và PostgreSQL QA **55432** đã dừng, kiểm cả hai cổng đóng. Database test PostgreSQL đã được Django xóa; không dừng hoặc sửa server local thật.
- Xóa `credentials.json`, pwfile initdb và cờ CSP tạm; hủy session đăng nhập trong **SQLite QA**, đóng tab QA, reset viewport. Không xóa dữ liệu nghiệp vụ fixture hoặc cluster/bằng chứng cũ.
- Count/content hash của **19 model finance trong phiên kiểm UI cuối** giữ nguyên. File/schema model, hai artifact EN/VI và ba requirements giữ nguyên **6/6 SHA-256**. SQLite thật giữ nguyên size/mtime; không mở bytes để kiểm hash và không kết nối bằng Django.
- Rà diff/bí mật chỉ có mã, kiểm thử và tài liệu liên quan; không stage dữ liệu, ảnh, credential hoặc cấu hình QA. Bằng chứng kết thúc: `shutdown-report.json`, `browser-finance-before.json`, `browser-finance-after.json`; đây là tham chiếu local, không có trong repository.
- Kết luận trong phạm vi: kiểm logic/tổng hợp/phân quyền/hồi quy đã đạt theo các lượt riêng được ghi rõ; **QA giao diện còn giới hạn viewport/ảnh, chưa gọi là hoàn chỉnh trên đúng hai kích thước hay thiết bị thật**.

## Lượt hoàn tất QA theo yêu cầu tiếp theo — 30/10/2026

**Chưa đạt điều kiện commit/push.** Lượt này không sửa mã ứng dụng, chỉ cập nhật tài liệu này; giữ nguyên 15 tệp TASK 22A chưa commit. Không chạy lại suite vì không đổi mã. Các số kiểm thử ở trên là kết quả các lượt đã ghi, không phải một lượt mới hoặc tổng được cộng thêm.

Thư mục bằng chứng mới **ngoài repository**, chỉ tham chiếu local: `D:\POSTGRESQL QA\task22a-ui-20261030-163220`. Dùng SQLite backup API sao chép **database QA mô phỏng** của lượt trước sang `qa.sqlite3` mới trong thư mục này; xác minh nguồn có đúng hai tài khoản QA và 31 giao dịch giả trước sao chép. Chỉ đặt lại mật khẩu tài khoản giả trên **bản sao QA** để đăng nhập; không mở database thật, không đọc credential thật/.env của dự án hoặc kết nối Render. Credential mới chỉ dùng trong QA, không in ra báo cáo. Server chỉ `127.0.0.1:8022`; không khởi động PostgreSQL hoặc trình duyệt Edge riêng.

### Phép đo viewport trên trang thật

Đã dùng công cụ trình duyệt được phép, API viewport được công bố và đo trực tiếp **`window.innerWidth/window.innerHeight`**; không dùng kích thước cửa sổ hoặc cắt/resize ảnh để thay cho viewport. Tab trắng ban đầu báo đúng 1280×900 và 390×844, nhưng **đó không phải bằng chứng trên website**. Khi tải xong báo cáo QA:

| Yêu cầu API viewport | Đo trực tiếp trên báo cáo đã tải | Kết luận |
|---|---|---|
| 1280×900 | **1910×1343**; document clientWidth/scrollWidth đều 1887 | Chưa xác minh đúng 1280×900 |
| 390×844 | **582×1259**; document clientWidth/scrollWidth đều 560 | Chưa xác minh đúng 390×844 |

Đặt lại 1280×900 trên chính trang đã tải và phím chuẩn Ctrl+0 trong trang đều không khắc phục được. Nguyên nhân trong công cụ/host chưa được xác minh; không coi giả thuyết tỷ lệ hiển thị Windows là nguyên nhân đã chứng minh. Không thử lại hoặc tìm cách vượt chặn Edge QA.

Đã lưu **từng lần chụp viewport riêng bằng `fullPage:false`**, không dùng ghép ảnh/full-page: `desktop-form.jpg`, `mobile-requested-390x844-unverified.jpg`. Đây là **ảnh chẩn đoán không đạt viewport yêu cầu**, còn vùng trống/cắt của công cụ, không phải ảnh QA đạt chuẩn. Bằng chứng tham số và phép đo: `viewport-attempts.json`; không chỉnh kích thước ảnh để tạo cảm giác đã đạt.

### Những phần chưa thể chốt

- A/B mặc định 09/2026–10/2026 đã mở được trên bản sao QA; không có khác biệt mã cần sửa được xác minh trong lượt này. Tuy nhiên, **chưa chốt bộ chọn, coverage/ngày tương lai, bảng/biểu đồ/tên dài/empty, liên kết/phân trang, overflow hoặc bàn phím tại chính xác hai viewport yêu cầu**. Kết quả chức năng ở các kích thước khác của lượt trước vẫn là bằng chứng riêng, không thay thế phần còn thiếu này.
- Công cụ hiện chỉ công bố capability browser `visibility/viewport`, tab `pageAssets/webmcp`; không có API tắt JavaScript toàn trình duyệt. **Chưa xác minh chế độ browser tắt JavaScript**. Kiểm CSP `script-src 'none'` trước đó vẫn được ghi đúng là chặn script trang, không được đổi tên thành đã tắt JavaScript toàn browser.
- Không thử thiết bị vật lý, trình duyệt khác hoặc production. Không stage, commit, push, deploy hoặc đổi quyền repository khi điều kiện QA còn thiếu. Cần công cụ được phép có thể giữ đúng viewport trên trang đã tải và kiểm chế độ không JavaScript trước khi chốt phát hành.

Kết thúc lượt này: đã đăng xuất/đóng tab QA, reset viewport, dừng server 8022 và kiểm cổng đóng, xóa credential tạm và hủy session trên bản sao SQLite QA. Số dòng 19 model finance không đổi. Hash 14 tệp còn lại giữ nguyên so với đầu lượt; chỉ tài liệu này được cập nhật, không sửa mã ứng dụng nên không chạy lại suite. `handoff-report.json` ghi SHA local và remote main cùng `61532704c11c95c612312878b2836e9f4efa763e`; đó là commit nền **đã có**, không phải commit TASK 22A mới. Working tree còn đúng 15 tệp của task, index trống. `evidence-manifest.json` ghi hash ảnh chẩn đoán/biên bản; tất cả là tham chiếu local ngoài Git.

## Hỗ trợ kiểm thủ công — 31/10/2026, đang chờ kết quả

- Server `http://127.0.0.1:8022` còn chạy, dùng riêng SQLite mô phỏng `D:\POSTGRESQL QA\task22a-manual-20261031-162552\qa.sqlite3`. Đây là tham chiếu local ngoài Git, không phải database thật. Cấu hình kết nối có guard chặn database khác; không mở cấu hình local thật hoặc kết nối Render.
- Đã xác minh database QA có đúng hai tài khoản thử; đăng nhập `qa22_a`, mở báo cáo A=09/2026/B=10/2026 và đăng xuất bằng HTTP thành công. Tổng tháng B trong database QA và trang phản hồi khớp **thu 13.000.000 VND, chi 2.770.000 VND**. Đây là kiểm chứng truy cập HTTP/database, **không phải đã kiểm UI bằng trình duyệt**. Không in mật khẩu, không lưu credential vào tài liệu/repository.
- Ngày kiểm đã là 31/10/2026: giao dịch QA ngày 31/10 từng được tính là tương lai ở lượt 30/10 nay không còn là ngày tương lai. Không yêu cầu cảnh báo “1 ngày tương lai” như một kết quả bắt buộc ở lượt này; chưa bổ sung dữ liệu hoặc giả lập thời gian để kiểm lại trường hợp đó.
- **Chưa xác nhận đạt**: người dùng đăng nhập thủ công; số liệu trên màn hình; viewport nội dung đúng 1280×900 và 390×844 bằng `window.innerWidth/innerHeight`; bộ chọn A/B, bảng/biểu đồ, coverage, tên dài, trạng thái trống, liên kết/phân trang giữ tháng, tràn ngang, bàn phím và tắt JavaScript bằng DevTools. Các kết quả cũ ở kích thước khác không thay thế các mục đang chờ.
- Giữ server và credential QA tạm để người dùng kiểm tiếp; **chưa kết thúc phiên thủ công/chưa dọn credential của phiên này**. Khi người dùng xác nhận kết thúc, cần dừng đúng server QA, kiểm cổng đóng, hủy session QA và xóa credential tạm. Không mở lại Edge QA hoặc tìm cách vượt chặn.
- Chỉ cập nhật biên bản này, giữ nguyên mã và các thay đổi chưa commit khác; không chạy lại suite, không stage/commit/push/deploy. Kết quả kiểm thủ công sẽ được bổ sung sau khi có xác nhận hoặc bằng chứng thực tế.
- Phản hồi bước 1 của người dùng: **không đăng nhập hoặc không mở được trang**, chưa có thông báo lỗi cụ thể nên chưa xác định nguyên nhân. Kiểm lại ngay sau phản hồi: cổng 8022 có kết nối, credential QA còn tồn tại; đăng nhập/mở báo cáo/đăng xuất qua HTTP vẫn thành công và hai tổng tháng B vẫn khớp. Không suy diễn kết quả HTTP thành người dùng đã đăng nhập thành công; bước UI này vẫn chưa đạt và đang chờ xác định lỗi hiển thị/kết nối/xác thực cụ thể.
- Theo yêu cầu hỗ trợ đăng nhập tiếp theo, đã đối chiếu tiến trình chạy `serve_qa.py` của thư mục QA trên, settings có guard và đường dẫn database thực tế qua `PRAGMA database_list`: đúng `qa.sqlite3` QA. `qa22_a` tồn tại, đang hoạt động; credential cũ khớp hash mật khẩu. Đã đặt mật khẩu mới ngẫu nhiên **chỉ cho qa22_a trong QA**, đồng bộ credential cục bộ ngoài repository và cung cấp lệnh clipboard không in mật khẩu. Đăng nhập bằng mật khẩu mới qua HTTP tới server 8022, mở đúng báo cáo/tổng tháng B và đăng xuất đều thành công. Hash nội dung các model finance và mật khẩu tài khoản B giữ nguyên. Không sửa cơ chế đăng nhập/mã ứng dụng; không chạy lại suite. Biên bản không chứa bí mật: `password-reset-result.json` ngoài Git. Chưa xác minh người dùng đăng nhập thành công bằng trình duyệt; server/credential QA vẫn được giữ cho lượt kiểm thủ công đang chờ.

### Cập nhật theo xác nhận tiếp theo của người dùng

Yêu cầu tiếp theo xác nhận đã đăng nhập và đối chiếu tổng tiền QA qua ảnh, đồng thời đã có ảnh **Tổng quan mobile với thanh Responsive 390×844**. Nguồn ghi nhận ở lượt này là xác nhận của người dùng; không có tệp ảnh mới đính kèm để trợ lý trực tiếp đối chiếu lại. Đây là cập nhật sau vấn đề đăng nhập ở trên, không phải kết luận từ kiểm HTTP. **Ảnh Tổng quan không chứng minh trang Báo cáo & so sánh tháng đạt**, và số trên thanh Responsive chưa thay thế phép đo `window.innerWidth/innerHeight` trên trang báo cáo.

| Mục | Trạng thái và phạm vi bằng chứng hiện tại |
|---|---|
| Đăng nhập và tổng QA tháng 10: thu 13.000.000 VND, chi 2.770.000 VND | Người dùng xác nhận qua ảnh; kiểm HTTP/database độc lập cũng khớp |
| Ảnh Tổng quan mobile, thanh 390×844 | Người dùng xác nhận đã có; chỉ áp dụng Tổng quan và kích thước được chọn trên thanh |
| Báo cáo A=09/2026, B=10/2026 tại đúng 390×844 và 1280×900 | Chờ phép đo innerWidth/innerHeight và ảnh đúng trang, từng viewport riêng |
| Bộ chọn tháng, coverage/cảnh báo, bảng/biểu đồ, tên dài, trạng thái trống | Chờ kiểm thủ công trên báo cáo tại các viewport yêu cầu |
| Liên kết giao dịch, phân trang giữ A/B và không tràn ngang toàn trang | Chờ kết quả tương ứng; bằng chứng cũ ở kích thước khác vẫn ghi riêng |
| Bàn phím và thao tác chính khi tắt JavaScript bằng DevTools | Chờ người dùng kiểm; không thay bằng lượt CSP cũ |

Kiểm lại server 8022 còn chạy; tài khoản/mật khẩu QA hiện tại đăng nhập, đọc báo cáo và đăng xuất qua HTTP được. Không thử lại các cách đặt viewport đã thất bại hoặc Edge QA bị chặn. Đang hướng dẫn thủ công từng bước và chờ ảnh/kết quả; server tiếp tục chạy. Không thay mã, không chạy lại suite, không commit/push/deploy và chưa chốt QA giao diện đạt.

### Tiếp tục ngày 01/11/2026

Đã kiểm lại cổng 8022 và chạy kiểm truy cập HTTP trên đúng SQLite QA nêu trên: đăng nhập `qa22_a`, mở báo cáo A=09/2026/B=10/2026 với tổng thu/chi tháng B tương ứng 13.000.000/2.770.000 VND, rồi đăng xuất phiên kiểm của script đều thành công. Không sửa dữ liệu nghiệp vụ hoặc mã ứng dụng; không chạy lại suite. Chưa nhận ảnh/phép đo mới của chính trang báo cáo, nên bảng trạng thái đang chờ ở trên giữ nguyên.

Ngày Việt Nam hiện là 01/11/2026: **tháng B=10/2026 đã kết thúc**, không còn là tháng đang diễn ra và giao dịch ngày 31/10 không còn là tương lai. Coverage tháng B vẫn chưa xác nhận; tháng đã kết thúc không tự trở thành đầy đủ. Đây là thay đổi theo ngày thực, không giả lập thời gian hoặc thay dữ liệu để làm ảnh QA. Trường hợp cảnh báo tháng đang diễn ra/ngày tương lai chưa được kiểm lại ở viewport yêu cầu bằng bộ dữ liệu này.

Tiếp tục hướng dẫn người dùng kiểm mobile trước, chờ kết quả `window.innerWidth/innerHeight` và ảnh báo cáo, sau đó mới xác nhận các mục tương ứng và chuyển sang desktop/bàn phím/tắt JavaScript. Không thử lại công cụ viewport đã thất bại hoặc Edge QA. Server và credential QA vẫn được giữ vì lượt thủ công chưa kết thúc; chưa commit/push/deploy.

## Tổng hợp QA thủ công và chuẩn bị bàn giao — 01/11/2026

Đây là trạng thái cập nhật sau các bước hỗ trợ ở trên; các đoạn “đang chờ” trước đó là biên bản theo thời điểm, không phủ nhận bằng chứng mới dưới đây. Nguồn bổ sung là **người dùng tổng hợp kết quả đã quan sát qua ảnh và thao tác trực tiếp** trong yêu cầu bàn giao. Không có tệp ảnh mới đính kèm ở lượt tổng hợp này để trợ lý tự đối chiếu lại; không bịa tên tệp/đường dẫn ảnh. Các ảnh chẩn đoán từ công cụ cũ vẫn là ảnh sai viewport, không được đổi thành bằng chứng đạt.

| Mục kiểm | Kết quả và nguồn bằng chứng | Giới hạn còn lại |
|---|---|---|
| Đăng nhập và số liệu QA | Người dùng xác nhận qua ảnh; HTTP/database kiểm độc lập cũng khớp tháng B thu **13.000.000 VND**, chi **2.770.000 VND** | Chỉ QA mô phỏng, không phải online |
| Xem đúng báo cáo A=09/2026, B=10/2026 | Người dùng xác nhận đã xem **trang báo cáo** qua ảnh ở Responsive **390×844** và **1280×900** | Chưa có kết quả `window.innerWidth/innerHeight` trên báo cáo ở cả hai khung; không gọi đây là hai viewport nội dung đã đo chính xác |
| Ảnh Tổng quan mobile | Đã ghi nhận ảnh Tổng quan với thanh 390×844 theo xác nhận của người dùng | Không dùng ảnh Tổng quan thay bằng chứng của báo cáo |
| Bảng so sánh mobile | Người dùng xác nhận bảng cuộn ngang trong vùng riêng và đọc được cột chênh lệch/tỷ lệ | Chưa có kiểm đo tràn ngang toàn trang tại hai viewport nội dung chính xác |
| Liên kết danh mục | Người dùng xác nhận mở đúng tháng, loại và tổng tiền | Không mở rộng kết luận sang mọi tổ hợp bộ lọc chưa thử thủ công |
| Quay về báo cáo | Người dùng xác nhận giữ đúng A/B | Phân trang được đối chiếu riêng ở hàng dưới |
| Enter trên bộ chọn | Người dùng xác nhận nhấn Enter mở báo cáo được | Không tương đương đã kiểm toàn bộ thứ tự Tab, focus-visible hoặc không mắc kẹt bàn phím |
| Sau Disable JavaScript | Người dùng xác nhận đã thực hiện bước Disable JavaScript rồi tải lại/mở liên kết | Chỉ ghi nhận chuỗi thao tác này; chưa có bằng chứng trạng thái tắt JS cùng kết quả của mọi form/menu/liên kết. Không tuyên bố toàn bộ chức năng đã đạt khi tắt JavaScript; không dùng lượt CSP cũ thay thế |
| Phân trang và giữ A/B | Lượt trình duyệt QA trước đã quan sát Ăn uống tháng B có **23 giao dịch**, trang 2 có **3 dòng**, quay lại giữ 09/2026–10/2026; kiểm thử tự động cũng kiểm việc giữ cặp tháng | Bằng chứng trước ở kích thước khác; chưa có xác nhận thủ công mới tại đúng hai viewport nội dung yêu cầu |
| Focus và bàn phím khác | Lượt công cụ trước có focus-visible/ArrowRight trong vùng bảng và Enter mở/đóng menu; Enter mở báo cáo có xác nhận mới ở trên | Chưa có lượt Tab/Shift+Tab và kiểm focus đầy đủ tại đúng hai viewport nội dung yêu cầu |
| Coverage, tên dài, biểu đồ, tháng trống | Lượt trình duyệt trước quan sát coverage A đầy đủ/B chưa xác nhận, tên dài, biểu đồ/bảng, A=B và tháng 08/2026 trống; kiểm thử tự động bao phủ dữ liệu tương ứng | Xem ảnh báo cáo hai kích thước chưa phải xác nhận riêng từng chi tiết. Các mục này còn cần checklist/ảnh cụ thể nếu yêu cầu nghiệm thu từng mục tại đúng viewport |
| Cảnh báo tháng đang diễn ra/ngày tương lai | Có kiểm thử tự động và quan sát lượt 30/10 trong dữ liệu QA | Ngày hiện tại 01/11: B=10/2026 đã kết thúc, bản ghi 31/10 không còn là tương lai; chưa kiểm lại trực quan trường hợp này ở viewport yêu cầu |

### Điều kiện nghiệm thu còn thiếu

1. Kết quả đo `window.innerWidth/innerHeight` trên **chính báo cáo đã tải** ở cả 390×844 và 1280×900; không dùng số trên thanh Responsive hoặc ảnh Tổng quan thay cho phép đo.
2. Xác nhận tại các viewport đó cho phân trang giữ A/B, focus/thứ tự Tab, không tràn ngang toàn trang và các chi tiết coverage/biểu đồ/tên dài/trạng thái trống nếu đây là tiêu chí nghiệm thu bắt buộc. Bằng chứng QA cũ và kiểm thử tự động vẫn có giá trị riêng, không tự nâng thành đã kiểm đủ tại hai khung.
3. Với chế độ không JavaScript, cần kết quả cụ thể của những thao tác còn lại nếu muốn kết luận rộng hơn chuỗi Disable JavaScript → tải lại/mở liên kết đã được người dùng xác nhận. Chưa kiểm toàn bộ chức năng khi tắt JS, thiết bị vật lý, browser khác hoặc production.

Không có lỗi ứng dụng mới được tái hiện từ phản hồi tổng hợp, không sửa mã hoặc chạy lại suite. Giữ số kiểm thử đúng như phần kỹ thuật: **458 bài PostgreSQL duy nhất (451 đạt lượt đầu, 7 lỗi cookie QA rồi chạy lại đúng 7 đều đạt)**; 58 PostgreSQL là tập con; lượt 58 SQLite ghi riêng; JavaScript **43/43**. **2 truy vấn** chỉ là phần tổng hợp, chưa đo toàn trang.

Lượt tổng hợp kết thúc kiểm thủ công hiện tại để chuẩn bị bàn giao. Không chốt QA hoàn chỉnh, không commit/push/deploy, không truy cập production/database thật hoặc thử lại Edge QA.

### Dọn phiên QA và rà diff thực tế

- Đã dừng đúng các tiến trình Python chạy `serve_qa.py` của thư mục QA này; kiểm kết nối `127.0.0.1:8022` trả **False**, cổng đã đóng. Không dừng server khác.
- Đã hủy session trong **SQLite QA** (còn 0) và xóa hai tệp credential tạm `credentials.json`, `qa22_a-password.txt` ngoài repository. Các lệnh clipboard cũ không còn dùng được; muốn kiểm tiếp cần chuẩn bị credential QA mới. Không xóa fixture/bằng chứng và không sửa dữ liệu thật.
- Hash nội dung **19 model finance QA** khớp bản trước lượt kiểm thủ công. Hash **14 tệp TASK 22A còn lại** giữ nguyên; chỉ tài liệu này được cập nhật trong các lượt hỗ trợ thủ công. Không có sửa mã cần chạy lại suite.
- Rà diff/whitespace và phạm vi vẫn đúng **15 tệp TASK 22A**, index trống. Quét các tệp được theo dõi và tệp không bị ignore tìm giá trị credential QA thực tế, mẫu token/private key và credential trong URL: không có phát hiện bí mật cần xử lý. Ba tệp kiểm thử cũ có URL credential giả được đối chiếu là fixture chủ động kiểm lỗi/redaction và nội dung không đổi so với HEAD; không sửa hoặc đưa credential thật vào các tệp đó.
- Không stage dữ liệu, ảnh, database, credential hoặc cấu hình QA. Biên bản dọn không chứa bí mật: `D:\POSTGRESQL QA\task22a-manual-20261031-162552\manual-qa-close-report.json` (tham chiếu local ngoài Git). Chưa commit/push/deploy; những điều kiện nghiệm thu còn thiếu được giữ rõ ở trên.

## Khép các mục còn thiếu: kết luận về giới hạn công cụ — 01/11/2026

Đã đọc lại và giữ nguyên bằng chứng trình duyệt cũ cùng các xác nhận thủ công ở bảng tổng hợp; **không yêu cầu người dùng chụp lại phần đã xác nhận**. Lượt này kiểm kê khả năng công cụ hiện tại, không phải một lượt kiểm giao diện mới.

- Inventory chỉ có **in-app browser (iab)** và **MCP Apps**; MCP Apps không phải browser QA thay thế. API browser iab công bố `visibility`, `viewport`; API tab công bố `pageAssets`, `webmcp`. Không có API được công bố để tắt JavaScript trước điều hướng/tải trang. Đã kiểm trên tab trắng tạm và đóng tab; không dùng tab trắng làm bằng chứng kích thước báo cáo.
- API viewport vẫn là cơ chế đã cho phép đo sai trên trang tải xong trong lượt trước. Không có cách mới được xác minh để xử lý; không lặp lại set viewport/zoom/reset hoặc hiệu chỉnh kích thước bằng thử nhiều lần, không thử lại Edge bị chặn và không gọi API ngoài tài liệu để vượt giới hạn.
- Vì chưa có đường kiểm đáp ứng yêu cầu, **không khởi động lại server, không tạo credential hoặc dữ liệu mới chỉ để lặp thử nghiệm đã thất bại**. Không dùng CSP để thay thế JavaScript bị tắt trước khi tải.

### Phép đo và thao tác còn chưa xác minh

| Kích thước yêu cầu trên báo cáo | innerWidth / innerHeight | documentElement.clientWidth / scrollWidth | Tràn ngang toàn trang, bảng cuộn riêng, Tab/Shift+Tab/focus và Enter | Phân trang giữ A/B/bộ lọc |
|---|---|---|---|---|
| 390×844 | **Chưa có phép đo đúng kích thước yêu cầu**; không đo mới trong lượt này | Chưa có phép đo gắn với viewport báo cáo đúng 390×844 | Bảng cuộn riêng và Enter đã có xác nhận thủ công; kiểm toàn bộ các mục tại viewport nội dung được đo chính xác còn thiếu | Có bằng chứng QA cũ với 23 giao dịch/3 dòng ở trang 2; chưa kiểm mới tại viewport nội dung đúng 390×844 |
| 1280×900 | **Chưa có phép đo đúng kích thước yêu cầu**; không đo mới trong lượt này | Chưa có phép đo gắn với viewport báo cáo đúng 1280×900 | Có ảnh báo cáo theo xác nhận của người dùng; chưa đủ phép đo/focus/overflow tại viewport nội dung đúng kích thước | Bằng chứng QA cũ và kiểm thử vẫn giữ riêng; chưa kiểm mới tại viewport nội dung đúng 1280×900 |

Dữ liệu QA cũ đã có đủ trang thứ hai; việc chưa khép phân trang không phải do fixture thiếu mục. Các số đo sai viewport ở phần biên bản trước giữ đúng là kết quả cũ, không đổi tên thành phép đo đạt hoặc kết quả mới.

| JavaScript tắt **trước khi tải trang** | Phạm vi bằng chứng còn lại |
|---|---|
| Chọn A/B rồi gửi form | Chưa có lượt công cụ thực hiện được điều kiện JavaScript-off trước tải và xác minh riêng thao tác này. Enter/form có bằng chứng riêng, không tự gộp thành kiểm no-JS đạt |
| Đọc bảng | Có ảnh bảng và kiểm cuộn thủ công, nhưng chưa đủ bằng chứng gắn riêng với trạng thái JavaScript-off trước tải |
| Mở giao dịch liên quan | Người dùng xác nhận chuỗi Disable JavaScript → tải lại/mở liên kết; giữ nguyên mức bằng chứng này, không suy rộng sang toàn bộ luồng |
| Chuyển trang rồi quay về giữ A/B | Quay về giữ A/B và phân trang có bằng chứng độc lập như trên; chưa có kiểm chứng toàn chuỗi với JavaScript-off trước tải |

**Kết luận: còn các mục cụ thể chưa xác minh, chưa đủ bằng chứng để chốt toàn bộ điều kiện QA bổ sung.** Lý do là thiếu API JavaScript-off và cơ chế viewport hiện có đã thất bại; không có lỗi ứng dụng mới được tái hiện từ lượt kiểm kê này. Không sửa CSS bù cho kích thước công cụ, không sửa mã hoặc chạy lại suite, không stage/commit/push/deploy.

Đã kiểm sau lượt này: cổng 8022 đóng; SQLite QA riêng còn **0 session**, hai tệp credential tạm vẫn không tồn tại; không phát sinh server/credential mới. Hash 14 tệp ngoài tài liệu này giữ nguyên so với đầu lượt thủ công; phạm vi vẫn đúng 15 tệp, index trống. Rà mẫu token/private key/URL chứa credential trong 15 tệp task không có phát hiện; không mở database thật hoặc kết nối production. Biên bản kiểm kê/dọn: `D:\POSTGRESQL QA\task22a-manual-20261031-162552\capability-review-20261101.json`, chỉ là tham chiếu local ngoài Git. Các giới hạn được giữ lại để bàn giao minh bạch; không tiếp tục vòng thử công cụ hoặc yêu cầu chụp lại bằng chứng đã có.

## Chấp nhận bàn giao với giới hạn đã công bố — 01/11/2026

Người dùng đã chấp nhận bàn giao theo các bằng chứng hiện có và cho phép commit/push mã, kiểm thử, tài liệu TASK 22A lên `main`, không force-push. Quyết định này **không bổ sung bằng chứng QA** và không chuyển bất kỳ mục “Chưa xác minh” nào thành đạt. Các bảng bằng chứng/giới hạn ở trên được giữ nguyên; giới hạn công cụ không bị gọi thành lỗi ứng dụng đã tái hiện.

Lượt chốt chỉ rà diff/bí mật và cập nhật tài liệu quyết định bàn giao; không sửa mã ứng dụng hoặc chạy lại suite. Kết quả vẫn là **458 bài PostgreSQL duy nhất: 451 đạt lượt đầu, 7 lỗi cookie QA rồi chạy lại đúng 7 đều đạt**. Nhóm 58 PostgreSQL thuộc 458; lượt 58 SQLite được ghi riêng, không cộng thành tổng bài duy nhất mới; JavaScript **43/43**. Con số **2 truy vấn** chỉ thuộc phần tổng hợp đã đo, không phải toàn trang.

Chỉ đưa 15 tệp mã/kiểm thử/tài liệu TASK 22A vào commit. Không đưa database, model/dataset, credential, cấu hình hoặc bằng chứng QA riêng tư vào Git; không đổi schema, dependency hoặc quyền repository. Push có thể kích hoạt Render auto-deploy theo cấu hình đã có; không thao tác trực tiếp production, không chạy migration hoặc coi auto-deploy là bằng chứng online mới. Server/credential QA đã dọn theo biên bản trước.

## TASK 22B — Xác nhận thủ công bổ sung cho mốc demo, 01/11/2026

Người dùng xác nhận đã kiểm luồng **Báo cáo tháng A=09/2026, B=10/2026 → mở danh mục Ăn uống → quay về giữ đúng A/B**. Tổng tháng 10 được người dùng xác nhận qua ảnh: **thu 500.000 VND, chi 750.000 VND, chênh lệch thu–chi −250.000 VND**.

Đây là **xác nhận thủ công qua ảnh do người dùng cung cấp thông tin**, không phải kiểm thử tự động hoặc lượt trợ lý kiểm lại runtime. Lượt TASK 22B không mở website/database, không có tệp ảnh mới để trợ lý đối chiếu độc lập, không xác minh môi trường hay tài khoản của ảnh. Không suy ra đây là bằng chứng online mới hoặc số liệu thuộc fixture QA cũ có 31 giao dịch. Giữ nguyên tổng QA cũ 13.000.000/2.770.000 VND ở các biên bản trước; hai bộ số liệu không được thay thế hoặc gộp thành một phép kiểm.

Xác nhận này bổ sung bằng chứng cho luồng mở danh mục/quay về và các số hiển thị nêu trên; **không khép** các mục viewport nội dung, overflow, focus/Tab, phân trang tại đúng hai kích thước hoặc phạm vi tắt JavaScript còn thiếu. Các mục đó vẫn **Chưa xác minh** như bảng QA phía trên. Không ghi QA hoàn tất toàn bộ hoặc gọi thiếu API công cụ là lỗi ứng dụng.

Checklist chuẩn bị mốc demo và danh sách dữ liệu mô phỏng cần chuẩn bị được bổ sung ngay trong [kịch bản bảo vệ hiện có, mục 6](thesis-demo-script.md#6-checklist-chuẩn-bị-mốc-demo--task-22b), không tạo tài liệu demo trùng. TASK 22B chỉ sửa tài liệu trên nhánh main, từ commit nền `c16457fd2bbc707aa2ccdf1d15a700bcff5675f6`, working tree sạch lúc bắt đầu; không chạy lại suite ứng dụng, không tạo dữ liệu/tài khoản hoặc khởi động server. Chưa commit/push/deploy TASK 22B.
