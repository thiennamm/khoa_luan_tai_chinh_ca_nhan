# TASK 11C — Cơ cấu chi và so sánh nhiều tháng

Thực hiện **21/10/2026** tại `D:\KHÓA LUẬN TỐT NGHIỆP`. Bổ sung vào Tổng quan hiện có; giữ dữ liệu thật, mô hình, thí nghiệm, logic lọc giao dịch TASK 11B và dự báo. Không cài thư viện, thêm ngân sách/export, commit/push hoặc deploy.

## Sử dụng

Trên Tổng quan, chọn tháng và **So sánh 6 tháng hoặc 12 tháng**, bấm **Xem**. Mặc định tháng hiện tại và 6 tháng. Khoảng so sánh kết thúc ở tháng đang chọn, gồm các tháng lịch liên tiếp, không nối bỏ qua tháng trống. Tháng đầu/cuối đều được tính trọn theo dữ liệu đã ghi đến thời điểm xem; tháng hiện tại có nhắc **“Tháng chưa kết thúc”**, tháng tương lai nếu được chọn ghi “Tháng tương lai”. Múi giờ xác định tháng hiện tại là Asia/Ho_Chi_Minh, tái sử dụng `current_month()` của lịch ghi chép.

### Cơ cấu chi tháng

- Chỉ các khoản expense, danh mục và giao dịch đều thuộc tài khoản đăng nhập.
- Nhóm theo **ID danh mục**, không theo tên; sắp số tiền giảm dần, hòa thì ID tăng dần. Tên trùng ở người khác hoặc danh mục thu không làm gộp nhầm. Cơ sở dữ liệu vốn không cho cùng tên/cùng loại trong một tài khoản; không bỏ ràng buộc để tạo tình huống trùng giả.
- Hiển thị tên, VND và tỷ trọng so với tổng chi tháng, hai chữ số thập phân. Tổng số tiền các nhóm bằng chính xác tổng chi đã ghi. Thanh ngang biểu diễn tỷ trọng này; bảng giữ số tiền đầy đủ.
- Tháng tổng chi 0: thông báo chưa ghi nhận khoản chi, không có thanh hoặc bảng tỷ trọng, không chia cho 0. Có thu nhưng không chi vẫn thuộc trường hợp này.
- Phần trăm làm tròn ROUND_HALF_UP nên tổng tỷ trọng hiển thị đôi khi lệch 100% vài phần trăm nhỏ do làm tròn; không điều chỉnh hoặc tạo thêm phần giả để ép tổng. Tổng tiền không bị làm tròn qua float.

### Thu/chi nhiều tháng

Mỗi tháng có tổng thu, tổng chi, chênh lệch thu–chi, trạng thái lịch sử ghi chép và nhắc thời gian nếu chưa kết thúc/tương lai. Chênh lệch là tổng thu trừ tổng chi, **không phải số dư ngân hàng**, ví hoặc tài sản. Trạng thái lấy theo chính tài khoản từ MonthlyCoverage; không có bản ghi thì **Chưa xác nhận**. “Đã xác nhận đầy đủ” vẫn là xác nhận do người dùng, không phải hệ thống chứng minh.

Tháng không có giao dịch vẫn có một hàng với tổng đã ghi bằng Decimal(0), đồng thời trạng thái có thể Chưa xác nhận/Chưa đầy đủ/Đã xác nhận đầy đủ. Dịch vụ thống kê không tạo hoặc sửa coverage, counter hay ForecastResult. **Không đưa các số 0 này vào dự báo.** `monthly_history` và snapshot dự báo vẫn giữ None khi thiếu xác nhận, chỉ cho zero khi đầy đủ theo quy tắc đã có. Không sửa các tệp coverage/forecast hoặc MoneyData.

Giới hạn lịch đặc biệt: nếu chọn những tháng đầu năm 0001, khoảng được rút gọn ở đầu lịch để tránh underflow; giao diện báo rõ số tháng thực tế. Span sai khác 6/12 báo lỗi, không âm thầm chọn lại. Bộ lọc tháng cũ vẫn giữ hành vi báo lỗi/fallback tháng hiện tại như trước; không đổi quy tắc của TASK 11B.

## Dữ liệu, biểu đồ và bảo mật

`finance/statistics.py:financial_statistics` đọc một queryset giao dịch đã giới hạn `user` và `category__user`, từ tháng đầu đến ngày cuối tháng chọn. Đọc date/kind/amount/category_id/name; tiền được cộng từng dòng bằng **Decimal**, không dùng SQLite SUM/float. Khởi tạo trước toàn bộ lịch tháng rồi cộng khoản thu/chi. Query MonthlyCoverage cũng giới hạn đúng chủ tài khoản và khoảng tháng.

Kết quả trả hai danh sách dùng chung: `category_statistics` cho cả thanh ngang/bảng danh mục, `monthly_statistics` cho cột/bảng nhiều tháng. Các thẻ tổng thu/chi/chênh lệch và số giao dịch của tháng đang chọn trên Tổng quan cũng lấy từ cùng hàng tổng hợp đó, tránh tính lại từ một truy vấn khác rồi lệch cơ cấu nếu có cập nhật giữa các lần đọc. Giao dịch gần đây vẫn là queryset chỉ đọc riêng; đây không phải snapshot bất biến trước thao tác đồng thời khác.

Tỷ trọng và chiều cao cột tính bằng Decimal. Cột thu và chi dùng **cùng thang tối đa** của toàn khoảng đang xem; zero có chiều cao 0, không tạo cột dương giả. Chuỗi chiều rộng/chiều cao là số do máy chủ tính, định dạng dấu chấm để đưa vào CSS an toàn; tên danh mục chỉ hiển thị qua template autoescape. Biểu đồ chỉ dùng HTML/CSS nội bộ, **không truyền tên hoặc số tiền sang JavaScript, không ghép tên vào mã JS**, không tải CDN hoặc thêm thư viện biểu đồ. Không có endpoint nhận dữ liệu biểu đồ từ client.

Bảng đầy đủ được render ngay trong HTML phản hồi, không phụ thuộc JavaScript. Biểu đồ có mô tả truy cập và bảng làm phương án đọc số liệu; màu thu/chi đi kèm chú giải chữ. Desktop hiện biểu đồ cùng bảng; mobile bảng thành khối, vùng biểu đồ cột cuộn ngang riêng bằng kéo hoặc bàn phím. Nội dung dài/tên chứa ký tự đặc biệt có thể xuống dòng; không chạy như HTML/script. Đây là kiểm HTML/server-render và giao diện thường, không khẳng định đã tắt JavaScript trong trình duyệt để thử mọi phần website.

## Kiểm thử và bằng chứng

- **41 kiểm thử liên quan** (10 mới về thống kê + 31 website nền) đạt.
- Hồi quy **168 kiểm thử Django đạt**, gồm 158 kiểm thử trước và 10 mới; không ghi vào database thật. Sau tinh chỉnh cuối nguồn tổng trên Tổng quan và bố cục/hướng dẫn cuộn, chạy lại 41 kiểm thử liên quan, đều đạt; không chạy lại toàn bộ khi không có thay đổi ở dịch vụ khác.
- **10 kiểm thử JavaScript gợi ý hồi quy đạt**. Phần biểu đồ mới không có JavaScript riêng.
- System check không lỗi; `makemigrations --check --dry-run` không có thay đổi. Không cần migration mới.

Các ca mới: tách tài khoản và trạng thái; tên trùng khác chủ/khác loại; tổng nhóm/sắp xếp/tỷ trọng khớp tổng tháng; 6/12 tháng qua năm và ngày biên; tháng trống, zero đã xác nhận và chưa xác nhận; None/0 của dịch vụ dự báo không đổi; tháng hiện tại/tương lai; số tiền tổng lớn **25.000.000.000.124.975 VND** vẫn chính xác; thang cột chung; ký tự HTML trong tên; bảng có sẵn trong HTML khi không dùng JS; span sai; read-only SQL và đăng nhập; lịch năm 0001 không underflow.

### Trình duyệt thật trên SQLite QA

Môi trường riêng: **`D:\SAO LUU KHOA LUAN\qa-11c-20261021-203630\qa.sqlite3`**, cổng **8005**, settings/secret/session cookie/CSRF cookie riêng; hai tài khoản QA mật khẩu ngẫu nhiên. Tài khoản A có giao dịch tự sinh qua năm 2025–2026, tên danh mục có `&`, `<QA>` và chuỗi giống thẻ script/img; tài khoản B có danh mục trùng tên và khoản chi 9.999.999đ riêng. Không sử dụng tài khoản/giao dịch thật.

| Thao tác UI | Kết quả quan sát |
|---|---|
| Desktop 1280×900, tháng 10/2026, 6 tháng | Thu 900.000đ, chi 400.000đ, chênh lệch 500.000đ. Danh mục 300.000đ/75% và 100.000đ/25%, tổng đúng 400.000đ, không lẫn khoản của B |
| Tên chứa chuỗi thẻ HTML | Hiển thị nguyên văn ký tự đã escape trong thanh/bảng; DOM không có img được sinh ra trong khu vực thống kê |
| Chọn 12 tháng qua form | Đúng 12 hàng/cặp cột, từ 11/2025 đến 10/2026, bao gồm 12/2025 và 01/2026 |
| Đối chiếu với dịch vụ trên cùng QA | Chiều cao 24 cột và chiều rộng các thanh trùng với kết quả dịch vụ `expected-ui.json`; bảng tháng hiển thị đúng các tổng và trạng thái |
| Mobile 390×844 | Bảng đọc thành khối, tên dài xuống dòng; document 375px (trừ scrollbar), không tràn toàn trang. Vùng biểu đồ riêng rộng 294px, nội dung 872px, cuộn tới tháng cuối được |
| Mobile chọn 08/2026 | Cơ cấu chi rỗng, không có thanh/tỷ trọng; hàng tháng 08 tổng 0 và Đã xác nhận đầy đủ |
| Mobile chọn 06/2026 | Hàng tháng tổng 0 nhưng Chưa xác nhận; không tự tạo xác nhận hoặc dự báo |
| Bản bố cục cuối desktop | Cả 6 và 12 tháng vừa vùng chart rộng 903px; đủ tháng cuối 10/2026 và nhắc Tháng chưa kết thúc |

Ảnh và dữ liệu đối chiếu giữ riêng trong thư mục QA: `desktop-six-months.png`, `desktop-twelve-months.png`, `desktop-final-six-months.png`, `desktop-final-twelve-months.png`, `mobile-twelve-months.png`, `mobile-final-twelve-months.png`, `mobile-chart-right.png`, `mobile-confirmed-zero.png`, `mobile-unknown-zero.png`, `expected-ui.json`. Đã mở lại bản mã cuối sau chỉnh nguồn tổng và chụp lại desktop/mobile, các số và 12 hàng giữ đúng. Ảnh có tên giống thẻ HTML là dữ liệu kiểm thử tự đặt, không phải script được thực thi. Kiểm tách tài khoản giả mạo/chi tiết mọi ca lỗi bằng test tự động; không khẳng định đã thao tác mọi ca đó qua UI. Chưa kiểm điện thoại vật lý/Safari hoặc dữ liệu rất lớn.

## Bảo toàn

Trước sửa có SQLite backup API tại `backups/task11c-20261021-203359/before.sqlite3`, integrity_check=ok. Sau thử đã đối chiếu **175 tệp** gồm dữ liệu/model/artifact/thí nghiệm, requirements, SQLite thật và bốn tệp logic coverage/forecast: SHA-256 giữ nguyên. Từ baseline sau đăng nhập QA đến sau thao tác thống kê, hash toàn bộ dòng tài khoản và các bảng finance QA không đổi (`before-ui.json`, `after-ui.json`). Chỉ đăng nhập ghi last_login/session trước mốc so sánh. Không thu thập dữ liệu thật cho biểu đồ hoặc thay các kết quả nghiên cứu.

Thêm `finance/statistics.py`, `finance/test_statistics.py`, `templates/finance/includes/financial_statistics.html` và tài liệu này. Sửa view Tổng quan, template dashboard/bộ chọn tháng, CSS và README. Giữ các thay đổi TASK 11B đã có trong workspace, không ghi đè chúng. Chưa commit/push.

Đã reset viewport, đóng tab và dừng máy chủ QA sau kiểm tra. Máy chủ cục bộ cấu hình bình thường đã khởi động lại tại `http://127.0.0.1:8001/` để nhận mã mới; chỉ kiểm cổng đang nghe, không thử ghi trên DB thật. Bằng chứng UI ở trên thuộc môi trường QA. Sau thay đổi cuối chỉ làm rõ lời nhắc cuối trang, chạy lại 10 kiểm thử thống kê và system check, đều đạt.
