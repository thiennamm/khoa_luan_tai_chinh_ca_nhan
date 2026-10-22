# TASK 11D — Tên đăng nhập và mật khẩu

Ngày thực hiện: **21/10/2026**. Đã đọc cấu hình auth, User mặc định, form đăng ký/đăng nhập, validators và mã PasswordChangeForm/UsernameField của Django 5.2 đang cài. Không đổi thông tin tài khoản thật, model/migrations, dữ liệu tài chính, ML hoặc kết quả thí nghiệm. Không deploy hoặc commit/push.

## Cách sử dụng

Mở **Tài khoản** từ menu, URL `/tai-khoan/`, yêu cầu đăng nhập. Trang hiển thị tên hiện tại và hai form POST riêng, có CSRF:

1. **Đổi tên đăng nhập**: nhập tên mới và mật khẩu hiện tại. Thành công quay lại trang này và hiện tên mới; lần đăng nhập sau dùng tên mới với mật khẩu hiện tại.
2. **Đổi mật khẩu**: mật khẩu hiện tại, mật khẩu mới và xác nhận. Dùng các validators Django hiện có: độ dài tối thiểu, độ giống thông tin người dùng, mật khẩu phổ biến và chỉ số. Thành công giữ phiên hiện tại; phiên khác mất hiệu lực khi auth kiểm tra lại ở yêu cầu sau.

GET chỉ hiển thị, bỏ qua action hoặc dữ liệu đổi tên đặt trên query string; không đổi tên/mật khẩu. POST action không hợp lệ trả 400 và thông báo. Form không liên quan không bị bind hoặc yêu cầu điền chung. Không có tính năng quên mật khẩu, email phục hồi hoặc thay thông tin của tài khoản khác. Không cần chạy migrate vì schema không đổi.

## Đổi tên và bảo toàn dữ liệu

`UsernameChangeForm` lấy cấu hình trường username từ model User hiện có: tối đa 150 ký tự, bộ UnicodeUsernameValidator/model validators và `UsernameField` chuẩn hóa **NFKC**. Ví dụ chữ fullwidth được chuẩn hóa trước kiểm trùng. Giữ quy tắc uniqueness/collation hiện tại của User trên SQLite, không tự đổi thành mô hình tài khoản phân biệt khác về hoa/thường.

Kiểm tên trùng bằng truy vấn loại chính PK của người hiện tại; không nhận user_id hoặc target từ form. Mật khẩu hiện tại được kiểm bằng `check_password`, không so mật khẩu nguyên văn với DB. Lưu trong transaction, **chỉ UPDATE username**, theo PK và hash mật khẩu đã xác nhận. Nếu hash bị đổi đồng thời thì không đổi tên, yêu cầu tải lại trang. Không ghi đè các trường quyền, password, email hoặc trường tài khoản khác từ dữ liệu POST.

Nếu tên bị người khác chiếm sau bước validation, ràng buộc unique của DB vẫn chặn; IntegrityError được bắt bên ngoài transaction rollback, trả lỗi tại tên mới. Nếu DB đang bận, trả lỗi chung để thử lại. Không tiết lộ nội dung SQL hoặc dữ liệu tài khoản khác. Chỉ đặt tên trên object request.user sau khi UPDATE thành công.

Không tạo User mới để thay tài khoản, không đổi PK hoặc các khóa ngoại. Danh mục, giao dịch, MonthlyCoverage, lô/receipt CSV, ForecastDataVersion và ForecastResult vẫn trỏ đúng ID ban đầu. Đổi tên không vô hiệu forecast vì dữ liệu tài chính/trạng thái xác nhận không đổi. Phiên hiện tại vẫn xác thực; phiên khác không bị buộc đăng xuất chỉ vì đổi tên, vì Django nhận diện theo PK/hash, không theo username.

## Mật khẩu, phiên và log

Form tiếng Việt kế thừa **PasswordChangeForm**; không viết thuật toán kiểm tra/đặt password riêng. Form gọi cơ chế set_password của Django, lưu hash và dùng `update_session_auth_hash(request, user)` sau thành công. Django quay session key và cập nhật auth hash của phiên hiện tại. Các phiên khác còn auth hash cũ bị middleware auth loại ở lần kiểm tra sau; không tuyên bố mọi session row đã bị xóa tức thì.

Không lưu mật khẩu nguyên văn, không ghi password vào log ứng dụng, URL, thông báo hoặc receipt. Các trường PasswordInput mặc định render_value=False và autocomplete current-password/new-password phù hợp. Dữ liệu POST nhạy cảm được đánh dấu `sensitive_post_parameters()` để bộ báo lỗi Django che toàn bộ POST. Response Tài khoản không cache. Thành công redirect về URL cố định `/tai-khoan/`, không mang mật khẩu/next do client gửi. Những cơ chế này không thay thế cấu hình DEBUG/HTTPS đúng khi triển khai; bước này tiếp tục chỉ dùng localhost.

## Kiểm thử tự động

**10 kiểm thử mới đạt**, rồi hồi quy **178 kiểm thử Django đạt** (168 trước + 10 mới). Không dùng DB thật. Sau tinh chỉnh cuối chỉ bỏ autofocus mặc định ở form mật khẩu để không giành focus khi form đổi tên báo lỗi, chạy lại 10 kiểm thử liên quan và system check. `makemigrations --check --dry-run`: không thay đổi schema.

Các ca gồm:

- GET có tham số đổi tên vẫn chỉ đọc; cần đăng nhập; hai form tách biệt; trang không cache.
- Sai mật khẩu hiện tại, tên rỗng/khoảng trắng/ký tự sai/quá dài, tên trùng và tên fullwidth trùng sau NFKC.
- Lưu tên chuẩn hóa, chỉ username đổi; ID/quyền/hash ban đầu và tài khoản khác giữ nguyên; tên cũ không đăng nhập, tên mới đăng nhập được; phiên khác vẫn tồn tại sau chỉ đổi tên.
- Mô phỏng tên bị chiếm sau validation gây unique constraint thật: rollback, thông báo lỗi và DB tiếp tục đọc được; hash mật khẩu bị đổi giữa xác nhận và UPDATE thì chặn đổi tên.
- Mật khẩu hiện tại sai, mật khẩu quá yếu/số, xác nhận lệch: hash không đổi; ô mật khẩu không có value khi render lỗi.
- Đổi password thành công: hash khác plaintext, mật khẩu cũ không đăng nhập được, mật khẩu mới dùng được; quay session key, giữ phiên hiện tại, phiên thứ hai bị loại khi GET trang yêu cầu auth.
- Gửi user_id/quyền/username/password ngoài form không đổi tài khoản đích hoặc quyền; tài khoản B chỉ đổi chính B.
- So toàn bộ dòng của các bảng dữ liệu liên kết (kể cả coverage, CSV, counter, forecast cache) trước/sau cả hai thao tác: không đổi.
- CSRF cho cả hai action, action lạ, đánh dấu POST nhạy cảm và redirect không chứa dữ liệu bí mật.

## QA thực tế và phân biệt API/UI

SQLite mới: **`D:\SAO LUU KHOA LUAN\qa-11d-20261021-210331\qa.sqlite3`**, cổng **8006**, settings/SECRET_KEY/session cookie/CSRF cookie riêng. Hai tài khoản QA, mật khẩu cũ/mới ngẫu nhiên chỉ giữ trong credentials.json cục bộ; không ghi vào tài liệu/Git. Dữ liệu tài chính QA là tự đặt, không copy DB thật.

### Qua Django Client trên SQLite QA (không phải thao tác trình duyệt)

Đã chạy lại chính view/form với CSRF được bật, Host localhost: đăng nhập QA gốc → POST đổi tên sang `qa11d_changed` → đăng nhập tên cũ bị từ chối → đăng nhập tên mới/mật khẩu cũ được → mở phiên thứ hai → POST đổi password → phiên hiện tại vẫn vào Tài khoản, phiên thứ hai redirect đăng nhập → mật khẩu cũ bị từ chối, mật khẩu mới được chấp nhận. Giữ đúng PK và hash toàn bộ dữ liệu liên kết, tài khoản B không đổi. Receipt `api-smoke.json` ghi kết quả/không ghi password. Đây là bài kiểm tích hợp qua client, **không trình bày thành đã bấm đổi thành công qua UI**.

### Qua trình duyệt thật

| Kiểm tra | Kết quả |
|---|---|
| Desktop 1280×900, đăng nhập bằng thông tin QA mới | Đăng nhập thành công, menu Tài khoản mở được |
| Trang Tài khoản desktop | Hiện `qa11d_changed`, hai form độc lập, nhãn/help tiếng Việt, password trống |
| Gửi tên hiện tại không đổi kèm mật khẩu xác nhận sai | Báo “Mật khẩu hiện tại không đúng”, không đổi tên, mọi ô password trống sau lỗi |
| Mobile 390×844 | Hai form xếp dọc, lỗi đọc được, document 375px (trừ scrollbar), không tràn toàn trang |
| Đăng xuất, thử tên QA cũ/mật khẩu cũ | Bị từ chối qua form đăng nhập thật |
| Thử tên QA mới/mật khẩu cũ | Bị từ chối qua form đăng nhập thật |
| Thử tên QA mới/mật khẩu mới | Đăng nhập thành công trên mobile, mở được Tài khoản và hiển thị tên mới |

**Giới hạn UI:** chưa tự động bấm đổi thông tin mới thành công qua trình duyệt. Quy tắc của công cụ điều khiển trình duyệt yêu cầu người dùng trực tiếp nhập và xác nhận thông tin đăng nhập mới. Vì vậy các ca đổi thành công/phiên nêu trên được thực hiện bằng kiểm thử tự động và Django Client trong SQLite QA; UI đã kiểm bố cục, thông báo lỗi và đăng nhập bằng thông tin đã đổi. Không dùng điều này để tuyên bố mọi luồng thay đổi đã kiểm qua UI. Nếu cần diễn tập nút đổi thành công, người dùng tự thao tác trên QA riêng, không trên tài khoản thật. Chưa kiểm thiết bị vật lý/Safari hoặc mọi tình huống mạng/ghi đồng thời.

Ảnh riêng: `desktop-account.png`, `desktop-invalid-current.png`, `mobile-account-error.png`, `mobile-old-login-rejected.png`, `mobile-account-new-login.png`. Chỉ có dữ liệu kiểm thử; không đưa ảnh/credential lên Git.

## Bảo toàn và tệp

Trước sửa: SQLite backup API tại `backups/task11d-20261021-205507/before.sqlite3`, integrity_check=ok. Đối chiếu dữ liệu/model/artifact/thí nghiệm, requirements và SQLite thật trước/sau: giữ nguyên hash. Không chạy lại thí nghiệm hoặc TASK 10D. Các thay đổi TASK 11B/11C đang có được giữ nguyên.

Xác minh cuối: **171 tệp được bảo vệ giữ nguyên hash**, dữ liệu tài chính QA giữ nguyên hash so với trước thay đổi tên/password. Bằng chứng riêng ở `preservation.json` trong thư mục QA. Đã reset viewport, đóng tab và dừng máy chủ QA; máy chủ cục bộ cấu hình bình thường đã khởi động lại tại `http://127.0.0.1:8001/` để nhận menu/route mới, chỉ kiểm cổng đang nghe, không đổi thông tin của tài khoản thật.

Thêm `finance/account_forms.py`, `finance/account_views.py`, `finance/test_account_management.py`, `templates/registration/account.html` và tài liệu này; sửa config/urls, menu base, CSS và README. Giữ nguyên model User, schema và mọi trường dữ liệu tài chính. Không tạo tài khoản mặc định hoặc đổi tên/mật khẩu cho người dùng thật.
