# TASK 11B — Tìm kiếm và lọc giao dịch

Ngày thực hiện: **21/10/2026**. Chỉ thay danh sách giao dịch; giữ bộ lọc tháng của Tổng quan, dữ liệu thật, requirements, mô hình và các thí nghiệm. Không export, biểu đồ, ngân sách hoặc deploy. Không commit/push trong task này.

## Cách dùng

Trang `/giao-dich/` yêu cầu đăng nhập, chỉ nhận GET. Nhập điều kiện rồi bấm **Lọc**; **Xóa bộ lọc** mở lại URL không có tham số, trở về tháng hiện tại theo múi giờ website Asia/Ho_Chi_Minh. Các trường:

| Tham số | Ý nghĩa |
|---|---|
| `q` | Chuỗi chứa trong mô tả, tối đa 500 ký tự; bỏ khoảng trắng hai đầu, không phân biệt hoa/thường, giữ dấu |
| `kind` | Rỗng = tất cả, `income` = thu, `expense` = chi |
| `category` | ID danh mục của chính tài khoản, hoặc rỗng = tất cả |
| `period` | `month` hoặc `range`; thiếu tham số mặc định `month` |
| `month` | YYYY-MM, mặc định tháng hiện tại khi thiếu; chỉ dùng trong chế độ month |
| `start`, `end` | Hai ngày của chế độ range; bắt buộc đủ hai ngày hợp lệ, bắt đầu không sau kết thúc; tính cả hai ngày biên |
| `page` | Phân trang 20 dòng; sắp xếp ngày giảm dần rồi ID giảm dần |

JavaScript ẩn/vô hiệu các ô thời gian không dùng. Máy chủ bỏ trường không thuộc chế độ đang chọn **trước validation**, kể cả URL bị sửa có cả hai bộ ngày. Vì vậy không có giao ngầm tháng với khoảng ngày; trường lỗi ở chế độ không chọn không làm sai kết quả. Khi tắt JavaScript vẫn chọn được chế độ và gửi form; máy chủ áp dụng đúng chế độ đó.

Danh mục có thể cùng hoặc khác loại đang lọc; khác loại hợp lệ cho kết quả rỗng, không tự sửa điều kiện. Danh mục không tồn tại, ID sai hoặc thuộc người khác đều cùng thông báo “Danh mục không hợp lệ. Vui lòng chọn lại.” Không đưa tên/ID dữ liệu người khác vào lỗi.

Bộ lọc không hợp lệ được giữ để sửa, báo lỗi tiếng Việt tại trường, không trả kết quả một phần hoặc tự chuyển về tháng hiện tại. Khi hợp lệ nhưng không khớp, hiển thị “Không có kết quả phù hợp” và các tổng bằng 0. Luôn hiện tóm tắt các điều kiện thực sự đang áp dụng. Template escape chuỗi tìm kiếm.

## Truy vấn và tiền

`transaction_list` khởi tạo **Transaction.objects.filter(user=request.user)** trước khi đưa vào `apply_filters`. Trường category dùng ModelChoiceField với queryset Category chỉ của tài khoản đó. Không nhận user_id làm điều kiện chủ sở hữu. Các bộ lọc chỉ thu hẹp queryset đã giới hạn, không bắt đầu lại truy vấn toàn bảng theo điều kiện của trình duyệt.

SQLite LIKE/LOWER mặc định không xử lý đầy đủ chữ Việt hoa/thường. Khi có q, dịch vụ đăng ký hàm thuần `finance_casefold` trên kết nối SQLite hiện tại, dùng alias SQL và `contains` với tham số được ORM escape. Cả mô tả lẫn chuỗi tìm đều dùng Python casefold. Không sửa schema hoặc lưu mô tả chuẩn hóa vào DB. Ký tự `%`, `_` trong q là ký tự thường, không thành wildcard tùy ý. Không bỏ dấu, dịch, chuẩn hóa NFC hoặc tìm gần đúng; Unicode tổ hợp khác nhau có thể không khớp nếu chỉ khác cách biểu diễn dấu. Dự án đã kiểm trên SQLite; nhánh backend khác dùng icontains chưa được xác minh Unicode tương đương.

Tổng toàn bộ kết quả lấy từng cặp kind/amount và cộng **Decimal**, tránh SUM NUMERIC/float của SQLite làm tròn tổng lớn. Đếm kết quả trên cùng queryset. Sau đó mới lấy trang 20 dòng. Tổng thu, tổng chi và chênh lệch không đổi chỉ vì chuyển trang. Phân trang mang q/kind/category/chế độ/ngày hiện hành, bỏ tham số không thuộc form và trường thời gian không dùng; tháng mặc định cũng được khóa trong link để không vô tình đổi tháng khi sang trang.

Không bao quanh đọc bằng transaction khóa ghi. Tổng/đếm/trang là các lần đọc riêng; khi có người ghi đồng thời giữa các lần đọc có thể thấy thay đổi dữ liệu thực tế. Thứ tự ngày/ID ổn định trên cùng bộ dữ liệu, không cam kết snapshot bất biến giữa các trang nếu người dùng sửa dữ liệu trong lúc duyệt. Tìm chuỗi chứa/casefold không dùng chỉ mục tìm toàn văn; chưa benchmark tập rất lớn, không thêm thư viện hoặc chỉ mục trong bước này.

## Kiểm thử tự động

- Lượt đầu: **42 kiểm thử liên quan đạt** (`finance.test_transaction_filters` và `finance.tests`).
- Hồi quy: **158 kiểm thử Django đạt**, gồm 147 cũ và 11 kiểm thử bộ lọc mới. Không cài thư viện, không dùng DB thật cho test.
- Sau chỉnh nhỏ cuối chỉ khóa điều kiện mặc định trong link phân trang, chạy lại **11 kiểm thử bộ lọc**, đều đạt; không chạy lại toàn bộ hồi quy khi không có thay đổi chức năng khác.
- System check không lỗi; `makemigrations --check --dry-run`: không có thay đổi schema, không cần migration trên DB thật.
- **10 kiểm thử JavaScript gợi ý phân loại hồi quy đạt**; JavaScript bộ lọc mới được kiểm trực tiếp qua các thao tác đổi chế độ trong trình duyệt QA.

Các ca kiểm thử mới: mặc định tháng hiện tại/tách tài khoản; chuỗi con chữ Việt hoa/thường; ký tự phần trăm/gạch dưới và chuỗi giống SQL injection; phối hợp loại/danh mục/ngày/mô tả; ngày đầu/cuối trùng nhau, qua năm và 29/2; bỏ điều kiện thời gian không chọn; ngày đảo/sai/thiếu, tháng sai, loại sai, mô tả quá dài; danh mục người khác/không tồn tại/ID sai cho cùng lỗi; 25 dòng qua hai trang không lặp/mất và ID ổn định; tổng Decimal **24.999.999.999.999.975** giữ chính xác; tổng thu/chi/chênh lệch/rỗng; escape HTML, đăng nhập, GET-only; không đổi dòng dữ liệu khi lọc; tháng 12/9999 không overflow.

## Kiểm tra trực tiếp bằng trình duyệt

SQLite mới tại **`D:\SAO LUU KHOA LUAN\qa-11b-20261021-202224\qa.sqlite3`**, settings/secret/session và CSRF cookie riêng, cổng **8004**. Hai tài khoản kiểm thử, 30 giao dịch mô phỏng: tài khoản A có 29 khoản ở tháng 9–11/2026; tài khoản B có một khoản với mô tả chứa ĐIỆN và danh mục riêng. Không copy hoặc sửa dữ liệu thật. Mật khẩu QA ngẫu nhiên chỉ giữ riêng, không ghi vào tài liệu/Git.

Đã điều khiển IAB thật, không dùng HTTP 200 thay cho kiểm giao diện:

| Luồng | Kết quả quan sát |
|---|---|
| Desktop 1280×900, trang mặc định | Tháng 10/2026, 27 khoản của A; thu 50.000đ, chi 32.000đ, chênh lệch 18.000đ |
| Tìm ĐIỆN, tất cả loại/danh mục, khoảng 01–31/10 | 26 khoản, trang 1 có 20 dòng; thu 50.000đ, chi 25.000đ, chênh lệch 25.000đ. Không có khoản/tên danh mục của B |
| Bấm Trang sau | 6 dòng, link giữ đúng chuỗi tìm/chế độ/hai ngày; tổng và số kết quả toàn bộ giữ nguyên |
| Thêm loại Chi tiêu + Điện nước QA | 25 khoản; thu 0đ, chi 25.000đ, chênh lệch −25.000đ; điều kiện hiển thị đầy đủ |
| Ngày bắt đầu 01/11 sau kết thúc 31/10 | Hiện lỗi tại ngày kết thúc; không hiển thị bảng tổng hợp/kết quả thay thế |
| Mobile 390×844, chuyển Theo tháng | Chỉ có ô tháng; hai ngày cũ không gửi/không áp dụng. q=điện vẫn khớp, 25 khoản; trang 2 có 5 dòng và giữ tổng chi 25.000đ |
| Mobile không có kết quả | Hiện trạng thái trống; tổng thu/chi/chênh lệch đều 0 |
| Mobile bấm Xóa bộ lọc | URL danh sách không tham số, tháng hiện tại/tất cả loại/danh mục; lại có 27 khoản |
| Mobile khoảng 31/10–31/10, loại Thu nhập | Đúng một khoản thu 50.000đ, chứng minh ngày kết thúc được tính vào kết quả |

Ảnh riêng: `desktop-range.png`, `desktop-page2.png`, `desktop-combined.png`, `desktop-invalid-range.png`, `mobile-month.png`, `mobile-empty.png`, `mobile-one-day-income.png` trong thư mục QA. Biểu mẫu mobile xếp dọc, tổng xếp từng khối, bảng giao dịch thành các dòng có nhãn; viewport 390px, document 375px do scrollbar, không tràn ngang toàn trang. Menu điều hướng có vùng cuộn ngang riêng. Đây là viewport mô phỏng, chưa kiểm điện thoại vật lý hoặc Safari. Tách tài khoản với ID giả mạo và mọi tổ hợp lỗi được kiểm tự động, không khẳng định tất cả đã thử qua UI.

Sau đăng nhập QA, đã chụp hash nội dung toàn dòng tài khoản và các bảng finance, đối chiếu lại sau các thao tác lọc: **không đổi**. Chỉ đăng nhập ghi session/last_login trước mốc so sánh; các thao tác tìm/lọc không ghi tài khoản, giao dịch, coverage hoặc forecast. Bằng chứng `before-ui.json` và `after-ui.json` chỉ nằm ngoài Git.

Đã trả viewport về mặc định, đóng tab và dừng máy chủ QA sau kiểm tra. Website cục bộ đã được mở với cấu hình bình thường tại `http://127.0.0.1:8001/`; kiểm cổng đang nghe, không đăng nhập hoặc thử ghi trên DB thật. Bằng chứng UI trong bảng vẫn là của DB QA ở cổng 8004, không nhầm hai môi trường.

## Bảo toàn và tệp thay đổi

Trước sửa có SQLite backup API tại `backups/task11b-20261021-201907/before.sqlite3`, integrity_check=ok. Đối chiếu **171 tệp** dữ liệu/artifact/thí nghiệm, requirements và SQLite thật sau kiểm tra: SHA-256 giữ nguyên. Không huấn luyện, chạy lại 10D hoặc sửa dữ liệu. Bản backup/QA đều bị loại khỏi Git; không đổi .gitignore.

Thêm `finance/transaction_filters.py`, `finance/test_transaction_filters.py`, `static/js/transaction-filters.js` và tài liệu này; sửa view danh sách, template danh sách, CSS và README. Không thay models, forms giao dịch, bộ lọc Tổng quan hoặc các dịch vụ ML/CSV/coverage/forecast. Mã truy vấn chỉ đọc, không có migration mới.
