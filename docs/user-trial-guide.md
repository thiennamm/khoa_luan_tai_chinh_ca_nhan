# Dùng thử Sổ Thu Chi trong 10–15 phút

Tài liệu TASK 21A, ngày 29/10/2026. Chỉ dùng địa chỉ/bản dùng thử do chủ dự án chỉ định và **tài khoản thử riêng**. Bản QA đã kiểm trên máy không có nghĩa bản online đã được kiểm. Người dùng thử không cần chạy migration, đổi cấu hình hoặc cung cấp quyền truy cập database.

Tự chọn tên đăng nhập và mật khẩu thử; không dùng lại mật khẩu quan trọng. **Không gửi mật khẩu cho chủ dự án hoặc trong phản hồi.** Chỉ nhập các khoản giả theo ví dụ dưới đây; không cần sao kê, số tài khoản, thông tin ngân hàng hoặc dữ liệu tài chính thật. Các số tiền là tình huống minh họa, không phải khuyến nghị chi tiêu.

## Kịch bản chính

| Thời gian | Thao tác | Điều cần quan sát |
|---|---|---|
| 0–2 phút | Chọn Đăng ký, điền form rồi bấm **Tạo tài khoản**; sau đó đăng nhập bằng tài khoản vừa tạo | Đăng ký thành công chuyển về Đăng nhập, không tự đăng nhập. Tài khoản mới chưa có giao dịch là trạng thái bình thường |
| 2–4 phút | Mở Danh mục → Thêm danh mục mẫu. Xem trước, chọn **Lương** và **Giáo dục**, rồi Xác nhận thêm mục đã chọn | Chỉ tạo các danh mục đã chọn; chưa có giao dịch hoặc tiền demo. Có thể tự tạo một danh mục chưa ánh xạ và dùng bình thường |
| 4–7 phút | Thêm khoản **Thu nhập**, `5.000.000`, ngày hôm nay, danh mục Lương, mô tả `Lương giả để dùng thử`. Lưu | Trang chi tiết hiện 5.000.000 VND. Chỉ bấm Lưu mới tạo giao dịch |
| 7–9 phút | Mở Thêm giao dịch. Nhập nhanh `Chi: Đóng học phí 45k hôm nay`, bấm Điền vào biểu mẫu; kiểm tra ngày, loại, 45.000 VND và mô tả | Có thông báo **Đã điền, chưa lưu**. Nếu form đã có dữ liệu, phải xác nhận thay thế; Giữ dữ liệu hiện tại không ghi đè |
| 9–11 phút | Chọn **VI — Tiếng Việt**, bấm Gợi ý danh mục. Đọc kết quả; nếu phù hợp, chọn danh mục rồi bấm **Áp dụng danh mục đã chọn**. Nếu không phù hợp hoặc chưa ánh xạ, chọn Giáo dục thủ công. Sau đó tự bấm **Lưu giao dịch** | Danh mục không tự thay chỉ vì vừa có gợi ý. Đổi mô tả/loại/chế độ cần yêu cầu gợi ý mới. Kiểm tra form trước khi lưu |
| 11–13 phút | Từ chi tiết khoản chi, mở **Tạo giao dịch tương tự**. Kiểm tra ngày mặc định hôm nay; đổi tiền thành `25.000` và mô tả thành `Khoản giả thứ hai`, rồi Lưu | Mở form chưa tạo bản ghi. Lưu tạo giao dịch mới; khoản nguồn 45.000 VND giữ nguyên |
| 13–15 phút | Mở Giao dịch, chọn đúng tháng và lọc Chi tiêu; sau đó mở Tổng quan → Báo cáo tháng | Nếu chỉ làm đúng các bước trên: thu **5.000.000 VND**, chi **70.000 VND**, chênh lệch **4.930.000 VND**, 3 giao dịch. Khi lọc chỉ Chi: thu 0, chi 70.000, chênh lệch −70.000 VND. Báo cáo có thể chọn toàn bộ chi tiết rồi In / Lưu PDF |

Nếu bạn sửa/xóa/thêm khoản khác, hãy tính lại kỳ vọng theo các khoản đã lưu. Chênh lệch thu–chi **không phải số dư ngân hàng hoặc tiền tiết kiệm**. Ngày/tháng chưa có bản ghi không chứng minh không phát sinh chi tiêu ngoài website.

## Hiểu gợi ý và dự báo

- Gợi ý ML có thể sai. Nhãn mô hình là liên kết tùy chọn, không phải danh mục bắt buộc. Chỉ ánh xạ khi ý nghĩa phù hợp; không tìm được thì để **Chưa ánh xạ**. Không chọn nhãn gần tên cho đủ.
- Tiếng Việt học từ tập mô phỏng nhỏ do AI biên soạn; tiếng Anh dùng dữ liệu tổng hợp. Chưa có bằng chứng đại diện người dùng Việt Nam. Một vài câu dùng thử đúng không phải đánh giá độc lập hoặc tỷ lệ chất lượng thực tế.
- Muốn thử tiếng Anh, chủ động đổi EN và dùng một mô tả tiếng Anh giả. Không có tự nhận diện ngôn ngữ hoặc tự đổi model khi lỗi. Transfer cần xem lại bản chất giao dịch; không tự coi là thu hay chi.
- **Phản hồi phân loại** phản ánh lựa chọn người dùng, không phải nhãn đúng đã kiểm định. Chỉ có bản ghi khi lưu thành công với gợi ý hợp lệ và danh mục cuối có nhãn để so sánh. Không có phản hồi cũng có thể là hành vi đúng; không tự học từ thao tác này.
- Tài khoản mới mở Dự báo sẽ **Chưa đủ lịch sử**. Cần ít nhất 3 tháng liên tiếp đã kết thúc và được xác nhận đầy đủ, kết thúc ngay tháng trước. Không xác nhận một tháng thật chưa ghi đủ chỉ để mở tính năng.
- Có thể mở **Demo dự báo → Demo dự báo**: đây là dữ liệu mô phỏng riêng, tháng đích cố định 01/2026, không phải dự báo hiện tại của bạn. Phương pháp được chọn có thể là baseline. MAE validation không phải cam kết sai số tương lai.
- Từ 3–35 tháng hợp lệ, cá nhân dùng trung bình 3 tháng, không gọi là ML. Từ 36 tháng mới so sánh baseline/Ridge. Dự báo là ước tính tổng khoản chi ghi trong website; không dùng giao dịch tháng hiện tại làm đầu vào.

## Tùy chọn sau lượt chính

Không cần làm hết trong 15 phút; chọn một mục phù hợp:

1. **CSV:** vào Giao dịch → Nhập / xuất CSV, tải mẫu header. Chuẩn bị vài dòng giả theo [quy ước nhập CSV](csv-import.md), kiểm lỗi theo số dòng và mẫu xem trước, rồi mới xác nhận. Tệp nhập lại cùng hash bị chặn; không phải bộ phát hiện mọi giao dịch trùng. Xuất CSV theo bộ lọc hiện tại, gồm toàn bộ kết quả, không chỉ trang đang xem. Không gửi tệp có dữ liệu thật để báo lỗi.
2. **Ngân sách:** đặt ngân sách tổng 100.000 VND. Với hai khoản chi trên, đã ghi nhận 70.000 VND, còn lại 30.000 VND. Không cộng ngân sách tổng với ngân sách danh mục thành một hạn mức.
3. **Tiết kiệm:** tạo mục tiêu giả, ghi đóng góp 50.000 VND. Đây là phân bổ tự ghi nhận; tổng thu–chi ở trên không đổi. Website không giữ hộ tiền hoặc tự trích tiền từ tài khoản.
4. **Định kỳ/lịch:** khai báo một khoản dự kiến. Chưa bấm xác nhận Ghi nhận thì tổng thực tế không đổi; Bỏ qua không tạo giao dịch. Mở Lịch thu–chi để phân biệt Dự kiến/Đã ghi nhận. Mobile ưu tiên ngày có mục; bật **Hiện cả ngày trống → Xem lịch** nếu muốn xem từng ngày.
5. **In:** xem báo cáo đúng tháng, chọn chi tiết nếu cần, bấm In / Lưu PDF rồi chọn Save as PDF trong trình duyệt. Kiểm trang trước khi lưu. Đây là dữ liệu đang có, không phải chứng từ ngân hàng hay snapshot bất biến.

Khi tắt JavaScript, form thường, CSV, bộ lọc, lịch và báo cáo vẫn dùng được. Nhập nhanh/gợi ý cần JavaScript và có nhắc riêng; in dùng Ctrl+P/menu In. Nếu kết nối bị gián đoạn sau thao tác tài chính, kiểm danh sách/trạng thái trước khi gửi lại; không bấm liên tục.

## Gửi phản hồi sau khi tự thử

Ghi lại theo mẫu; **không điền mật khẩu, cookie, token, URL kết nối database hoặc thông tin tài chính thật**:

```text
Tên bước / trang:
Trình duyệt, máy tính hay khung mobile (nếu biết):
Ngày giờ và tháng đang chọn:
Các bước thực hiện (chỉ dùng mô tả/số tiền giả):
Kết quả mong đợi:
Kết quả thực tế:
Có lặp lại được không:
Ảnh đính kèm đã che tên tài khoản/thông tin riêng tư:
Điểm gây khó hiểu hoặc gợi ý cải thiện:
```

Chỉ gửi phản hồi bằng kênh bạn đã thống nhất với chủ dự án. Tài liệu không tự gửi lời mời/tin nhắn, không thu thập credential và không tạo danh mục/giao dịch khi bạn chỉ mở trang.
