# TASK 21A — Kiểm thử hành trình và chuẩn bị dùng thử

Kiểm chứng **29/10/2026**, dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`. Mã kiểm tra: **main, `d01a9282516ac110fd587457d14da2ef65720eef`**. Working tree sạch khi bắt đầu; không tìm thấy AGENTS.md ở repository hoặc thư mục cha trực tiếp. Đã đọc README, luồng/model/template liên quan và tài liệu nhập nhanh, ML/phản hồi, CSV, định kỳ, ngân sách, tiết kiệm, coverage/dự báo, báo cáo và lịch. Không dùng sự tồn tại tài liệu làm bằng chứng chức năng chạy được.

## Môi trường và giới hạn dữ liệu

- QA mới: **`D:\POSTGRESQL QA\task21a-20261029`**, SQLite **`qa.sqlite3`**, website chỉ **127.0.0.1:8024**, Waitress 4 thread/WhiteNoise. Cấu hình từ `config.base`, không nạp config.local, config.production hoặc URL Render.
- Chặn mỗi lần mở kết nối: chỉ cho database SQLite đúng đường dẫn QA hoặc test memory. Các biến kết nối PostgreSQL bị bỏ khỏi tiến trình quản lý/server; không in giá trị biến môi trường. Thư mục QA giới hạn quyền Windows cho người hiện tại và SYSTEM; không nằm trong repository/static/public.
- Áp dụng các migration hiện có đến **0014** vào QA mới; không migrate SQLite thật/production. Không khởi động hoặc kết nối PostgreSQL trong TASK 21A.
- Hai tài khoản ngẫu nhiên A/B, do task đăng ký qua trình duyệt; không dùng tài khoản/credential thật. Mọi giao dịch là mô phỏng. Dùng ngày Việt Nam thực tế **29/10/2026**, không đổi đồng hồ server; ba tháng lịch sử giả 07–09/2026 được tạo riêng để kiểm coverage/dự báo.
- Runtime QA đã có: **Python 3.13.16, Django 5.2.18, scikit-learn 1.9.1, numpy 2.5.4, pandas 3.0.6, Waitress 3.0.2, WhiteNoise 6.12.0**. Không cài/nâng cấp thư viện. Hai artifact EN/VI cấu hình phía server được giữ nguyên; inference thật có hash kiểm trong dịch vụ và đối chiếu snapshot phản hồi. Không dùng adapter DLL/launcher CLI trong server.
- Edge Chromium headless, **1280×900 / 390×844**, locale vi-VN, timezone Asia/Ho_Chi_Minh; có context tắt JavaScript. Đây là viewport trình duyệt, **không phải thiết bị điện thoại vật lý**.

## Bảng hành trình: mong đợi, thực tế, bằng chứng

Các tên A/B và nội dung bên dưới chỉ là định danh QA; không công bố tên đăng nhập hoặc mật khẩu. Tất cả đường dẫn bằng chứng ở thư mục QA nêu trên, ngoài Git.

| Kịch bản | Kết quả mong đợi | Kết quả thực tế | Bằng chứng |
|---|---|---|---|
| Đăng ký → trang cần đăng nhập | Tạo tài khoản, chuyển Đăng nhập và giữ khách | Cả A/B đăng ký thành công; sau đăng ký vào Giao dịch vẫn bị yêu cầu đăng nhập; chưa có giao dịch | `journey-phase1.json`, `journey1.js` |
| Đăng nhập/đăng xuất | Truy cập đúng sau login, logout mất quyền | Đạt, gồm login lại; `next` giữ trang được yêu cầu | Phase 1 |
| Tài khoản mới | Trạng thái trống, không tạo tiền/lịch sử giả | Onboarding và lịch sử dự báo trống; không ForecastHistory trước chủ động tính | `desktop-empty-history-a.png`, `desktop-empty-history-b.png` |
| Danh mục | Tự tạo Thu/Chi hoặc chủ động thêm mẫu; chưa ánh xạ vẫn dùng | Tạo 2 danh mục thủ công, thêm đủ 11 mẫu qua xác nhận. Chi chưa ánh xạ lưu giao dịch được, không tự đổi nhãn | Phase 1 |
| CRUD / HTML | Sửa đúng bản ghi, xóa cần POST, escape mô tả | Tạo 50.000 → sửa 55.000 VND; mô tả `<script>` hiện chữ, không chạy mã; GET xóa không xóa | Phase 1 |
| Giao dịch tương tự | GET chỉ điền, lưu ID mới, nguồn giữ nguyên | Đạt; date hôm nay Việt Nam, cùng receipt gửi lại chỉ có một bản mới. Đã xóa bản thử bằng xác nhận riêng | Phase 1 |
| Lỗi tiền/form | Server từ chối, giữ dữ liệu, có thể sửa | `50.00` bị từ chối, mô tả/tiền sai còn trên form, nút không kẹt. Không JS: 0 bị từ chối rồi sửa được | `desktop-validation-keeps-fields.png`, Phase 1/4 |
| Nhập nhanh | Phân tích chưa lưu; cần xác nhận thay thế | Hủy giữ form cũ; Xác nhận thay bằng khoản học phí 450.000 VND, đúng ngày, chưa chọn danh mục; không tăng Transaction | Phase 2 |
| Gợi ý VI/EN → Apply → Lưu | Artifact thật, chỉ áp dụng/lưu sau thao tác | Cả hai cho Education trên hai câu giả. Danh mục vẫn trống khi chỉ nhận gợi ý; Apply chưa tạo giao dịch; Lưu mới tạo đúng 2 phản hồi applied/same_label | `desktop-ml-applied-not-saved.png`, `mobile-feedback.png`, Phase 2, `final-verification.json` |
| Đổi đầu vào ML | Gợi ý cũ mất hiệu lực | Đổi mô tả, loại hoặc VI/EN xóa receipt trên form; backend receipt/quyền/CSRF còn được kiểm trong suite | Phase 2, hồi quy Django/JS |
| CSV lỗi | Chỉ rõ dòng, không nhập một phần | Sai ngày dòng 2, tiền âm dòng 3; không có nút xác nhận/Transaction mới | `desktop-csv-line-errors.png`, Phase 2 |
| CSV BOM/xem trước/xác nhận | Preview chưa ghi; đúng số dòng/Decimal | Tệp UTF-8 BOM với đuôi/MIME không quyết định nội dung, 23 khoản chi, **276.000 VND**. Xác nhận thêm đủ 23; POST lại trả **409**, không thêm; tải cùng hash bị chặn | Phase 2, `synthetic-import.csv` riêng tư |
| Tìm/lọc/phân trang/xuất | Tổng trên toàn bộ lọc; xuất hết | Kết hợp q/kind/category/tháng được 23, trang 20+3; tìm hoa/thường và khoảng ngày đúng ngày biên. Tổng 276.000 ở cả hai trang. Xuất BOM đủ 23 dòng dữ liệu, Decimal khớp; bộ lọc lỗi không cho xuất | `mobile-filtered-page2.png`, `synthetic-export.csv`, Phase 2, kiểm cuối |
| Ngân sách | Dùng chi thực tế, không dự kiến | Tổng 500.000 VND; lúc kiểm cuối chi 1.176.000, vượt 676.000 VND, tỷ lệ 235,20%, thanh giới hạn 100% | `mobile-budget.png`, kiểm cuối |
| Tiết kiệm | Phân bổ không phải thu/chi | Mục tiêu 1.000.000; đóng góp 200.000, rút 50.000, tích lũy 150.000; tổng tài chính không đổi | Phase 2, kiểm cuối |
| Định kỳ | Khai báo chưa ghi; record/skip có xác nhận | 3 quy tắc 300.000 VND chỉ là dự kiến. Một kỳ hạn 01/10 ghi ngày thực tế 29/10, **275.000**; POST lặp không thêm; kỳ khác bỏ qua không tạo Transaction/phản hồi ML | `desktop-recurring-pending.png`, Phase 2/3 |
| Lịch | Không cộng trùng, tách dự kiến, GET chỉ đọc | Sau xử lý còn 1 dự kiến ngày 31; khoản ghi ngày 29 chỉ hiện như thực tế. Mobile 3 ngày có mục, GET toggle hiện 31 và giữ tháng/chế độ khi xem ngày | `desktop-calendar.png`, `mobile-calendar-all-days.png`, Phase 3/4 |
| Tổng quan/báo cáo | Tổng/cơ cấu và toàn bộ chi tiết khớp | 28 giao dịch tháng 10: thu **5.000.000**, chi **1.176.000**, chênh lệch **3.824.000 VND**. Hai cơ cấu 606.000 + 570.000 khớp tổng chi; báo cáo đủ 28 hàng, giữ cảnh báo chưa đầy đủ/tháng chưa kết thúc | `desktop-dashboard.png`, `desktop-report.png`, kiểm cuối |
| In/PDF | Chỉ gọi in khi bấm, giữ cột/dòng/cảnh báo | Click gọi hàm print (dùng stub kiểm lời gọi trong QA); Chromium xuất A4 2 trang, đã render/xem cả hai: không mất cột, trang trắng hoặc hàng bị cắt. Header bảng lặp trang 2, đủ 23 mô tả CSV đúng một lần, tổng khớp | `synthetic-monthly-report.pdf`, `pdf-page-1.png`, `pdf-page-2.png`, `pdf-check.json` |
| Dự báo thiếu lịch sử | Không tạo ước tính/lịch sử giả | Tài khoản mới không có nút Tính. Hai tháng xác nhận vẫn chưa tính được | Phase 3 |
| Coverage/dự báo đủ 3 tháng | Chỉ tháng đã kết thúc/liên tiếp/đầy đủ | QA tạo chi 100.000/200.000/300.000 trong 07–09/2026, xác nhận qua UI. POST tính **200.000** cho 10/2026; tính lại cùng fingerprint không thêm lịch sử | `desktop-forecast-three-months.png`, Phase 3 |
| Sửa lịch sử → vô hiệu → tính lại | Reset coverage, ẩn cache cũ, giữ snapshot | Sửa tháng 09 thành 330.000: tháng về unknown, không hiện tiền cũ. Xác nhận lại → **210.000**, hai snapshot 200.000/210.000. Tháng 10 chưa kết thúc nên số tháng đối chiếu **0**, MAE chưa có | Phase 3, kiểm cuối |
| Demo | Mô phỏng rõ, không ghi tài khoản | Chạy thật baseline/Ridge bằng POST. Chọn **Ước tính theo trung bình 3 tháng**, không ép Ridge; mục tiêu minh họa 01/2026. Hash/số dòng 19 bảng finance giữ nguyên | `mobile-demo.png`, `demo-selection-and-final-ui.json`, Phase 3 |
| Tách A/B / CSRF | Không đọc/sửa dữ liệu nhau | B thấy báo cáo rỗng dù thêm user_id=A; URL giao dịch/CSV/mục tiêu/định kỳ của A trả 404; feedback/lịch sử riêng. POST không CSRF bị 403 | Phase 1/3, suite CSRF |
| Không JS / bàn phím | Luồng server dùng được, không kẹt | Space/Enter cho menu, skip link tới main, checkbox ngày trống; nhập/sửa/xóa thường và CSV preview/confirm hoạt động; lọc/pager giữ điều kiện; báo cáo đọc được, Ctrl+P là cách in không JS | `mobile-nojs-detail-long.png`, `mobile-nojs-calendar.png`, `mobile-nojs-report.png`, Phase 4 |
| Back/Forward / lưu cục bộ | Nút dùng lại được, không giữ gợi ý cũ | Các nút phân tích/gợi ý/lưu sẵn sàng sau Back; receipt rỗng; không ghi mô tả vào localStorage | Phase 4, suite JS |
| GET không sửa nghiệp vụ | Không tạo kỳ/Transaction/coverage/forecast | Đối chiếu nội dung cả 19 bảng và SQL trên 17 trang GET: không lệnh ghi. Browser kiểm GET lịch/form tương tự/preview/demo riêng | `final-verification.json`, `final-finance-hashes.json` |

PDF trên được tạo **trước khi thêm ba tháng lịch sử QA**; so sánh tháng trước phản ánh dữ liệu tại thời điểm in. Báo cáo đang sống, không phải snapshot trong hệ thống. Trong bước không JS sau đó, task tạo/sửa/xóa khoản tạm và nhập/xóa 1 dòng CSV qua UI, khôi phục tổng tháng về đúng 28 giao dịch trên. Các thao tác vẫn tăng phiên bản dữ liệu: kết quả 210.000 trở nên lỗi thời, UI cuối **không hiển thị như còn hiệu lực**, hai snapshot lịch sử vẫn giữ nguyên. Đây là hành vi đúng, không sửa cache/coverage để làm kết quả đẹp.

## Kiểm thử và lệnh đã chạy

Python QA sử dụng `D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe`; không dùng .venv để trỏ database thật. Các script/cấu hình QA ở thư mục ngoài Git; credential đã dọn sau kiểm tra, cần tạo lại cấu hình QA độc lập nếu lặp toàn hành trình. Các lệnh dưới ghi lại lượt đã thực hiện, không phải hướng dẫn chạy vào local thật.

```powershell
$pyQA = 'D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe'
$manageQA = 'D:\POSTGRESQL QA\task21a-20261029\manage_qa.py'
& $pyQA -X utf8 $manageQA test finance --verbosity 2
# Sau khi chỉnh riêng tên cookie ở profile unit test, chạy lại đúng 7 bài bên dưới:
$csrfCases = @(
  'finance.test_account_management.AccountManagementTests.test_csrf_action_security_and_no_passwords_in_redirect',
  'finance.test_classification.SuggestionEndpointTests.test_auth_post_only_csrf_and_length',
  'finance.test_csv_import.CsvImportTests.test_auth_csrf_post_only_and_html_escape',
  'finance.test_forecast.ForecastIntegrationTests.test_login_csrf_and_get_never_trains',
  'finance.test_forecast_demo.DemoWebTests.test_get_auth_and_post_csrf',
  'finance.test_quick_entry.QuickEndpointTests.test_post_login_csrf_and_no_cache',
  'finance.test_vietnamese_classification.ModeEndpointTests.test_empty_zero_and_security_both_modes'
)
& $pyQA -X utf8 $manageQA test $csrfCases --settings qa21a_test_settings --verbosity 2
$jsCases = Get-ChildItem -LiteralPath scripts -Filter 'test_*.js' | Select-Object -ExpandProperty FullName
node --test $jsCases
& $pyQA -X utf8 $manageQA check
& $pyQA -X utf8 $manageQA makemigrations --check --dry-run
& $pyQA -X utf8 'D:\POSTGRESQL QA\task21a-20261029\collectstatic_qa.py'
# UI: node <QA_ROOT>\journey1.js, journey2.js + journey2_resume.js, journey3.js, journey4.js
```

| Nhóm | Kết quả cuối và cách đếm | Bằng chứng |
|---|---|---|
| Django | **441 bài duy nhất được kiểm**: lượt đầu 434 đạt, 7 lỗi cookie QA; chạy lại đúng 7 bài đạt với profile tên cookie chuẩn. Không skip. Không báo đây là một lượt 441/441 sạch hoặc cộng thành 448 bài | `django-regression.log` (108,537 giây), `django-cookie-profile-recheck.log` (6,575 giây) |
| JavaScript | **43/43**, không skip; nhóm riêng, không cộng với Django thành độ phủ nghiệp vụ | `javascript.log` |
| Browser | 26 nhóm kiểm hành trình ở 4 phase; là kịch bản tích hợp nhiều bước, **không cộng vào số unit test** | `journey-phase1.json` … `journey-phase4.json` |
| Django check / schema | **0 issues**, **No changes detected** | `system-check.log`, `migration-check.log` |
| Production QA static | **11 copied / 22 postprocessed**; manifest/URL hash/gzip 11 CSS/JS/icon, chặn mọi kết nối database | `handoff-static-report.json`, `handoff-collectstatic.log` |
| Bảo toàn | SQLite QA integrity=ok, không vi phạm khóa ngoại. 30 file bảo vệ gồm SQLite thật, hai artifact, dependency và nghiệp vụ giữ SHA-256. Feedback VI/EN khớp hash model đã chốt | `final-verification.json`, `protected-before.json` |

Không thay mã thực thi nên không thêm test hồi quy chỉ để kiểm tên CSS hoặc tài liệu, không chạy lại các thí nghiệm nghiên cứu. Suite có các bài ranh giới UTC sang ngày Việt Nam, stale receipt, rollback, lựa chọn phương pháp và chống trùng cũ; không coi browser đã thao tác hết mọi tổ hợp đó.

## Phát hiện và xử lý

**Chưa phát hiện lỗi ứng dụng tái hiện được trong các luồng đã thử; không sửa mã chạy, schema/model/dependency.** Chuẩn hóa README thành hướng dẫn tự khởi động local, bỏ mô tả cũ khiến người mới có thể hiểu rằng server luôn đang mở hoặc tình trạng triển khai online đã được xác nhận trong task này. Thêm liên kết hướng dẫn dùng thử và biên bản.

Các lỗi của **harness/cấu hình QA**, không báo thành sự cố website/production:

- Bảy bài test cố định tên `csrftoken`; website QA cố ý dùng `qa21a_csrf`. Chỉ override tên cookie ở profile unit test riêng, giữ nguyên middleware/CSRF và cookie riêng của server/browser; kiểm lại 7 bài đạt. Không bỏ bài, nới assert hoặc tắt CSRF.
- Script ban đầu tìm nút “Đăng ký” trong khi UI là “Tạo tài khoản”, rồi giả định login luôn về Tổng quan dù URL có `next=/giao-dich/`. Sửa selector/kỳ vọng của harness và tiếp tục bằng đúng tài khoản QA đã tạo; không sửa luồng website.
- Harness mong POST xác nhận CSV lặp trả 302; thực tế thiết kế trả **409** và không nhập lại. Sửa kỳ vọng, đối chiếu số dòng trước/sau; không coi 409 này là mất dữ liệu hoặc tắt chống trùng.
- Bộ đối chiếu dùng nhầm tên DTO `expense_categories`; đã dùng đúng `category_statistics`, đối chiếu Decimal đạt. Không thay dữ liệu/số tiền ứng dụng để ép khớp.

## Bằng chứng, riêng tư và kết luận

Thư mục **`D:\POSTGRESQL QA\task21a-20261029`** giữ script tái kiểm, JSON kết quả, hash, log, CSV/PDF và ảnh mô phỏng. Ảnh chính đã xem trực quan: `desktop-dashboard.png`, `desktop-ml-applied-not-saved.png`, `mobile-filtered-page2.png`, `mobile-nojs-detail-long.png`, `mobile-nojs-calendar.png`, `mobile-budget.png`, hai `pdf-page-*.png`. Các ảnh khác ghi theo bảng trên và trong `evidence-manifest.json`. Không đưa các file này hoặc cấu hình/credential QA vào Git.

Đã dừng website QA, xác minh cổng **8024 đóng**; xóa credential, cookie session A/B và secret QA tạm. Không khởi động PostgreSQL/Render, không dùng URL production, không mở SQLite thật bằng Django/SQLite; chỉ đọc byte để kiểm SHA-256. Rà diff/bí mật giữ đúng 3 tài liệu mới/sửa: README, hướng dẫn dùng thử và biên bản này. **Tại thời điểm kết thúc QA chưa commit/push/deploy.** Kết quả bảo toàn, dọn và rà nằm ở `final-verification.json`, `shutdown-report.json`, `diff-secret-review.json`, `evidence-manifest.json` ngoài Git.

**Kết luận:** đủ bằng chứng để bắt đầu **dùng thử có kiểm soát trên bản QA đã kiểm**, không thấy lỗi chặn trong phạm vi kịch bản này. Chưa có bằng chứng người dùng ngoài dự án đã tự dùng thành công, chưa gửi lời mời hoặc thu phản hồi thật.

Giới hạn giữ rõ:

- Không truy cập/kiểm giao diện online, không kiểm database production hoặc trạng thái auto-deploy. Cần smoke test riêng trên đúng bản được chọn trước khi mời thử online.
- TASK 21A chỉ dùng SQLite; không kiểm lại concurrency/PostgreSQL/Linux/multiworker, không kiểm tải lớn. Bằng chứng PostgreSQL ở task trước không phải lượt chạy trong task này.
- Chỉ Edge Chromium headless/viewport và mẫu dữ liệu QA. Chưa browser khác, thiết bị vật lý, screen reader hoặc đánh giá WCAG toàn diện.
- PDF do Chromium xuất và render kiểm đủ hai trang; **chưa thao tác hộp thoại Save as PDF thủ công, chưa mở Excel thật**. Chưa khẳng định mọi browser/printer xử lý giống nhau.
- Không có kiểm cắt mạng/timeout thực tế trong TASK 21A; suite JS có lỗi giả lập. Không biến kết quả giả lập hoặc lỗi harness thành báo cáo sự cố production.
- Cá nhân chỉ thử trực tiếp mức 3 tháng/trung bình, không dựng thêm 36 tháng để trình diễn ML cá nhân. Nhánh Ridge/selection được kiểm qua suite và demo thật; demo không phải bằng chứng dự báo ngoài đời. MAE thực tế chưa có tháng đủ điều kiện.
- Đây là kiểm hành trình theo mẫu, không chứng minh không còn lỗi, bảo mật toàn diện hoặc độ chính xác thực tế của ML. Hướng dẫn dùng thử không thu bí mật/dữ liệu tài chính nhạy cảm và không tự gửi tin nhắn.

## Chốt bàn giao tài liệu — 29/10/2026

Theo yêu cầu tiếp theo, chỉ rà/stage **README.md, docs/user-trial-guide.md, docs/user-journey-qa.md**. Đối chiếu tên nút và bộ danh mục mẫu với template/mã hiện tại; ghi đúng “Tạo tài khoản”, “Áp dụng danh mục đã chọn” và “Lưu giao dịch”. Làm rõ kiểm lời gọi print bằng stub, không coi là đã thử hộp thoại in thủ công.

Giữ nguyên cách đếm **441 bài Django duy nhất: 434 đạt lượt đầu, 7 lỗi cấu hình cookie QA rồi chạy lại đúng 7 bài đều đạt**; JavaScript **43/43**. Không mô tả toàn bộ Django đạt trong một lượt, không cộng trùng và không chạy lại kiểm thử vì bước bàn giao chỉ chỉnh tài liệu. Giữ rõ **chưa chạy lại PostgreSQL, chưa kiểm online hoặc điện thoại vật lý** trong TASK 21A.

Rà bí mật và danh sách file; không đưa credential, database, cấu hình QA, CSV/PDF/ảnh/log riêng hoặc bằng chứng nhạy cảm vào Git. Không đổi mã ứng dụng, dữ liệu, model ML hoặc dependency; không truy cập production. Commit/push bình thường lên main theo yêu cầu, không force-push; xác minh SHA local/remote và working tree sau push, báo trong tin nhắn bàn giao. Việc push không phải bằng chứng website online đã được kiểm.
