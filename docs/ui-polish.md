# TASK 12A — Hoàn thiện giao diện bản đầu

Thực hiện ngày **21/10/2026** tại `D:\KHÓA LUẬN TỐT NGHIỆP`. Đã đọc các template/CSS/JavaScript hiện có và tài liệu nhập/xuất CSV, bộ lọc, thống kê, tài khoản, lịch sử ghi chép, tích hợp dự báo, demo và gợi ý tiếng Việt. Không thêm chức năng nghiệp vụ, schema, framework, CDN hoặc deploy. Không chạy lại thí nghiệm hay TASK 10D.

## Thay đổi

| Khu vực | Trước | Sau |
|---|---|---|
| Menu điện thoại | Một hàng cuộn, chỉ thấy khoảng ba mục | Hai cột ở 390 px, thấy đủ sáu mục; mục đang mở có nền và đường nhấn |
| Điều hướng CSV | Nhập/xem trước CSV chưa đánh dấu khu vực Giao dịch | Giữ mục Giao dịch đang hoạt động trên các trang CSV; demo vẫn thuộc Dự báo |
| Nhập/xuất | Hai nút nằm ở hai đoạn riêng | Cùng một khối công cụ trong Giao dịch, xếp dọc trên điện thoại; xuất vẫn mang bộ lọc đã áp dụng |
| CSV upload | Hướng dẫn dài đẩy trường chọn tệp xuống thấp | Giới hạn và header vẫn hiện; quy tắc từng cột chuyển vào mục mở rộng có thể dùng bàn phím |
| CSV xem trước | Hướng dẫn kỹ thuật và liên kết dồn một đoạn | Giữ hạn dùng, cảnh báo và xác nhận; đưa chi tiết máy chủ/hash vào mục mở rộng, tách liên kết dễ bấm |
| Biểu mẫu/nút | Một số liên kết nhỏ và chữ phụ nhạt | Tăng tương phản chữ phụ, cỡ hướng dẫn; vùng bấm liên kết hành động/phân trang tối thiểu 44 px; nút chính xanh, phụ viền, xóa đỏ |
| Trạng thái | Có lỗi/thành công nhưng thiếu phản hồi chung khi POST | Thêm thông báo “Đang xử lý… Vui lòng chờ.” và `aria-busy`; ngăn submit lặp trên cùng trang, khôi phục khi Back/Forward; flash lỗi dùng `role=alert`, thông báo khác dùng `role=status` |
| Ngày | Mẫu xem trước CSV dùng YYYY-MM-DD | Ngày hiển thị trong mẫu CSV dùng dd/mm/yyyy như giao dịch; định dạng tệp và trường ngày vẫn giữ YYYY-MM-DD |

Giữ bố cục, bảng/card, màu xanh và font hệ thống hiện có. Các vùng bảng/biểu đồ rộng có cuộn riêng; bảng vẫn dùng HTML, không phụ thuộc JavaScript để đọc số liệu. CSS có phiên bản URL `?v=12a` để trình duyệt nhận giao diện mới. Các tài nguyên vẫn phục vụ cục bộ; không cần Internet để tải font, CSS hoặc thư viện giao diện.

JavaScript mới chỉ phản hồi **POST** sau khi trình duyệt chấp nhận gửi form. Không thay giá trị trường, `action`, CSRF, submitter hoặc vô hiệu các input; không tự gửi, tự lưu hoặc tính dự báo khi mở trang. Chống gửi lặp phía giao diện không thay thế ràng buộc phía máy chủ. GET lọc/xuất không bị chặn.

Các cảnh báo dễ thấy vẫn giữ: gợi ý có thể sai và chỉ áp dụng chủ động; dữ liệu demo là mô phỏng; xác nhận lịch sử do người dùng; tháng chưa biết không tự thành 0; dự báo chỉ ước tính khoản chi ghi trong website. Chi tiết mô hình AI/tiếng Anh, MAE và giới hạn vẫn đọc được trong các mục mở rộng. Không hiển thị điểm mô hình như phần trăm chắc chắn; không gọi chênh lệch thu–chi là số dư ngân hàng.

## Cách ly kiểm tra

- QA: `D:\SAO LUU KHOA LUAN\qa-12a-20261021-213137`, máy chủ `127.0.0.1:8008` trong lúc kiểm tra. SQLite sao từ **QA TASK 11E**, không sao tài khoản hoặc dữ liệu thật. Có settings, SECRET_KEY và cookie riêng. Mật khẩu QA không nằm trong báo cáo/Git.
- Dữ liệu QA có 26 giao dịch tháng 10/2026 để kiểm phân trang, bảng dài và thống kê; tên danh mục thử có ký tự `=1+1`. Trong lần kiểm CSV này chỉ nhập thêm **một giao dịch mô phỏng 23.000 VND tháng 09/2026** vào QA. Không xác nhận lịch sử, xóa giao dịch hoặc đổi thông tin đăng nhập để kiểm bố cục.
- Snapshot trước sửa: `D:\KHÓA LUẬN TỐT NGHIỆP\backups\task12a-20261021-213137`: bản SQLite bằng backup API và manifest SHA-256 của 241 tệp dữ liệu/mô hình/thí nghiệm/mã nghiệp vụ/cấu hình/requirements/SQLite thật. Sau thực hiện, cả 241 mục vẫn khớp. Đây là snapshot bảo toàn dữ liệu và dấu vân tay, không phải bản sao toàn bộ source trước TASK 12A.

## Kiểm tra trực tiếp trên trình duyệt

Dùng trình duyệt trong ứng dụng, viewport **1280×900** và **390×844 CSS px**, thao tác UI thật, lưu PNG và đọc kích thước DOM; không dùng HTTP 200 thay bằng chứng giao diện. `browser-evidence.json` ghi **30 tổ hợp trang/kích thước**: Tổng quan, Giao dịch, Danh mục, Lịch sử ghi chép, Dự báo, Demo, Tài khoản, thêm giao dịch, thêm danh mục, tải CSV, chi tiết giao dịch, xác nhận xóa, xác nhận tháng, đăng nhập và đăng ký.

| Kiểm tra | Kết quả thực tế |
|---|---|
| Bố cục/điều hướng | 15 trang ở mỗi kích thước không có scrollWidth toàn trang lớn hơn viewport; menu điện thoại thấy đủ sáu mục; CSV thuộc Giao dịch, demo thuộc Dự báo |
| Nhãn và bàn phím | Không phát hiện input/select/textarea đang rà thiếu label; Tab từ ô tìm kiếm chuyển sang Loại, có outline vàng rõ; mục hướng dẫn CSV mở được |
| CSV lỗi | Chọn tệp qua file chooser, bấm kiểm tra: lỗi ngày 30/02 và số tiền âm ở dòng 2; không có nút xác nhận |
| CSV hợp lệ | Xem trước một dòng, 23.000 VND, ngày 10/09/2026; xem được ở hai kích thước; bấm xác nhận trên mobile, hiện đã nhập một giao dịch và không còn nút nhập lại |
| Lọc lỗi/trống | Khoảng ngày đảo nhận lỗi tiếng Việt; không xuất CSV hay hiển thị tổng sai. Chuỗi không khớp hiển thị trạng thái trống; Xóa bộ lọc quay về tháng hiện tại |
| Gợi ý ML | Chọn Chi + tiếng Việt, nhập mô tả QA; quan sát “Đang tìm gợi ý…” rồi kết quả thực. Danh mục vẫn rỗng, không tự lưu. Mục thông tin mô hình mở được |
| Dự báo/demo | Rà trạng thái thiếu lịch sử, danh sách tháng cần xác nhận, liên kết demo, banner mô phỏng, lịch sử và mục cấu hình. Không bấm tính Ridge/demo hoặc tạo kết quả mới trong lần QA này |
| Trang tài khoản/xóa/xác nhận | Kiểm giao diện biểu mẫu và nút chính/phụ/xóa; không đổi mật khẩu/tên, không thực hiện xóa hoặc xác nhận tháng |
| Đăng nhập/đăng xuất | Đăng nhập bằng tài khoản QA được, POST logout trở về đăng nhập; form đăng nhập/đăng ký không tràn ở hai kích thước |

Thông báo chờ POST chung được kiểm hành vi bằng Node (gửi đầu không bị hủy, chặn gửi lặp, bỏ qua GET/sự kiện đã hủy và reset `pageshow`). POST CSV thành công và logout đã thử trên trình duyệt; chưa có ảnh bắt được trạng thái chờ POST chung vì chuyển trang nhanh. Ảnh đang chờ gợi ý là trạng thái bất đồng bộ sẵn có, không dùng để chứng minh ảnh chờ POST chung.

## Ảnh và bằng chứng

Tất cả ảnh nằm ngoài Git tại **`D:\SAO LUU KHOA LUAN\qa-12a-20261021-213137`**. Ảnh `fullPage` giữ chiều rộng viewport nhưng có thể cao hơn 900/844 px để ghi cả trang.

| Thay đổi chính | Trước | Sau |
|---|---|---|
| Tổng quan desktop | `before-desktop-dashboard.png` | `after-desktop-dashboard.png` |
| Công cụ Giao dịch desktop | `before-desktop-transactions.png` | `after-desktop-transactions.png` |
| Menu/Giao dịch điện thoại | `before-mobile-transactions.png` | `after-mobile-transactions.png` |
| Menu/hướng dẫn CSV điện thoại | `before-mobile-csv.png` | `after-mobile-csv.png` |

Ảnh bổ sung: `after-desktop-csv-guide.png`, `after-desktop-csv-errors.png`, `after-desktop-csv-preview.png`, `after-mobile-csv-preview.png`, `after-mobile-csv-success.png`, `after-mobile-filter-errors.png`, `after-mobile-empty.png`, `after-mobile-suggestion.png` (đang chờ), `after-mobile-suggestion-final.png`, `after-mobile-model-info.png`, `after-mobile-coverage-confirm.png`. Các trang còn lại có tên `after-desktop-<trang>.png` và `after-mobile-<trang>.png`; danh sách đầy đủ và SHA-256 ở `qa-artifact-manifest.json`. Ảnh viewport desktop bàn giao: `after-desktop-overview-viewport.png`.

## Kiểm thử và bảo toàn

- `manage.py test`: **188/188 đạt** sau sửa CSS/base/JavaScript/template chung. Log thiếu/lỗi mô hình là các nhánh lỗi có chủ đích trong kiểm thử.
- Sau thay riêng ngày hiển thị CSV: `manage.py test finance.test_csv_import finance.test_csv_export`: **34/34 đạt**; không chạy lại toàn bộ khi chỉ template CSV đổi.
- `node --test scripts/test_form_feedback.js scripts/test_transaction_suggestion.js`: **14/14 đạt** (4 phản hồi form + 10 gợi ý).
- `manage.py check`: không vấn đề. `makemigrations --check --dry-run`: không thay đổi schema. Không chạy migration mới trên dữ liệu thật.
- Giữ nguyên byte mã Python nghiệp vụ/cấu hình/script thí nghiệm, dữ liệu, artifact và requirements đã lập manifest; SHA-256 SQLite thật không đổi. Kiểm `integrity_check` bản snapshot SQLite: `ok`.
- Máy chủ QA được dừng và viewport trả mặc định sau kiểm tra; máy chủ cục bộ chính được khởi động lại để nhận template/CSS mới. Không deploy hoặc commit/push.

## Tệp thuộc TASK 12A

`static/css/app.css`; `templates/base.html`; `templates/finance/transaction_list.html`; `templates/finance/csv_upload.html`; `templates/finance/csv_preview.html`; `templates/finance/includes/csv_inspection.html`; mới `static/js/form-feedback.js`, `scripts/test_form_feedback.js`, tài liệu này. Các thay đổi chưa commit của TASK 11B–11E đã có từ trước được giữ lại; không tính chúng là thay đổi mới của TASK 12A.

## Giới hạn và vấn đề để sau

- Chỉ thử responsive trên cùng engine trình duyệt, chưa thử thiết bị Android/iPhone, Safari, screen reader hoặc kiểm toán accessibility đầy đủ. Màu/focus/nhãn đã rà nhưng không tuyên bố đạt chứng nhận WCAG.
- Menu hai cột dùng thêm chiều cao trên điện thoại; bảng nhiều tháng/giao dịch dài cần cuộn dọc. Biểu đồ demo rộng vẫn cuộn trong vùng riêng.
- Chưa kiểm lại toàn bộ trạng thái dự báo ML đủ lịch sử/cache lỗi trên trình duyệt trong task giao diện này; giữ bằng chứng TASK 09C và kiểm thử hồi quy, không gọi đó là lần thử UI mới.
- Quan sát gợi ý cho “Mua rau củ nấu bữa tối” trả Restaurants. Điều này cho thấy cần xem lại gợi ý theo ngữ cảnh; không sửa mô hình/ánh xạ/quy tắc trong TASK 12A và không dùng một câu để suy ra độ chính xác.
- Chưa phát hiện lỗi nghiệp vụ mới cần đổi mã trong lần rà này. Nếu cần cải thiện chất lượng gợi ý hoặc phạm vi kiểm thử đa trình duyệt, xử lý ở task riêng.
