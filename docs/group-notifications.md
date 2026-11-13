# TASK 24A — Thông báo Chia tiền nhóm

Chuông cạnh tài khoản mở `/thong-bao/`. Số trên chuông đếm các mục chưa đọc của chính tài khoản; số được cập nhật khi tải trang hoặc sau khi mở một thông báo. Danh sách sắp mới trước, 20 mục/trang. Không cần JavaScript để mở và đọc thông báo. Không gửi email, thông báo đẩy hoặc làm mới tự động.

| Sự kiện | Người nhận | Nơi mở |
|---|---|---|
| Gửi lời mời | Tài khoản được mời | Biểu mẫu xử lý đúng lần mời, có lựa chọn chấp nhận hoặc từ chối. Lời mời đã chấp nhận mở sổ nhóm và hiện thông báo trạng thái. |
| Chốt khoản đã trả | Từng thành viên có phần chia | Chi tiết khoản chi và trạng thái phần chia, kể cả phần đã được xử lý hoặc khoản đã hủy. Xem trước không gửi thông báo. |
| Gửi đề nghị hoàn trả | Người cần xác nhận đã nhận tiền | Chi tiết đúng khoản hoàn trả, hiện trạng thái hiện tại, kể cả đề nghị đã xử lý hoặc hết hạn. |

Khi bấm một mục, POST có CSRF chỉ đánh dấu mục đó đã đọc và chuyển tới trang nghiệp vụ. Luồng xác nhận riêng của nhóm vẫn kiểm quyền và yêu cầu người dùng tự quyết định. Mục đã mở vẫn xem lại được; thời điểm đọc đầu tiên không bị ghi đè. Nếu người nhận đã mất quyền xem, lời mời đã bị thu hồi hoặc đã có lần mời mới, hệ thống giải thích và đưa về danh sách Chia tiền nhóm. Mở mục thuộc tài khoản khác trả 404.

Thông báo được tạo trong cùng transaction với thao tác gửi lời mời, chốt khoản hoặc đề nghị hoàn trả. Receipt của nhóm và ràng buộc duy nhất của bảng thông báo ngăn nhân bản khi gửi lại. Dữ liệu lưu người nhận, tham chiếu tới đúng một đối tượng, lần mời nếu có, thời điểm tạo và đọc; không sao chép tên nhóm, mô tả giao dịch hoặc số tiền. Hai index phục vụ truy vấn đếm và danh sách theo tài khoản. Thanh đầu trang thêm một truy vấn đếm, không tăng theo số thành viên, giao dịch hoặc ngày.

Migration `finance.0017_group_notification` phụ thuộc `0016_group_ledger`, thêm bảng mới, khóa ngoại và index. Không backfill thông báo cho dữ liệu cũ. Trước khi chạy bản mã mới cần áp dụng migration bằng quy trình backup/triển khai của dự án. Reverse xóa bảng và lịch sử thông báo; không dùng reverse thay bản sao lưu. Đã kiểm migration trên SQLite và PostgreSQL QA. SQLite thật và Render vẫn chưa áp dụng migration này.

## Kiểm tra local

- Django trên SQLite QA: **547 đạt, 9 bỏ qua, 0 lỗi** trong 556 bài (gồm 7 bài riêng cho thông báo). System check không có vấn đề, `makemigrations --check --dry-run` không phát hiện thay đổi, `collectstatic` thành công và CSS mới trả HTTP 200. Không thay JavaScript.
- QA riêng: [Danh sách thông báo](http://127.0.0.1:8034/thong-bao/). Dùng hai tài khoản mô phỏng ở hai phiên trình duyệt.
- HTTP qua Waitress với CSRF và hai phiên thật: B mở lời mời và phần chia, mỗi lần đếm **1 → 0**; A mở đề nghị hoàn trả, đếm **2 → 1** vì còn thông báo phần chia của A. Đã xác minh trang đích và đối tượng vẫn chờ sau khi bấm mở. Sau xác nhận hoàn trả, mở lại thấy **Đã xác nhận**. A không thấy lời mời của B trong danh sách và gửi POST vào URL của B nhận **404**.
- QA còn thông báo chưa đọc để thử: B có lời mời và một phần chia, A có đề nghị hoàn trả và phần chia của A.
- Trình duyệt trong ứng dụng mở được form đăng nhập. Clipboard cục bộ không truyền vào clipboard của công cụ. Cài đặt viewport 390×844 đo thực tế thành 582×1259, nên **chưa xác minh trực quan giao diện thông báo ở desktop hoặc 390px**. Có thể kiểm trên trình duyệt thường: mở QA, đăng nhập, dùng DevTools Responsive, xác nhận `innerWidth`/ `innerHeight` đúng khung, bấm chuông và kiểm số, chữ, vùng bấm và không tràn ngang.

Database, cấu hình, tài khoản thử và biên nhận `qa-result.json` nằm trong thư mục QA local ngoài Git.

## TASK 24B — Kiểm tra trước phát hành

PostgreSQL 18.6 chạy trong cluster QA mới, chỉ nghe ở `127.0.0.1:55434`. Dùng mã bản phát hành `9c18f1f` để tạo database ở 0016 rồi ghi dữ liệu mô phỏng có giao dịch, ví, phần chia, hoàn trả, phân bổ hoàn trả và dòng tiền ví. Cấu hình kiểm địa chỉ, cổng, tên database và thư mục cluster ngay khi kết nối.

- Kế hoạch chỉ có `0017_group_notification`. Sau migrate, số dòng và SHA-256 của dữ liệu cũ trong **37 bảng** (16 bảng có dữ liệu) khớp trước/sau. Tổng thu giữ **500.000 VND** và tổng chi giữ **300.000 VND**. Bảng thông báo mới có **0 dòng**, 4 khóa ngoại đã xác thực và 8 index hợp lệ. Django thêm đúng một loại nội dung và bốn quyền mặc định cho model mới. Lượt đối chiếu đầu của script QA tính nhầm các dòng metadata mới vào dữ liệu cũ. Đã sửa phép so sánh và chạy lại trên database QA khác từ 0016.
- System check đạt, không có migration chờ và `makemigrations --check --dry-run` không phát hiện thay đổi.
- Tập kiểm thử thông báo và Chia tiền nhóm trên PostgreSQL có **58 đạt, 3 bỏ qua, 0 lỗi** trong 61 bài. Cả 7 bài thông báo đều đạt.
- HTTP qua Waitress trên PostgreSQL, với hai phiên đăng nhập riêng và CSRF. B mở đúng lời mời và đúng chi tiết phần chia, số chưa đọc mỗi lần giảm **1 → 0**. A mở đúng hoàn trả **40.000 VND**, số giảm **2 → 1**. Nội dung vẫn chờ sau khi mở. Xác nhận hoàn trả bằng thao tác riêng rồi mở lại thấy **Đã xác nhận**. A không thấy thông báo của B trong danh sách. POST mở lời mời hoặc phần chia của B trả **404**, thời điểm đọc của B vẫn trống.
- Biên nhận migration và HTTP lần lượt là `migration-result.json` và `qa-result.json` tại `D:\POSTGRESQL QA\task24b-notifications-pg`, ngoài repository.

Công cụ điều khiển Edge ở TASK 24B dừng vì không xác định được URL cửa sổ. Hai phiên HTTP đã xác minh luồng và phân quyền. Kết quả giao diện được bổ sung bằng xác nhận kiểm tay của người dùng ở TASK 24C.

## TASK 24C — Chuẩn bị phát hành

Người dùng xác nhận kiểm tay đạt trên [QA 8034](http://127.0.0.1:8034/thong-bao/) ở desktop **1280×900**, mobile **390×844** và khi thao tác bằng **Tab/Enter**. Biên bản ghi theo xác nhận của người dùng. Không có số đo DOM riêng để ghi lại.

Ứng viên chỉ đưa chuông, danh sách thông báo, liên kết từ ba sự kiện Chia tiền nhóm và migration `0017_group_notification` vào bản nền `9c18f1f418990303da3e0030af621d5437c18768`, mốc Live của đợt Chia tiền nhóm. Khi kiểm lại ứng viên, dùng PostgreSQL QA từ 0016, đối chiếu dữ liệu cũ, tải CSS đã qua `collectstatic` và mở đủ ba loại thông báo qua hai phiên có xác thực.

Thứ tự sau khi duyệt, theo [quy trình bảo trì Render](render-maintenance.md) và [hướng dẫn sao lưu PostgreSQL](production-verification.md):

1. Xác nhận lại SHA Live, nhánh, PostgreSQL đích và trạng thái Auto-Deploy trong Dashboard. Bật bảo trì và kiểm trang công khai trả 503. Dừng các tác nhân có thể ghi trực tiếp vào database trong cửa sổ bảo trì.
2. Sao lưu PostgreSQL, giữ archive ngoài Git, kiểm `pg_restore --list` và SHA-256. Khôi phục vào database QA rỗng, xác minh đúng đích rồi đối chiếu số dòng, liên kết và tổng thu–chi. Chỉ triển khai khi bản khôi phục khớp.
3. Đưa đúng SHA đã duyệt lên `main` bằng fast-forward, chọn deploy đúng SHA trong bảo trì. Theo dõi build đóng gói CSS và startup áp dụng `finance.0017_group_notification`. Xác minh SHA Live, migration đã ghi nhận và không còn migration chờ.
4. Đối chiếu dữ liệu cũ bằng kết nối chỉ đọc. Kiểm CSS và trang thông báo qua phiên vận hành được phép. Nếu cần kiểm ba sự kiện có ghi dữ liệu online, dùng hai tài khoản thử riêng khi có phép. Mở lại web sau khi kiểm đạt. Khi có lỗi, giữ bảo trì và quyết định cách xử lý dựa trên log và trạng thái database. Reverse 0017 xóa lịch sử thông báo, nên cần giữ bản sao trước triển khai.
