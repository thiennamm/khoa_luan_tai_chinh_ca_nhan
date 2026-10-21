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

Commit mốc **`5acc75a15a39cd0815dfeadafcd1e7694f0ac2a6`** đã push thành công lên `origin/main`; ngay sau push, `git rev-parse HEAD` và `git ls-remote --heads origin main` trả cùng SHA này. Commit gồm mã nguồn website các TASK 08A–09A, migrations, kiểm thử, script nghiên cứu và tài liệu/kết quả tổng hợp trước đó chưa được commit (88 tệp thay đổi so với mốc cũ). TASK 09B chỉ thêm báo cáo; không sửa thiết kế thí nghiệm.

Commit tiếp theo chỉ chốt kết quả xác minh trong báo cáo này. SHA cuối nhánh và SHA remote sau lần push cuối được giữ trong `git-verification.json` ở bản sao lưu; không tự ghi SHA của chính commit vào nội dung commit. `source.bundle` được tạo sau lần push cuối và kiểm tra bằng `git bundle verify`.

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
```

2. Clone mã nguồn từ bundle, chỉ vào thư mục mới:

```powershell
$restore = 'D:\KHOI_PHUC_KHOA_LUAN_09B'
if (Test-Path -LiteralPath $restore) { throw 'Chọn thư mục mới, không ghi đè' }
git clone --branch main "$backup\source.bundle" "$restore"
git -C "$restore" bundle verify "$backup\source.bundle"
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

## 7. TASK 09C — Kiểm tra UI dự báo cá nhân đủ 36 tháng

Thực hiện **21/10/2026**, theo Asia/Ho_Chi_Minh. Phần này bổ sung giới hạn “chưa thử 36 tháng qua UI” của TASK 09B; giữ nguyên kết quả và bản sao lưu 09B như một mốc lịch sử.

### Môi trường và kịch bản cố định

- DB mới hoàn toàn tại `D:\SAO LUU KHOA LUAN\qa-09c-20261021-091445\qa.sqlite3`, máy chủ kiểm thử cổng **8002**. Dùng settings, SECRET_KEY, session cookie và CSRF cookie riêng; không dùng DB/tài khoản thật ở cổng 8001.
- Hai tài khoản kiểm thử riêng **forecast_qa_a**, **forecast_qa_b**, mật khẩu ngẫu nhiên giữ riêng. Không thêm các tài khoản này vào DB thật hoặc Git.
- Tài khoản A có **36 tháng mô phỏng liên tiếp, 10/2023–09/2026**, một khoản expense tự sinh mỗi tháng, Decimal VND nguyên dương. Tài khoản B không có lịch sử/kết quả. Không có khoản tháng hiện tại hoặc tương lai trong fixture.
- Seed **9093** được cố định trước khi tính, chỉ dùng một seed; công thức xu hướng + mùa vụ + nhiễu nguyên, đủ tham số và 36 tổng tháng được lưu riêng trong `scenario.json` ngoài Git. Không lấy chuỗi MoneyData hoặc dữ liệu thật, không thử seed để Ridge thắng.
- SHA-256 chuỗi gốc (JSON danh sách `month` ISO/`expense` chuỗi Decimal, sort_keys=True): `e679eff03f411b7939742b21298ef4a4eaa3f19cc6427acb8fc6077bdec2260b`.
- Fixture khởi tạo **35 tháng đầu đã complete, tháng 09/2026 chưa xác nhận**, chưa có ForecastResult. Đây là trạng thái tự đặt của môi trường thử, không phải người dùng thật xác nhận. Tháng cuối được xác nhận và xác nhận lại qua UI thật. Không giả định đã bấm xác nhận cả 36 tháng bằng trình duyệt.
- Tháng đích được lấy từ dịch vụ `current_month()` theo giờ Việt Nam lúc chạy: **10/2026**, không phải 11/2026. Sáu tháng validation: **04/2026–09/2026**.

### Luồng trực tiếp và đối chiếu dịch vụ

Thao tác trình duyệt gồm đăng nhập, bấm xác nhận tháng, POST **Tính dự báo**, sửa giao dịch, chuyển trang và đăng xuất/đăng nhập tài khoản thứ hai. Không dùng status HTTP thay cho kiểm tra UI.

| Mục kiểm tra | Kết quả thực tế |
|---|---|
| Chưa đủ xác nhận | Dù fixture có 36 khoản, tháng cuối chưa xác nhận khiến đoạn hợp lệ kết thúc đúng tháng trước là 0; UI báo thiếu 09/2026, không có nút Tính dự báo và không có bảng/kết quả |
| Xác nhận tháng còn thiếu | Bấm xác nhận 09/2026 rồi vào Dự báo: UI nhận đúng **36 tháng liên tiếp** |
| POST tính dự báo cá nhân | Tính được tổng tháng **10/2026**; lần đầu chọn **Ước tính theo tháng trước**, kết quả **6.564.426 VND**. UI ghi đây là thống kê, không phải Machine Learning |
| So sánh baseline/Ridge | Đủ **6 hàng**: ba baseline và Ridge alpha 0.1, 1, 10; đúng giai đoạn validation. Đọc các ô DOM và đối chiếu toàn bộ với kết quả dịch vụ, đúng phương pháp được chọn và cách làm tròn VND |
| Sửa giao dịch lịch sử | Sửa khoản thuộc 09/2026 bằng UI: coverage trở về **Chưa xác nhận**; trang dự báo báo kết quả trước hết hiệu lực, ẩn hoàn toàn ước tính và bảng cũ, không có nút tính khi thiếu lịch sử |
| Xác nhận lại | Khi vừa xác nhận lại đủ 36 tháng, kết quả cũ vẫn bị ẩn; chỉ sau khi bấm **Tính dự báo** mới có kết quả mới hợp lệ |
| Tính lại qua các lượt sửa | Các kết quả sau ba lần thay đổi cố định lần lượt **6.664.426**, **6.764.426**, **6.864.426 VND**; phương pháp vẫn là baseline tháng trước. Không sửa mô hình để đổi kết quả |
| Tách tài khoản | Đăng xuất A, đăng nhập B và vào cùng `/du-bao/`: chỉ có trạng thái thiếu lịch sử của B, không có bảng hoặc ước tính của A. Đối chiếu DB thử: B không có transaction, coverage hoặc ForecastResult; kết quả A vẫn tồn tại riêng |

Đối chiếu tính toán: gọi lại trực tiếp **`calculate(snapshot(A)['history'])`**, không gọi view HTTP thay cho UI. So sánh với ForecastResult do POST trình duyệt tạo: tháng đích, fingerprint, phương pháp, ước tính nguyên đồng khớp; MAE thô của từng ứng viên khớp trong dung sai **0.001 VND**. Bảng DOM khớp từng ô với `METHOD_LABELS` và bộ định dạng `vnd` của dịch vụ. Đã đối chiếu chuỗi ban đầu, kết quả sau lượt sửa mobile và kết quả desktop cuối; trên cùng dữ liệu cuối, đổi viewport không đổi bảng/kết quả và không bấm tính lại.

MAE validation dưới đây là **kết quả tổng hợp của dữ liệu kiểm thử**, không phải điểm MoneyData hoặc đánh giá chất lượng thực tế:

| Phương pháp | Chuỗi gốc, MAE VND hiển thị | Sau lượt sửa desktop cuối, MAE VND hiển thị |
|---|---:|---:|
| Trung bình 3 tháng | 317.427 | 367.427 |
| Tháng trước — được chọn | **298.778** | **348.778** |
| Cùng tháng năm trước | 487.785 | 537.785 |
| Ridge alpha 0.1 | 394.609 | 444.609 |
| Ridge alpha 1 | 394.928 | 444.928 |
| Ridge alpha 10 | 397.266 | 447.266 |

Ridge chạy thật trong dịch vụ nhưng không được chọn vì MAE lớn hơn baseline. Không dùng decision score, % chính xác, khoảng tin cậy hoặc cam kết sai số tương lai.

### Kích thước và bằng chứng

Đã kiểm cả **desktop đặt rõ 1280×900** và **khung điện thoại 390×844**. Ở mỗi kích thước, đã thử trạng thái chưa xác nhận sau sửa, ẩn cache cũ, xác nhận lại, tính mới, bảng kết quả và tài khoản B. Các lượt ban đầu ở kích thước mặc định khoảng 638 px là kiểm bổ sung; không dùng chúng thay cho lượt desktop 1280 px.

UI desktop có sidebar và bảng sáu hàng. UI điện thoại xếp bảng thành từng khối có nhãn; đọc được phương pháp, MAE và lựa chọn. Đo từ DOM: mobile viewport/document đều **390 px**, desktop viewport **1280 px**, document **1265 px** (phần còn lại là scrollbar); không phát hiện tràn ngang toàn trang ở trang dự báo. Đã trả viewport về mặc định và dừng máy chủ kiểm thử sau khi xong.

Toàn bộ ảnh/fixture/DB/metadata nằm riêng trong thư mục `qa-09c-20261021-091445` nêu trên, không thêm vào Git. Các bằng chứng chính:

- `11-stale-desktop-1280.png`: tháng mất xác nhận, kết quả cũ bị ẩn.
- `12-result-desktop-1280.png`: dự báo cá nhân đủ lịch sử, kết quả cuối và sáu MAE.
- `08-stale-mobile.png`, `09-recomputed-mobile.png`: vô hiệu và tính lại trên mobile.
- `13-same-result-mobile.png`: cùng kết quả/dữ liệu với desktop cuối, chỉ đổi viewport.
- `06-account-b-mobile.png`, `14-account-b-desktop-1280.png`: tài khoản B không thấy kết quả A.
- `verified-original.json`, `verified-final.json`, `verified-desktop-1280.json`: đối chiếu dịch vụ/cache trên các phiên bản chuỗi thử.
- `original-ui-check.json`, `final-ui-check.json`, `desktop-mobile-comparison.json`: đối chiếu bảng DOM/ước tính với dịch vụ.
- `evidence-manifest.json`: hash các bằng chứng và xác nhận bảo toàn dữ liệu thật; không chứa mật khẩu hoặc khóa dưới dạng văn bản báo cáo.

### Kết luận và giới hạn của lượt 09C

Không phát hiện lỗi cần sửa, **không thay mã ứng dụng/mô hình/thí nghiệm/migrations/requirements**. Chỉ bổ sung phần báo cáo này; không commit/push trong TASK 09C. Không chạy lại toàn bộ hồi quy vì mã không đổi; kết quả 137 Django + 6 JavaScript trước đó vẫn được tham chiếu theo đúng lượt chạy ở 09A, không tính thành kiểm thử mới.

Đã đối chiếu **8 bảng tài khoản/finance trong DB thật** trước/sau bằng số lượng và hash toàn bộ nội dung dòng: không đổi. Hash tất cả tệp đã theo dõi trước khi ghi báo cáo cũng không đổi. DB mới/khóa/cấu hình tài khoản QA chỉ nằm ngoài dự án.

Đây là kiểm UI và tính nhất quán trên **chuỗi tự sinh** của tài khoản thử, không chứng minh dự báo tốt cho người dùng thật. Vẫn chưa kiểm thiết bị điện thoại vật lý hoặc Safari, tình huống tải đồng thời qua UI và mọi cấu hình người dùng; không tuyên bố thêm phạm vi đó.
