# TASK 09B — Kiểm tra luồng sử dụng và sao lưu mốc hiện tại

Hoàn tất báo cáo ngày **21/10/2026** (Asia/Ho_Chi_Minh). Tên thư mục sao lưu và ảnh giữ timestamp lúc bắt đầu kiểm tra: `20261020-230945`. Không thêm chức năng, sửa thiết kế thí nghiệm hoặc deploy.

## 1. Cách ly việc kiểm tra

Website thật: `http://127.0.0.1:8001/`, SQLite gốc không dùng cho thao tác thử. Tạo DB mới hoàn toàn và tài khoản `milestone_qa` trong thư mục ngoài dự án, chạy máy chủ **cổng 8002** với module settings riêng. DB, SECRET_KEY, tên session cookie và CSRF cookie của môi trường kiểm thử đều tách biệt; không sao chép tài khoản/giao dịch thật sang DB thử. Mật khẩu QA được tạo ngẫu nhiên, không dùng mật khẩu mặc định và không đưa vào tài liệu/Git.

Các thao tác ghi dưới đây được thực hiện **bằng trình duyệt**, qua biểu mẫu/nút thật trên DB thử, không dùng HTTP 200 hoặc unit test thay cho kiểm giao diện. Chỉ tạo tài khoản QA bằng ORM trong DB thử đã kiểm tra đường dẫn; danh mục, giao dịch, CSV và xác nhận tháng đều thao tác qua UI. Máy chủ QA đã dừng sau kiểm tra; không thay máy chủ thật.

Trình duyệt trong ứng dụng: desktop mặc định khoảng **1264 px chiều rộng**; viewport điện thoại **390×844 CSS px** qua khả năng viewport của trình duyệt. Đã reset viewport sau kiểm tra. Đây là kiểm responsive bằng cùng engine trình duyệt, **chưa phải thử trên thiết bị Android/iPhone hoặc Safari thật**.

## 2. Kết quả trực tiếp

| Luồng | Máy tính | Khung điện thoại | Quan sát thực tế |
|---|---|---|---|
| Đăng nhập → danh mục → giao dịch → tổng quan | Đạt | Đạt | Tài khoản QA đăng nhập được; tạo danh mục chi Groceries và danh mục thu trên desktop; điện thoại xem danh mục, sửa/lưu giao dịch và tổng quan được |
| Gợi ý → chủ động áp dụng → lưu | Đạt | Đạt | Mô tả tự đặt tiếng Anh được Pipeline thật gợi ý Groceries; chọn danh mục QA và bấm Áp dụng mới đổi biểu mẫu; bấm Lưu mới ghi giao dịch; điện thoại lặp lại được |
| CSV → xem trước → xác nhận | Đạt | Đạt | UTF-8 BOM: desktop 2 dòng, tổng thu 1.000.000 VND/chi 80.000 VND; mobile tệp khác 1 dòng chi 20.000 VND; xem trước đúng, xác nhận thành công; bản thành công không còn nút nhập lại |
| Xác nhận lịch sử → sửa giao dịch → mất xác nhận | Đạt | Đạt | CSV không tự xác nhận. Desktop tháng 09/2026 có 3 giao dịch/chi 200.000; xác nhận xong sửa 120.000 thành 130.000 → chi 210.000, trạng thái Chưa xác nhận. Mobile sau CSV có 4 giao dịch/chi 230.000; xác nhận rồi sửa thành 140.000 → chi 240.000 và mất xác nhận |
| Dự báo thiếu lịch sử | Đạt | Đạt | Tháng đích 10/2026, chưa đủ lịch sử; chỉ rõ 07, 08, 09/2026 cần kiểm tra/xác nhận; không tạo ước tính giả |
| Demo dự báo riêng | Đạt | Đạt | POST chạy logic hiện có, tháng minh họa cố định 01/2026; TB 3 tháng thắng, 7.802.124 VND; sáu hàng MAE và biểu đồ phân biệt ước tính/lịch sử; không dùng điểm thí nghiệm cũ |

Sau CSV mobile và trước lần sửa cuối, tổng quan hiển thị đúng **thu 1.000.000, chi 230.000, chênh lệch 770.000 VND**, 4 giao dịch. Đây là số liệu QA tự đặt, không phải dữ liệu tài khoản thật. Đo từ DOM ở viewport 390 px: chiều rộng document cũng 390 px, không tràn toàn trang ở tổng quan.

Điện thoại: bảng chuyển thành các khối theo dòng; menu ngang và biểu đồ demo có vùng cuộn ngang riêng. Biểu đồ cần kéo ngang để thấy tháng đích; không khẳng định toàn biểu đồ vừa một màn hình. Đã kiểm tra ảnh tổng quan và demo. Ảnh bằng chứng của biểu mẫu gợi ý, CSV, coverage trước/sau, tổng quan và demo được giữ **cục bộ** trong `qa-private/` của thư mục sao lưu; không đưa ảnh hoặc thông tin đăng nhập vào Git.

Không phát hiện lỗi ứng dụng cần sửa trong các luồng đã thử; **không thay mã chức năng trong TASK 09B**. Một lần chọn ô mật khẩu bằng nhãn tự động không khớp, đã dùng ID DOM thật; đây là vấn đề selector kiểm tra, không phải lỗi đăng nhập.

### Giới hạn kiểm tra

- Đây là smoke test các luồng chính, không phải kiểm thử mọi tổ hợp đầu vào, mọi trình duyệt hoặc tải đồng thời.
- Không lặp lại các ca CSV lỗi/rollback, CSRF, tách tài khoản, vector rỗng/Transfer bằng UI trong lượt này; các ca tương ứng đã có trong hồi quy tự động.
- Không tạo 36 tháng giao dịch để chạy ML trên trang dự báo cá nhân qua UI. Luồng này được kiểm thử tự động ở 08D; demo chỉ chứng minh quy trình tính trên chuỗi mô phỏng riêng.
- Một mô tả Groceries chạy được không chứng minh chất lượng phân loại cho tiếng Việt. Không dùng kết quả QA để sửa nhãn, mô hình hoặc các thí nghiệm đã khóa.
- Chỉ gọi chức năng demo hiện có để kiểm UI; không chạy lại script huấn luyện/thí nghiệm nghiên cứu hoặc lưu mô hình mới.

## 3. Kiểm thử được tận dụng

Mã ứng dụng không đổi so với TASK 09A: tận dụng **137/137 kiểm thử Django và 6/6 kiểm thử JavaScript đã đạt** trong lượt 09A ngay trước đó; không báo đây là một lượt hồi quy mới của 09B. Trong 09B chạy lại `manage.py check` → không có vấn đề; `makemigrations --check --dry-run` → không có thay đổi. Không chạy migrations trên DB thật ở bước này. DB thử mới được áp dụng đủ migration để kiểm độc lập.

Đối chiếu hash nội dung toàn dòng và số lượng của **8 bảng tài khoản/finance** trước/sau UI: **giữ nguyên**, gồm tài khoản, danh mục, giao dịch, CSV, MonthlyCoverage, ForecastDataVersion và ForecastResult. Không chỉ so số dòng. Requirements giữ SHA-256 `467c587b5c488e5a89350100b5ea0387c8234bbf0af3521ab15461badcd00686`.

## 4. Bản sao lưu cục bộ ngoài dự án

Thư mục:

```text
D:\SAO LUU KHOA LUAN\milestone-09b-20261020-230945
```

Nội dung chính:

- `database.sqlite3`: bản DB thật tạo bằng **SQLite connection.backup()**, không copy thô tệp đang mở. Không phục hồi đè DB hiện tại.
- `project-private/data/`: toàn bộ 118 tệp dữ liệu tải về, dữ liệu dẫn xuất, manifest chia dữ liệu, mô hình phân loại và artifact thí nghiệm đang có ngoài Git, khoảng 109,7 MB theo byte thập phân. Giữ nguyên byte; không chỉnh mô hình/kết quả.
- `project-private/secrets/`, `config/`, `requirements.txt`, `.gitignore`, `local-environment.json`: cấu hình cần thiết; bản JSON riêng chỉ giữ biến cấu hình Django liên quan nếu có, không thu token GitHub/GCM hoặc toàn bộ biến môi trường.
- `project-private/experiments/`, `docs/metadata/`: cấu hình nghiên cứu và báo cáo/metadata tổng hợp tương ứng.
- `source.bundle`: lịch sử Git đầy đủ và mã nguồn mốc sau khi commit/push; không gồm `.venv`, DB hoặc artifact riêng.
- `manifest.json`, `manifest.sha256`: tên tệp, số byte và SHA-256; `git-verification.json` ghi SHA commit/remote sau push; `git-safety-review.json` ghi kết quả rà trước khi đưa lên Git.
- `qa-private/`: môi trường/DB/CSV tự sinh và ảnh kiểm tra riêng, không phải dữ liệu thật dùng phục hồi; tách khỏi manifest artifact sản phẩm.

Bản DB và phần `project-private/` ban đầu có **141 tệp, 110.116.721 byte**; manifest cuối bổ sung Git bundle và bằng chứng Git. Không sao chép `.venv` vì có thể dựng lại từ requirements. Bản này nằm cùng ổ D: với dự án, bảo vệ trước lỗi thao tác mã nguồn nhưng **chưa bảo vệ trước hỏng/mất toàn bộ ổ đĩa**; chưa tạo bản sao ở ổ vật lý khác.

`PRAGMA integrity_check` trên bản DB trả **`ok`**. Schema có CHECK dùng hàm ngày do Django đăng ký; kết nối sqlite3 thuần ban đầu báo `unknown function: django_date_extract()`. Đã đăng ký hàm bằng `django.db.backends.sqlite3._functions.register(connection)` từ Django đang dùng, rồi chạy integrity_check thành công trên bản sao. Không nới/xóa ràng buộc hoặc sửa DB để vượt kiểm tra.

Mô hình phân loại được đối chiếu bản gốc/bản sao với SHA-256 đã đánh giá:

```text
362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345
```

Bản sao riêng chứa DB và khóa cấu hình cần phục hồi: không đưa thư mục này/manifest riêng lên GitHub hoặc chia sẻ công khai. Tài liệu này không chứa mật khẩu, token hoặc SECRET_KEY.

## 5. Rà Git và repository

Git **2.53.0.windows.2**; giữ nhánh `main`, remote `origin` sẵn có:

`https://github.com/thiennamm/khoa_luan_tai_chinh_ca_nhan.git`

GitHub API dùng credential hiện có của Git Credential Manager (không in token) xác minh tài khoản **thiennamm**, đúng repository **Private**, có quyền push. Không đổi remote/quyền truy cập, không force-push. Fetch trước khi commit cho thấy HEAD và origin/main cùng mốc ban đầu `7aa79fa`; giữ toàn bộ lịch sử.

Rà cả tệp đã theo dõi và tệp mới: không có tệp dữ liệu riêng, DB, `.venv`, `.env`, mô hình, khóa thật hoặc chuỗi credential trong danh sách dự định commit. Năm vị trí gán mật khẩu literal được kiểm tra thủ công đều là fixture của `finance/tests.py` trong DB test, không phải tài khoản website. Metadata nghiên cứu đưa lên là nguồn/hash/thống kê/đánh giá tổng hợp; không có workbook/CSV, mô hình hoặc mô tả giao dịch cá nhân. Các mã dòng lỗi phân loại tham chiếu dữ liệu tổng hợp tiếng Anh.

Commit mốc gồm mã nguồn website các TASK 08A–09A, migrations, kiểm thử, script nghiên cứu và tài liệu/kết quả tổng hợp trước đó chưa được commit. TASK 09B chỉ thêm báo cáo; không sửa thiết kế thí nghiệm. Nội dung thực tế push và xác minh SHA được cập nhật dưới đây sau thao tác Git.

## 6. Hướng dẫn phục hồi sang thư mục mới

Chưa thực hiện phục hồi; không ghi đè DB thật. Dùng thư mục mới chưa tồn tại, ví dụ `D:\KHOI_PHUC_KHOA_LUAN_09B`, và Python 3.13 như README.

1. Kiểm manifest trước. Trong PowerShell:

```powershell
$backup = 'D:\SAO LUU KHOA LUAN\milestone-09b-20261020-230945'
$manifestHash = (Get-Content -LiteralPath "$backup\manifest.sha256").Split(' ')[0]
if ((Get-FileHash -Algorithm SHA256 -LiteralPath "$backup\manifest.json").Hash.ToLowerInvariant() -ne $manifestHash) { throw 'Manifest sai hash' }
$manifest = Get-Content -Raw -LiteralPath "$backup\manifest.json" | ConvertFrom-Json
foreach ($entry in $manifest.files) {
    $path = Join-Path $backup $entry.path
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Sai hash: $($entry.path)" }
}
git bundle verify "$backup\source.bundle"
```

2. Clone mã nguồn từ bundle, chỉ vào thư mục mới:

```powershell
$restore = 'D:\KHOI_PHUC_KHOA_LUAN_09B'
if (Test-Path -LiteralPath $restore) { throw 'Chọn thư mục mới, không ghi đè' }
git clone --branch main "$backup\source.bundle" "$restore"
Copy-Item -LiteralPath "$backup\database.sqlite3" -Destination "$restore\db.sqlite3"
Copy-Item -LiteralPath "$backup\project-private\data" -Destination "$restore\data" -Recurse
Copy-Item -LiteralPath "$backup\project-private\secrets" -Destination "$restore\secrets" -Recurse
Set-Location -LiteralPath $restore
py -3.13 -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
```

3. Nếu `local-environment.json` có cấu hình riêng, đọc ở máy cục bộ và áp dụng cho tiến trình PowerShell, không chép giá trị vào chat/Git. Đường dẫn model tuyệt đối cũ cần đổi sang bản tương ứng trong thư mục phục hồi. Mặc định model nằm dưới `data/experiments/classification/task06b-v1-final/models/`, metadata ở `docs/metadata/`. Không chạy các launcher huấn luyện can thiệp DLL trong web server.

4. Kiểm DB bản phục hồi trước khi chạy web, dùng venv vừa dựng:

```powershell
@'
import sqlite3
from django.db.backends.sqlite3._functions import register
connection = sqlite3.connect('file:db.sqlite3?mode=ro', uri=True)
register(connection)
assert connection.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
print('integrity_check: ok')
'@ | & '.\.venv\Scripts\python.exe' -X utf8 -
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py showmigrations
& '.\.venv\Scripts\python.exe' -X utf8 manage.py runserver 127.0.0.1:8003
```

Không cần migrate lại nếu DB/bundle đúng mốc đã có đủ migrations. Nếu về sau dùng mã mới hơn, sao lưu DB phục hồi trước rồi mới xem xét migrate. Git bundle clone có origin là đường dẫn bundle; nếu muốn liên kết GitHub sau phục hồi, kiểm remote và tự cấu hình rõ ràng, không vô tình push vào sai nơi.

Chỉ sau khi kiểm tra bản phục hồi và người dùng chủ động quyết định mới chuyển sang sử dụng. Không xóa hoặc chép đè website gốc trong hướng dẫn này.
