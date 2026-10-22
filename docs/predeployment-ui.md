# TASK 13B — Hoàn thiện giao diện trước triển khai trực tuyến

Ngày thực hiện: **22/10/2026**, Asia/Ho_Chi_Minh. Làm trên dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`, cổng **8001**; không sửa bản phục hồi 8003. Phạm vi chỉ template, CSS và hai câu kỳ vọng trong kiểm thử giao diện. Không đổi schema, nghiệp vụ, JavaScript, models, requirements, dữ liệu thật hoặc artifact/thí nghiệm ML; chưa deploy.

## Thay đổi giao diện

| Khu vực | Thực hiện |
|---|---|
| Tổng quan | Giữ thứ tự bộ chọn tháng → thu/chi/chênh lệch → ngân sách → cơ cấu chi → so sánh tháng → giao dịch gần đây. Giảm khoảng cách và chiều cao thẻ, tăng chữ phụ |
| Ngân sách trên Tổng quan | Gom thành một thẻ; hạn mức, chi đã ghi nhận và còn lại/vượt xếp ba cột ở desktop, dòng đôi trên điện thoại. Có nút **Xem ngân sách**, cảnh báo bằng chữ và màu; giữ trạng thái lịch sử rõ ràng |
| Nội dung/tháng trống | Dùng “thu/chi đã ghi nhận”, “tháng này chưa ghi nhận giao dịch”; không suy ra không chi tiền ngoài thực tế. Có thao tác thêm giao dịch, tạo danh mục nếu cần và tạo ngân sách |
| Danh sách giao dịch | Bộ lọc nằm trong mục mở rộng **Tìm và lọc giao dịch**; tự mở khi bộ lọc sai để lỗi không bị giấu. Điều kiện đang áp dụng vẫn hiện. Thẻ tổng gọn và công cụ CSV nằm trong mục riêng có thể mở |
| Thêm/sửa giao dịch | Ba phần: **1. Nhập giao dịch**, **2. Gợi ý danh mục (tùy chọn)**, **3. Kiểm tra và lưu**. Các trường nhập tay và nút Lưu không bị chôn sau một khối ML dài; gợi ý được mở khi cần |
| ML | Giữ nhắc gợi ý có thể sai bên ngoài mục đóng; nội dung AI/dữ liệu mô phỏng, tiếng Anh/Việt và áp dụng chủ động vẫn đọc được khi mở. Không thêm score, phần trăm chắc chắn hoặc tự áp dụng |
| Ngân sách/Dự báo | Dùng cùng nền, viền, bo góc, khoảng đệm, hệ nút/thông báo và `vnd` hiện có. Giữ hạn chế coverage, mục tiêu dự báo và nhãn TB3 không phải ML |
| Menu điện thoại | **Menu điều hướng** mở/đóng bằng `<details>/<summary>` gốc HTML; mặc định gọn, mở ra đủ bảy mục. Desktop vẫn là sidebar. Hai nơi dùng chung `includes/navigation.html` |
| Khả năng tiếp cận/offline | Giữ label/focus bàn phím; vùng bấm khoảng 44px trở lên, chữ phụ 13–14px. Không thêm framework, font ngoài, CDN hoặc ảnh trang trí. Các mục mở rộng không cần JavaScript |

CSS được cập nhật URL phiên bản `?v=13b.1`; chỉ phục vụ tài nguyên cục bộ. Các bảng và dữ liệu HTML vẫn giữ nguyên; bảng/biểu đồ rộng cuộn trong vùng riêng. Khi JavaScript không chạy, người dùng vẫn đọc số liệu, mở menu/bộ lọc/hướng dẫn và nhập thủ công; gợi ý ML vẫn cần JavaScript như trước.

## Môi trường và dữ liệu QA

Thư mục QA mới: **`D:\SAO LUU KHOA LUAN\qa-13b-20261022-080008`**. SQLite, settings, khóa phiên và cookie riêng, cổng **8010**. Không sao giao dịch hoặc tài khoản thật vào QA. Tài khoản QA được tạo với mật khẩu ngẫu nhiên, không ghi mật khẩu trong báo cáo/Git.

Dữ liệu mô phỏng cố định, chỉ trong QA:

- Tháng 10/2026: thu **9.000.000**, chi **1.100.000**, chênh lệch thu–chi **7.900.000 VND**; hai danh mục chi 780.000 và 320.000.
- Ngân sách tổng 1.000.000 → **110%, vượt 100.000**; danh mục 500.000 so với 780.000 → **156%, vượt 280.000 VND**. Tháng hiện tại giữ **Chưa xác nhận**.
- Sáu tháng liên tiếp 04–09/2026 được giả lập và xác nhận trong QA sau khi tạo giao dịch; tháng 06 có zero được xác nhận rõ. Ba tổng tháng cuối 650.000, 700.000, 750.000 → kết quả dịch vụ TB3 **700.000 VND** cho 10/2026. Chỉ dùng nhánh dưới 36 tháng, không fit Ridge/huấn luyện ML cho fixture.
- Tháng 01/2026 không có giao dịch/ngân sách, trạng thái chưa xác nhận: kiểm lời dẫn và hành động trống, không diễn giải zero là không chi tiền.
- Biểu mẫu được điền 95.000 VND và mô tả QA để chụp, chưa bấm lưu giao dịch hợp lệ từ biểu mẫu này. Không gửi mô tả QA vào mô hình hoặc chạy lại TASK 10D.

## Kiểm tra trình duyệt thực tế

Đã thao tác trình duyệt trong ứng dụng, đo DOM **1280×900** và **390×844 CSS px**, chụp đủ bốn trang yêu cầu ở cả hai kích thước với dữ liệu như trên. Có thêm trang Giao dịch: `browser-evidence.json` ghi 10 tổ hợp trang/kích thước. Không dùng HTTP 200 thay cho bằng chứng UI.

| Kiểm tra | Quan sát |
|---|---|
| Tràn ngang/nhãn | Cả 10 tổ hợp không có scrollWidth lớn hơn clientWidth; không thấy input/select/textarea thiếu label trong các trang rà |
| Tổng quan có dữ liệu | Đúng thứ tự các khối; tổng thu/chi, mức vượt ngân sách và lịch sử Chưa xác nhận giữ rõ |
| Tháng trống | Hiện “chưa ghi nhận”, zero quan sát và các nút thao tác; không tuyên bố không chi tiền |
| Biểu mẫu | Các trường nhập tay hiện trước, có dữ liệu đã điền; ML mặc định gọn và mở được; bước kiểm tra/Lưu vẫn hiện |
| Menu điện thoại | Mở bằng click; đóng bằng Space trên summary; focus có outline. Không cần JS để mở/đóng |
| Bộ lọc | Mở để chỉnh; ngày đầu sau ngày cuối trả lỗi tiếng Việt và mục lọc tự mở. Khi đóng các công cụ, đầu khu vực kết quả lên khoảng y=763 trong khung 844px của kịch bản QA |
| Ngân sách | Tổng 110% và danh mục 156%, thanh vẽ dừng 100%, số vượt giữ thật; không mất cảnh báo lịch sử |
| Dự báo có kết quả | Hiện 6 tháng lịch sử, đích 10/2026, TB3 700.000 VND; nêu rõ không phải ML. Không bấm chạy demo hoặc tính Ridge |

Đầu lượt kiểm, công cụ đọc được DOM nhưng chụp ảnh thất bại. Sau khi người dùng mở/khôi phục cửa sổ Codex, chụp được ảnh. Công cụ có tỷ lệ hiển thị khác CSS pixel: đã hiệu chỉnh qua viewport API và **xác nhận lại kích thước DOM thực tế**, không lấy số yêu cầu API làm bằng chứng. PNG có thể lớn hơn viewport CSS do DPI; ảnh fullPage cao hơn 900/844px. Ảnh preview được chụp với clip qua chính API screenshot để bỏ phần canvas thừa, không sửa dữ liệu/màu hay dựng ảnh giao diện giả.

## Kiểm tra khi script không chạy

QA phụ cổng **8011** dùng cùng SQLite QA, thêm middleware **chỉ ngoài dự án** để đặt CSP `script-src 'none'`. Đã mở Tổng quan, menu, danh sách/bộ lọc và biểu mẫu qua trình duyệt khi script bị chặn:

- Số liệu, bảng ba giao dịch, menu và bộ lọc vẫn đọc/mở được; không tràn ngang.
- Gửi thử form Chi nhưng chọn danh mục Lương qua luồng không có JS: server trả lỗi “Danh mục phải phù hợp với loại thu hoặc chi.”, lỗi hiện trong phần nhập tay; không lưu thêm bản ghi.
- Mục ML vẫn là tùy chọn; không bịa kết quả khi không chạy script.

Đây là kiểm **script bị chặn bằng CSP trong QA**, không phải tuyên bố đã tắt JavaScript toàn bộ trình duyệt. Phần `<noscript>` giữ như cũ; CSP không đổi cờ JS của trình duyệt nên không dùng lần này để chứng minh `<noscript>` đã hiển thị. Cấu hình CSP QA không được đưa vào website chính.

## Ảnh bàn giao

Ảnh nằm ngoài Git tại thư mục QA ở trên, chỉ chứa dữ liệu mô phỏng. Danh sách/hash đầy đủ ở `qa-manifest.json` trong thư mục đó. Các ảnh dưới đây là ảnh sau sửa:

| Trang | Desktop | Mobile |
|---|---|---|
| Tổng quan có giao dịch/vượt ngân sách | `desktop-dashboard.png` | `mobile-dashboard.png` |
| Thêm giao dịch có trường đã điền | `desktop-transaction-form.png` | `mobile-transaction-form.png` |
| Ngân sách có số liệu | `desktop-budget.png` | `mobile-budget.png` |
| Dự báo có kết quả TB3 | `desktop-forecast.png` | `mobile-forecast.png` |

Ảnh bổ sung: `desktop-transactions.png`, `mobile-transactions.png`, `mobile-menu-open.png`, `mobile-filter-error-open.png`, `mobile-ml-expanded.png`, `mobile-empty-month.png`, `nojs-mobile-dashboard.png`, `nojs-mobile-filter.png`, `nojs-mobile-form-error.png`. Preview gọn: `desktop-overview-preview.png`.

### Tổng quan

![Tổng quan desktop — dữ liệu QA](</D:/SAO LUU KHOA LUAN/qa-13b-20261022-080008/desktop-dashboard.png>)

![Tổng quan 390×844 — dữ liệu QA](</D:/SAO LUU KHOA LUAN/qa-13b-20261022-080008/mobile-dashboard.png>)

### Thêm giao dịch

![Biểu mẫu desktop](</D:/SAO LUU KHOA LUAN/qa-13b-20261022-080008/desktop-transaction-form.png>)

![Biểu mẫu 390×844](</D:/SAO LUU KHOA LUAN/qa-13b-20261022-080008/mobile-transaction-form.png>)

### Ngân sách

![Ngân sách desktop](</D:/SAO LUU KHOA LUAN/qa-13b-20261022-080008/desktop-budget.png>)

![Ngân sách 390×844](</D:/SAO LUU KHOA LUAN/qa-13b-20261022-080008/mobile-budget.png>)

### Dự báo

![Dự báo desktop có kết quả](</D:/SAO LUU KHOA LUAN/qa-13b-20261022-080008/desktop-forecast.png>)

![Dự báo 390×844 có kết quả](</D:/SAO LUU KHOA LUAN/qa-13b-20261022-080008/mobile-forecast.png>)

## Kiểm thử và bảo toàn

- **198/198 kiểm thử Django hồi quy đạt** sau sửa template/CSS và cập nhật hai assert nội dung trạng thái trống. Lần chạy đầu có hai assert còn tìm câu cũ; chỉ sửa câu kỳ vọng sang “chưa ghi nhận giao dịch”, không bỏ kiểm thử hoặc nới điều kiện nghiệp vụ.
- **14/14 kiểm thử Node đạt**: gợi ý VI/EN, chủ động áp dụng, vô hiệu gợi ý cũ và phản hồi gửi form. Không sửa JS ứng dụng.
- System check không vấn đề; `makemigrations --check --dry-run`: không thay đổi. Không chạy migration lên dữ liệu thật.
- Baseline bảo toàn gồm **247 tệp**: 246 tệp khớp nguyên byte, gồm SQLite thật, model, dữ liệu, script thí nghiệm, mã Python nghiệp vụ và requirements. Tệp khác duy nhất là `finance/tests.py`; đảo đúng hai thay thế câu kỳ vọng khôi phục hash ban đầu, chứng minh không đổi logic kiểm thử khác. `preservation-result.json` ghi kết quả.
- Snapshot SQLite qua backup API tại `backups/task13b-20261022-080008/before.sqlite3`, integrity `ok`; hash SQLite thật trước/sau không đổi. Không thêm QA vào tài khoản thật.
- Đã dừng QA 8010/8011, trả viewport/trạng thái hiển thị công cụ và đóng tab QA. Máy chủ dự án chính khởi động lại ở 8001 để nhận template/CSS mới; không dùng hoặc sửa bản phục hồi 8003.

Tệp thuộc task: `static/css/app.css`; `templates/base.html`; mới `templates/includes/navigation.html`; `templates/finance/dashboard.html`, `transaction_list.html`, `transaction_form.html`; `templates/finance/includes/budget_summary.html`, `financial_statistics.html`; hai assert trong `finance/tests.py`; báo cáo này. Giữ các thay đổi chưa commit từ task trước, không commit/push hoặc đổi remote trong task này.

## Giới hạn còn lại

Chưa thử điện thoại vật lý, Safari, screen reader hoặc kiểm toán accessibility đầy đủ. Bảng dài vẫn cần cuộn dọc; biểu đồ nhiều tháng cuộn trong vùng riêng. Gợi ý ML cần JS như thiết kế cũ; chất lượng mô hình không được đánh giá lại trong task giao diện. Không có kết luận mới về độ chính xác, dữ liệu đầy đủ hoặc mức sẵn sàng triển khai production. Các đường dẫn ảnh là bằng chứng cục bộ, cần chuyển riêng nếu đọc tài liệu trên máy khác.
