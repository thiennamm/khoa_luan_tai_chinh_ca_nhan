# Sổ Thu Chi — website tài chính cá nhân

Bản tối thiểu chạy trên máy, dùng Python 3.13, Django 5.2, SQLite và Django templates. Chưa tích hợp học máy, nhập CSV hay triển khai lên Internet.

## Chạy bằng PowerShell

Mở PowerShell tại thư mục dự án. Không cần kích hoạt môi trường ảo hoặc đổi Execution Policy; gọi trực tiếp Python trong `.venv`:

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate
& '.\.venv\Scripts\python.exe' -X utf8 manage.py runserver 127.0.0.1:8001
```

Truy cập <http://127.0.0.1:8001/>. Trong phiên chuẩn bị này, máy chủ đã được mở tại cổng 8001, bạn có thể truy cập ngay. Dừng máy chủ chạy trong PowerShell bằng **Ctrl+C**. Nếu cổng 8001 đang được sử dụng khi tự chạy lại, đổi thành `127.0.0.1:8002` và truy cập cổng tương ứng. Máy chủ chỉ nghe trên máy hiện tại; bố cục hỗ trợ màn hình điện thoại khi thu nhỏ trình duyệt.

Môi trường `.venv` và `requirements.txt` hiện có được giữ nguyên. Nếu cần tạo lại môi trường sau này:

```powershell
py -3.13 -m venv .venv
& '.\.venv\Scripts\python.exe' -X utf8 -m pip install -r requirements.txt
```

## Sử dụng lần đầu

1. Chọn **Đăng ký** và tự đặt tên đăng nhập, mật khẩu. Không có tài khoản hoặc mật khẩu mặc định.
2. Mở **Danh mục**, tạo danh mục thu nhập hoặc chi tiêu của riêng bạn.
3. Chọn **Thêm giao dịch**, nhập loại, số tiền, ngày, danh mục và mô tả nếu cần.
4. Mở **Tổng quan** và chọn tháng để xem tổng thu, tổng chi, chênh lệch. Trang **Giao dịch** cũng lọc theo tháng và phân trang 20 dòng.
5. Nhấn **Xem** để xem chi tiết, sửa hoặc xác nhận xóa giao dịch. Đăng xuất bằng nút ở đầu trang.

Số tiền là **VND nguyên đồng**, từ `1` đến `999999999999999`. Khi nhập không gõ dấu chấm/phẩy phân cách hoặc ký hiệu tiền; ví dụ `150000`. Khi hiển thị, website định dạng thành `150.000 ₫`. Mọi số tiền và phép cộng trừ ở mã ứng dụng dùng `Decimal`, không dùng `float`. Tổng được cộng theo từng dòng Decimal để tránh làm tròn khi tổng lớn trên SQLite.

Chênh lệch là **tổng thu trừ tổng chi trong tháng được chọn**, có thể âm. Đây không phải số dư tài khoản ngân hàng hay số dư tích lũy của ví. Ngôn ngữ: tiếng Việt; múi giờ: `Asia/Ho_Chi_Minh`.

Danh mục phải cùng tài khoản và cùng loại thu/chi với giao dịch. Danh mục đã có giao dịch chỉ được đổi tên; không thể đổi loại hay xóa cho đến khi các giao dịch liên quan được chuyển hoặc xóa. Danh mục trùng tên và loại trong cùng tài khoản bị từ chối.

## Kiểm thử

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py makemigrations --check --dry-run
& '.\.venv\Scripts\python.exe' -X utf8 manage.py test --verbosity 2
```

Django tạo cơ sở dữ liệu kiểm thử riêng trong bộ nhớ. Các tài khoản và giao dịch trong kiểm thử chỉ là dữ liệu kiểm thử tạm thời, không được ghi vào `db.sqlite3` đang sử dụng. Các nhóm kiểm thử bao gồm đăng ký/đăng nhập/đăng xuất, CSRF, phân quyền giữa hai tài khoản, danh mục, tổng theo tháng và tiền/ngày/loại giao dịch không hợp lệ.

## Dữ liệu và cấu hình cục bộ

- `db.sqlite3`: dữ liệu thực của bạn, chỉ được tạo cấu trúc bảng khi chạy migrations; không tự thêm tài khoản, danh mục hoặc giao dịch.
- `secrets/django-secret-key.txt`: khóa ngẫu nhiên được tạo riêng cho máy ở lần chạy đầu, đã được `.gitignore` loại trừ. Có thể thay bằng biến môi trường `DJANGO_SECRET_KEY` nếu cần. Không chia sẻ khóa này.
- Mọi trang quản lý yêu cầu đăng nhập và lọc dữ liệu theo chủ sở hữu, kể cả khi nhập trực tiếp URL hoặc giả mạo ID trong biểu mẫu.
- Biểu mẫu POST sử dụng CSRF; Django kiểm tra và băm mật khẩu, quản lý phiên và escape nội dung đầu ra. Thao tác xóa và đăng xuất yêu cầu POST.
- `DEBUG` mặc định bật để phát triển cục bộ; `ALLOWED_HOSTS` chỉ cho phép localhost. Đây là cấu hình chạy máy cá nhân bằng HTTP, chưa phải cấu hình triển khai công khai.
- `.gitignore` hiện có loại trừ môi trường ảo, khóa bí mật, dữ liệu cá nhân và SQLite. Hãy sao lưu `db.sqlite3` ở nơi riêng tư trước khi tự chỉnh sửa hoặc di chuyển dữ liệu.

## Cấu trúc chính

```text
config/                 Cấu hình Django và URL gốc
finance/models.py       Danh mục, giao dịch và quy tắc dữ liệu
finance/forms.py        Biểu mẫu và giới hạn lựa chọn danh mục
finance/views.py         Các trang, CRUD và kiểm tra chủ sở hữu
finance/services.py      Tổng thu/chi Decimal theo tháng
finance/tests.py         Kiểm thử tự động
finance/migrations/      Lịch sử cấu trúc cơ sở dữ liệu
templates/               Giao diện Django tiếng Việt
static/                  CSS responsive và hỗ trợ chọn danh mục
requirements.txt         Phiên bản thư viện được giữ nguyên
```
