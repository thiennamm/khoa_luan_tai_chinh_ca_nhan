# TASK 19B — Báo cáo thu–chi tháng và chế độ in

Kiểm chứng ngày 27/10/2026, giờ Việt Nam. Làm trên dự án chính. Giữ nguyên thay đổi TASK 19A chưa commit; chưa commit/push/deploy cả hai task.

## Cách dùng

1. Đăng nhập, ở **Tổng quan** chọn tháng rồi bấm **Báo cáo tháng**. Liên kết giữ tháng đang chọn.
2. Ở `/bao-cao-thang/?month=YYYY-MM`, kiểm tra tháng và trạng thái ghi chép. Mặc định không đưa danh sách giao dịch vào báo cáo.
3. Muốn có chi tiết: chọn **Bao gồm toàn bộ giao dịch trong tháng**, bấm **Xem báo cáo**. Bao gồm tất cả kết quả tháng, không chỉ trang 20 dòng; ngày và ID giảm dần.
4. Bấm **In / Lưu PDF** để gọi chức năng in sau thao tác của bạn, chọn **Save as PDF / Lưu dưới dạng PDF**, A4 dọc. Có thể tắt header/footer của trình duyệt nếu không muốn in URL/ngày do trình duyệt thêm. Không cần bật in màu nền để đọc số liệu.
5. Tắt JavaScript: biểu mẫu GET vẫn hoạt động; dùng Ctrl+P/menu In. Nút in được ẩn khi không có JavaScript. Chọn nơi lưu riêng tư, kiểm tra preview trước khi lưu/chia sẻ.

Website không cung cấp endpoint xuất PDF, không tự tải PDF, không gọi API ngoài, không lưu bản báo cáo vào static/public/log. PDF chỉ được tạo bởi trình duyệt theo yêu cầu người dùng. Các công cụ đọc/render PDF trong QA dùng runtime đi kèm Codex, không thêm dependency cho Django.

## Nguồn số liệu và ý nghĩa

- `financial_statistics(user, selected, 6)` là dịch vụ Tổng quan hiện có. Báo cáo lấy tháng cuối và tháng liền trước từ cùng kết quả tổng hợp, dùng lại cơ cấu chi theo ID danh mục, sắp xếp số tiền giảm dần. Không gộp theo tên hoặc viết bản sao phép cộng thu/chi.
- Tiền cộng bằng Decimal; dùng filter `vnd` chung, ví dụ `50.000 VND`, giá trị âm khi chênh lệch âm. Không đổi giá trị database, rounding tiền, CSV hoặc parser nhập nhanh.
- Tỷ trọng chi: số chi danh mục / tổng chi, làm tròn HALF_UP đến 2 số thập phân theo dịch vụ cũ. Tổng số tiền danh mục phải khớp tổng chi; tổng tỷ trọng đã làm tròn có thể lệch nhẹ 100%. Tổng chi bằng 0 không tạo bảng/tỷ trọng giả.
- So sánh từng tổng đã ghi: tháng báo cáo trừ tháng trước. Thu/chi chỉ tính phần trăm nếu tháng trước khác 0; không tính phần trăm cho chênh lệch thu–chi. Không tính bằng mẫu số 0.
- Hiện coverage và ghi chú tháng hiện tại/tương lai cho cả hai tháng. Nếu một tháng chưa được xác nhận đầy đủ hoặc chưa kết thúc, giữ cảnh báo không diễn giải chênh lệch số đã ghi là xu hướng chi tiêu thực tế. Coverage đầy đủ vẫn chỉ là xác nhận của người dùng.
- Tháng trống: **Không có giao dịch được ghi nhận**; không khẳng định không phát sinh thu/chi. Không tự đổi coverage từ unknown sang complete hoặc coi số 0 này là đầu vào hợp lệ cho dự báo.
- Chênh lệch thu–chi không phải số dư ngân hàng hoặc tiền tiết kiệm. Chỉ lấy Transaction đã lưu; SavingsEntry và khoản định kỳ chưa được ghi nhận không cộng vào thu/chi. Không gọi dịch vụ dự báo, fit ML hoặc tạo ForecastHistory.
- Báo cáo có thời điểm tạo theo **Asia/Ho_Chi_Minh**. Nội dung là dữ liệu đang có, không phải snapshot bất biến hoặc chứng từ ngân hàng. Các lần truy vấn không khóa người khác ghi dữ liệu; nếu có thao tác ghi đồng thời, tải lại và kiểm tra báo cáo trước khi in. Chưa kiểm tải lớn hoặc snapshot nhất quán trong môi trường nhiều người ghi đồng thời.

## Tham số, phân quyền và quyền riêng tư

Chỉ GET, yêu cầu đăng nhập. `month` phải có dạng YYYY-MM và là tháng lịch hợp lệ. Không truyền month thì mặc định tháng hiện tại theo giờ Việt Nam; truyền rỗng/sai trả **HTTP 400**, hiển thị lỗi và không tự hiển thị báo cáo tháng khác. Tháng 01/0001 không có tháng trước trong phạm vi ngày được hỗ trợ nên không có bảng so sánh; 12/9999 vẫn xem được.

Các truy vấn giao dịch và coverage đều theo tài khoản đăng nhập; giao dịch còn kiểm category thuộc cùng tài khoản như dịch vụ thống kê hiện có. Không dùng user_id từ query, không truy vấn tài khoản đích tùy ý. Chi tiết lấy đủ tháng bằng queryset riêng, không Paginator/slice/hạn mức ngầm. Danh mục và mô tả được autoescape, xuống dòng và wrap chuỗi dài; không ghép nội dung người dùng vào JavaScript.

Nội dung article/bản in không đưa username, mật khẩu, phản hồi ML hoặc trường nội bộ. Thanh tài khoản của layout màn hình thông thường được ẩn khi in. Response dùng `never_cache` (private, no-store), không tạo tệp/cache báo cáo trên máy chủ. Log mới không được bổ sung mô tả/danh mục; query chỉ chứa tháng và lựa chọn chi tiết. GET báo cáo không tạo/sửa bất kỳ model nghiệp vụ nào.

## CSS in và kiểm trực quan

`monthly-report.css` chỉ được tải trên trang báo cáo, qua block styles mới trong base. A4 dọc, lề 14/12/16 mm; ẩn sidebar/topbar/menu, thông báo layout, form, nút và hướng dẫn thao tác. Giữ tiêu đề, thời điểm, VND, coverage, cảnh báo và nguồn số liệu. Bảng trở về toàn chiều rộng vùng in, tiêu đề bảng lặp lại, hàng tránh tách trang khi có thể. Không cắt/ellipsis nội dung dài; số tiền và tên/mô tả được wrap.

Đã phát hiện và sửa trong QA: layout `.app-shell` có `min-height:100vh` gây một trang trắng sau báo cáo ngắn; chỉ trong print đã reset min-height về 0. Thu gọn khoảng cách in để tránh một trang riêng chỉ chứa chú thích cuối báo cáo. Không thay bố cục hoặc CSS của các trang khác.

Kết quả PDF cuối:

| Tệp QA ngoài Git | Nội dung | Kiểm chứng |
|---|---|---|
| `qa-short.pdf` | Tháng 08/2026, 3 giao dịch, không đưa chi tiết, 1 trang A4 | Xem trang 1; nguồn/cảnh báo/số liệu còn đủ, không có trang trắng |
| `qa-long.pdf` | Tháng 09/2026, đủ 38 giao dịch (36 chi, 2 thu), 5 trang A4 | Xem cả 5 trang; tiêu đề bảng lặp trên trang 2–5; đủ 38 dấu định danh QA, không mất cột/chữ |
| `qa-nojs-long.pdf` | Cùng tháng, JavaScript tắt, 5 trang A4 | Xem cả 5 trang; đủ chi tiết và nguồn như bản bật JavaScript |

**Đã tạo PDF thật bằng bộ máy in Edge Chromium headless qua Playwright `page.pdf`, không chỉ giả lập print CSS. Chưa thao tác hộp thoại in/Save as PDF thủ công**, chưa thử máy in vật lý, Safari/Firefox hoặc điện thoại thật. Việc bấm nút gọi `window.print()` được kiểm bằng unit test và hook trình duyệt; không gọi đó là đã kiểm hộp thoại native. Số trang phụ thuộc font, lề, tỷ lệ và browser; trường hợp một hàng quá cao hơn một trang có thể phải tách theo bộ máy in.

Đã render **mọi trang** của ba PDF cuối bằng PDFium và xem PNG riêng từng trang. PDFplumber kiểm thêm A4, trang không trống, chữ trong lề ngang, đủ 36 dấu dòng chi và 2 dòng thu; không có username hoặc mô tả tài khoản thứ hai. Kiểm text bổ sung cho kiểm trực quan, không thay thế kiểm trực quan.

## QA và kiểm thử

Thư mục: `D:\SAO LUU KHOA LUAN\qa-19b-20261027`, chỉ dữ liệu mô phỏng. SQLite mới khởi tạo đến migration 0013; không migrate hoặc kết nối SQLite thật/Render. Hai tài khoản QA mới, có tháng trống, tháng hiện tại, tháng đã xác nhận, danh mục dài/ký tự HTML, mô tả dài không khoảng trắng, một số tiền cực lớn để kiểm wrap, mục tiêu phân bổ và khoản định kỳ chưa ghi nhận.

- **14 kiểm thử mới**: đăng nhập/GET/cache; tháng sai không fallback; link giữ tháng; tổng/cơ cấu khớp Tổng quan; tỷ trọng; mẫu số 0 và không chi; ranh giới năm/ngày; hơn 20 dòng/sắp xếp; không lộ tài khoản khác; text dài/HTML/Decimal lớn; coverage hai tháng; ranh giới ngày Việt Nam kể cả timezone UTC; khoản dự kiến/tiết kiệm không vào tổng; GET không đổi toàn bộ model finance; tháng lịch tối thiểu/tối đa.
- Bộ `finance` trên `.venv` local: **388 trường hợp, 382 đạt, 6 bỏ qua** do thiếu dependency triển khai trong venv local. 14 mới và 8 TASK 19A đã nằm trong 388, không cộng trùng.
- Chạy bổ sung bằng venv QA có sẵn có requirements Render: 14 mới + 8 TASK 19A + 6 trường hợp runtime Render, **28/28 đạt**. Nhóm này trùng một phần với 388, không báo tổng 416. Không cài thêm thư viện.
- JavaScript **35/35 đạt**: gồm 2 mới, 3 TASK 19A và 30 hồi quy; nút không tự in lúc mở trang, chỉ in sau click.
- System check **0 vấn đề**; `makemigrations --check --dry-run`: **No changes detected**. Không cần schema/migration mới.
- Collectstatic với production QA `config.render`, DEBUG=False, database giả localhost:1, chặn mọi `ensure_connection`: **10 tệp copied, 20 post-processed**; manifest/URL/gzip đạt, gồm CSS/JS báo cáo và script TASK 19A. Không có kết nối DB và không phải deploy Render/Linux.
- Edge headless **1280×900** và **390×844**: mở từ Tổng quan đúng tháng, xem đủ 38 dòng, bảng rộng cuộn trong vùng riêng, không tràn ngang toàn trang; lỗi tháng/empty/current đúng; không page error. Tắt JavaScript: chọn tháng/bật chi tiết và gửi form bằng Enter, xem/in PDF đủ dữ liệu.
- Sau browser/PDF: mọi bản ghi finance QA giữ nguyên so với trước. Hash SQLite thật và hai model EN/VI không đổi. Không chạy lại thí nghiệm hoặc sửa artifact.

Bằng chứng ngoài Git:

| Tệp | Mục đích |
|---|---|
| `desktop-short-report.png`, `desktop-long-report.png`, `mobile-short-report.png` | Giao diện có dữ liệu ở hai viewport |
| `mobile-long-detail-scroll.png`, `mobile-empty-report.png`, `mobile-nojs-report.png` | Bảng cuộn, trạng thái trống, tắt JavaScript |
| `qa-short-page-01.png`, `qa-long-page-01.png` … `05.png`, `qa-nojs-long-page-01.png` … `05.png` | Render từng trang của PDF cuối |
| `browser-checks.json`, `pdf-verification.json`, `final-verification.json` | Kết quả UI/PDF/bảo toàn dữ liệu và TASK 19A |
| `regression.log`, `final-related-tests.log`, `javascript.log`, `handoff-static-report.json`, `evidence-manifest.json` | Kiểm thử, đóng gói static và hash bằng chứng |

Server QA 8024 và browser headless đã dừng sau kiểm tra; cổng 8024 đã đóng.

Ảnh trung gian cũ đã được tách vào `initial-print-inspection`; không dùng chúng làm bằng chứng bản PDF cuối. Cấu hình, credential, database, PDF và ảnh QA không đưa vào Git/static/public. Chưa kiểm PostgreSQL thật trong task này; schema/truy vấn ORM không thêm ràng buộc đặc thù SQLite. Chưa kiểm tải lớn.

## Tệp thay đổi riêng TASK 19B

1. `finance/monthly_report.py` — form tháng và dữ liệu đọc lại từ thống kê chung.
2. `finance/monthly_report_views.py` — view đăng nhập, GET-only, private/no-store, lỗi tháng 400.
3. `finance/urls.py` — URL báo cáo.
4. `templates/finance/monthly_report.html` — báo cáo, lựa chọn chi tiết, hướng dẫn in.
5. `templates/finance/dashboard.html` — liên kết giữ tháng chọn.
6. `templates/base.html` — block tải CSS riêng trang.
7. `static/css/monthly-report.css` — screen/mobile và A4 print.
8. `static/js/monthly-report.js` — gọi in sau click.
9. `finance/test_monthly_report.py`, `scripts/test_monthly_report.js` — kiểm thử.
10. `README.md`, tài liệu này — hướng dẫn/bàn giao.

TASK 19A được giữ nguyên từng byte trong 11 tệp riêng; README chỉ nối thêm phần TASK 19B sau nội dung đã có. Không reset, stage, commit hoặc push. Rà diff/bí mật trước bàn giao; không thay dữ liệu thật, production, schema, model ML, dependency hoặc kết quả nghiên cứu.
