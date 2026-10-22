# TASK 12B — Diễn tập phục hồi mốc hiện tại

Thực hiện **21/10/2026**, giờ Việt Nam. Diễn tập thành công trên cùng máy Windows x64. Không ghi đè dự án/SQLite thật, không deploy, đổi chức năng hoặc chạy lại thí nghiệm. Mã ứng dụng và artifact phục hồi giữ nguyên byte; chỉ thêm cấu hình, công cụ kiểm tra và tài khoản QA trong bản phục hồi.

## 1. Vị trí và bản sao lưu

| Thành phần | Đường dẫn |
|---|---|
| Dự án đang dùng | `D:\KHÓA LUẬN TỐT NGHIỆP` — cổng 8001 |
| Backup mới | `D:\SAO LUU KHOA LUAN\milestone-12b-20261021-214736` |
| Bản phục hồi mới | `D:\PHUC HOI KHOA LUAN\rehearsal-12b-20261021-214736` — cổng 8003 |
| Python mới | `D:\PHUC HOI KHOA LUAN\rehearsal-12b-20261021-214736\.venv\Scripts\python.exe` |
| Bằng chứng | Thư mục `evidence` bên trong bản phục hồi |

Hai thư mục backup/phục hồi đều **chưa tồn tại trước diễn tập**, được tạo mới với timestamp; không xóa hoặc ghi đè bản sao cũ. Mở rộng quy trình TASK 11A/09B: SQLite backup API từ kết nối nguồn chỉ đọc, kiểm integrity, sao tệp riêng và khóa manifest SHA-256.

Backup có **314 tệp, 116.088.929 byte** (không tính chính manifest và tệp hash):

- `database.sqlite3`: snapshot bằng `sqlite3.Connection.backup`, không chỉ copy tệp đang chạy; `integrity_check = ok`.
- `project-private/`: mã nguồn hiện tại, templates/static, migrations, kiểm thử, scripts, requirements, tài liệu, cấu hình cục bộ `secrets/`, toàn bộ `data/` và artifact thí nghiệm hiện có. Bao gồm mã chưa commit của các task gần đây; không chỉ phục hồi commit cũ từ Git.
- `source.bundle`: lịch sử Git, tạo bằng `git bundle create --all` và kiểm bằng `git bundle verify`; không đổi remote, commit hoặc push.
- `local-environment.json`, `runtime.json`, `source-before.json`, bản helper tạo backup. Các tệp cấu hình riêng có thể chứa bí mật, không in nội dung và không đưa lên Git.
- Không sao `.venv`, `.git` đang dùng, cache Python, log, kho credential hệ điều hành hoặc các backup cũ vào backup mới.

`manifest.json` liệt kê kích thước/SHA-256 từng tệp, `manifest.sha256` khóa manifest. Đã kiểm lại đủ danh sách, kích thước và hash sau khi sao, và kiểm lại cuối diễn tập; **314/314 khớp**. SHA-256 manifest:

```text
3d389d0a65a5d4020f9c4a1416c6d10d7cea7e4309330060176d217ace1af479
```

## 2. Phục hồi và runtime độc lập

Sao `project-private` vào thư mục phục hồi mới bằng copy có kiểm hash; sao snapshot SQLite thành `db.sqlite3` ở đó. Trước khi tạo QA, hash SQLite phục hồi bằng snapshot. **308 tệp source/cấu hình/dữ liệu/artifact phục hồi khớp backup**, vẫn khớp sau thao tác trình duyệt.

Tạo `.venv` mới bằng Python nền cài trên máy:

```powershell
$restore = 'D:\PHUC HOI KHOA LUAN\rehearsal-12b-20261021-214736'
$basePython = 'C:\Users\namt2\AppData\Local\Programs\Python\Python313\python.exe'
# Đã thực hiện một lần khi .venv chưa tồn tại:
& $basePython -m venv "$restore\.venv"
& "$restore\.venv\Scripts\python.exe" -m pip --isolated install `
  --index-url https://pypi.org/simple -r "$restore\requirements.txt" `
  --disable-pip-version-check
```

Cài thành công từ PyPI/cache wheel; không cài vào hoặc chạy bằng venv gốc. Python **3.13.16**, AMD64; Django **5.2.18**, pandas **3.0.6**, scikit-learn **1.9.1**, numpy **2.5.4**, scipy **1.18.1**. Đối chiếu **14/14 gói khóa trong requirements** đúng phiên bản; `pip check` không phát hiện dependency hỏng. Chi tiết đủ 14 gói, executable/prefix và đường dẫn module nằm trong `preflight.json` của bản phục hồi. `requirements.txt` không thay đổi.

## 3. Cấu hình và ngăn dùng nhầm dự án gốc

Không sửa `config/settings.py` hoặc metadata/artifact đã sao. Thêm **chỉ trong bản phục hồi**:

- `rehearsal_settings.py`: lấy cấu hình ứng dụng hiện có nhưng ép SQLite, EN/VI model, EN/VI metadata, VI artifact manifest về chính thư mục phục hồi; kiểm tồn tại và đường dẫn sau `resolve()`. Templates/static cũng nằm trong bản phục hồi.
- `restore-secret.txt`: khóa riêng cho phiên diễn tập, không in ra báo cáo. Khóa gốc vẫn được giữ trong backup/cấu hình phục hồi nhưng không dùng cho phiên QA. Cookie riêng `restore12b_session` và `restore12b_csrf` tránh lẫn với website gốc trên cùng host khác cổng.
- `rehearsal_manage.py`: yêu cầu `sys.prefix` là venv mới, bỏ cấu hình `DJANGO_*` kế thừa, đặt `DJANGO_SETTINGS_MODULE=rehearsal_settings`. Chạy Python với `-E` để bỏ ảnh hưởng của các biến môi trường Python từ lúc khởi động.
- `verify_restore.py`: kiểm runtime/module, paths, hash, tải hai Pipeline, integrity/migration/requirements rồi mới tạo QA. Không chạy lại script này sau lần đầu vì cố ý từ chối tạo trùng tài khoản QA.
- `final_verify.py`: kiểm lại backup, source gốc, source/artifact phục hồi, SQLite và CSV xuất; không tạo thêm QA hay huấn luyện.

Các đường dẫn dưới đây tương đối với **thư mục phục hồi**, không phải dự án gốc:

| Cấu hình | Đích đã kiểm |
|---|---|
| SQLite | `db.sqlite3` |
| EN model | `data/experiments/classification/task06b-v1-final/models/char_linearsvc_C_10p0.joblib` |
| VI model | `data/experiments/classification-vietnamese/task10b-vi-v1/models/char_linearsvc_C_10.joblib` |
| EN metadata | `docs/metadata/classification-experiment-results.json` |
| VI metadata | `docs/metadata/vietnamese-classification-experiment-results.json` |
| VI manifest | `data/experiments/classification-vietnamese/task10b-vi-v1/artifact-manifest.json` |

Hash EN: `362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345`.

Hash VI: `19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55`.

Hai loader tải thành công, đúng cấu trúc đã khóa. Đã kiểm ứng dụng `finance` nạp từ bản phục hồi, Django/sklearn/pandas nạp từ venv mới; không có đường dẫn dự án gốc trong `sys.path` hoặc tệp module đã nạp. Metadata có thể giữ đường dẫn xuất xứ lịch sử trong nội dung báo cáo; không sửa chúng để làm mất provenance. Các đường dẫn **thực sự được loader sử dụng** đều thuộc bản phục hồi. Không dùng launcher hay adapter DLL của CLI.

## 4. Kiểm tra trước khi mở web

Đã chạy bằng Python mới, working directory là bản phục hồi:

```powershell
Set-Location -LiteralPath 'D:\PHUC HOI KHOA LUAN\rehearsal-12b-20261021-214736'
& '.\.venv\Scripts\python.exe' -E -m pip --isolated check
& '.\.venv\Scripts\python.exe' -E -X utf8 rehearsal_manage.py check
& '.\.venv\Scripts\python.exe' -E -X utf8 rehearsal_manage.py migrate --check
& '.\.venv\Scripts\python.exe' -E -X utf8 rehearsal_manage.py makemigrations --check --dry-run
```

Kết quả: system check không vấn đề; **0 migration chờ áp dụng**, không thay đổi model cần tạo migration; integrity SQLite `ok` trước và sau diễn tập. Không cần migrate dữ liệu mới; không chạy migration lên SQLite gốc.

Máy chủ khởi chạy ẩn trên **`http://127.0.0.1:8003/`**, dùng venv/cấu hình mới và `--noreload`. Đang giữ chạy cục bộ sau bàn giao; cổng 8001 của dự án gốc vẫn giữ nguyên. Lệnh khởi động lại sau khi tiến trình diễn tập đã dừng:

```powershell
Set-Location -LiteralPath 'D:\PHUC HOI KHOA LUAN\rehearsal-12b-20261021-214736'
& '.\.venv\Scripts\python.exe' -E -X utf8 rehearsal_manage.py runserver 127.0.0.1:8003 --noreload
```

Không khởi động thêm nếu 8003 đang được dùng. Việc khởi động lại sẽ xóa cache demo RAM theo thiết kế, không sửa artifact.

## 5. Thử bằng trình duyệt trên bản phục hồi

Tạo mới tài khoản **`restore12b_qa`** và ba danh mục QA bằng ORM sau khi preflight xác minh DB; mật khẩu ngẫu nhiên chỉ lưu tại `qa-credentials.json` cục bộ trong bản phục hồi. Không dùng tài khoản thật hoặc thay mật khẩu người dùng. Các thao tác bên dưới thực hiện qua UI thật, không dùng HTTP 200 thay kết quả thao tác.

| Bước | Kết quả thực tế | Ảnh trong `evidence/` |
|---|---|---|
| Đăng nhập | Đăng nhập QA được, ban đầu tổng quan trống | `01-login-empty.png` |
| VI | Mô tả QA “Ăn cơm trưa tại nhà hàng” → Restaurants; danh mục chưa tự đổi, chọn Ăn uống QA rồi bấm Áp dụng | `02-vi-suggestion.png` |
| Thêm giao dịch | Bấm Lưu: một khoản chi 55.000 VND ngày 21/10/2026; có thông báo thành công và trang chi tiết | `03-transaction-saved.png` |
| EN | Chọn rõ tiếng Anh, “grocery shopping at supermarket” → Groceries, hiện danh mục Đi chợ QA; không lưu thêm giao dịch từ câu EN | `04-en-suggestion.png` |
| CSV xem trước | Chọn tệp QA UTF-8 BOM qua file chooser: hai dòng, tổng thu 200.000, chi 47.000 VND, không lỗi | `05-csv-preview.png` |
| CSV xác nhận | Bấm xác nhận nhập hai giao dịch thành công, không còn nút nhập lại | `06-csv-imported.png` |
| Xuất CSV | Tải qua nút Xuất CSV; BOM/header đúng, đủ ba dòng; đọc lại bằng csv.reader đối chiếu đúng từng trường với ORM tài khoản QA | `07-export.png`, `export-qa.csv` |
| Thống kê | Thu 200.000, chi 102.000, chênh lệch thu–chi 98.000 VND; cơ cấu 55.000 + 47.000 = 102.000; danh sách ba giao dịch | `08-statistics.png`, `11-restored-overview.png` |
| Dự báo cá nhân | Tài khoản mới thiếu lịch sử nên không tạo kết quả cá nhân | `09-forecast-insufficient.png` |
| Demo | Bấm POST chạy thật baseline/Ridge trên chuỗi mô phỏng có sẵn; đích 01/2026, chọn TB3, ước tính 7.802.124 VND | `10-demo-result.png`, `demo-ui.json` |
| Kết thúc | Đăng xuất QA thành công, đóng tab kiểm thử | — |

Demo hiển thị MAE validation làm tròn: TB3 **313.374**, tháng trước **429.598**, cùng tháng năm trước **460.418**; Ridge alpha 0,1/1/10 tương ứng **384.149 / 382.519 / 386.393 VND**. Đây là kết quả chạy mới của demo, không lấy từ báo cáo cũ, không ép Ridge thắng. Demo dùng fit tạm trong RAM trên dữ liệu mô phỏng theo chức năng đã có; **không huấn luyện/refit lại mô hình phân loại hoặc chạy lại/sửa artifact thí nghiệm**. Sau demo, tài khoản QA vẫn chỉ có ba giao dịch, **0 coverage và 0 kết quả dự báo cá nhân**.

Các câu VI/EN trên chỉ kiểm hoạt động suy luận/phục hồi, không là đánh giá chất lượng độc lập. Không chọn ngưỡng, sửa nhãn hoặc đưa giao dịch QA vào tập huấn luyện.

## 6. Đối chiếu dữ liệu và bằng chứng cuối

- **309/309 tệp gốc đã lập baseline không đổi**, gồm 308 tệp mã/cấu hình/dữ liệu/artifact và SQLite thật; không dùng DB thật cho thao tác QA. Tài liệu TASK 12B là tệp mới tạo sau snapshot, không thuộc baseline.
- SQLite gốc trước/sau cùng SHA-256: `edad70207e212c2230385db433c6a20c81e6e323e61f76f3497cb4979bf261fc`.
- **308/308 tệp source/artifact trong bản phục hồi vẫn khớp backup**, bao gồm hai mô hình và dữ liệu thí nghiệm.
- Đối chiếu từng bản ghi đã có theo khóa chính: `auth_user` và bảy bảng `finance_*` trong SQLite phục hồi vẫn khớp snapshot ban đầu. Chỉ tài khoản/danh mục/giao dịch/import/phiên và bộ đếm riêng của QA được thêm trong bản phục hồi.
- Export có đúng ba dòng, thu 200.000/chi 102.000 VND, khớp ORM; không có dữ liệu của tài khoản đã sao từ nguồn trong export QA.
- `preflight.json`, `evidence/final-verification.json`, `evidence/demo-ui.json` lưu kết quả máy đọc được; `evidence/evidence-manifest.json` ghi hash các ảnh và bằng chứng cố định. Log runtime lưu cục bộ, không chép mô tả giao dịch hay bí mật vào báo cáo.
- Không chạy lại 188 kiểm thử hồi quy vì không sửa mã ứng dụng; lần đạt gần nhất là TASK 12A. Lần này kiểm runtime mới, cấu hình, migration, integrity và các luồng UI nêu trên. Không gọi kết quả cũ là kiểm thử đã chạy trong venv mới.

## 7. Lỗi và giới hạn

Không gặp lỗi chặn phục hồi, sai hash, thiếu gói hoặc lỗi loader trong diễn tập. Không cần hạ/nâng phiên bản hay sửa ứng dụng gốc. Việc ép đường dẫn, tách cookie và dùng khóa phiên riêng là cấu hình cách ly chủ động, không phải âm thầm sửa lỗi dự án.

- Backup/phục hồi cùng ổ vật lý D: kiểm được quy trình nhưng chưa bảo vệ trước hỏng/mất ổ đĩa; backup chứa SQLite/cấu hình riêng, cần giữ kín và không đưa lên Git.
- Dùng Python nền 3.13.16 đã cài trên cùng máy, gói PyPI/cache có sẵn; backup không đóng gói bộ cài Python hoặc wheelhouse đầy đủ. Chưa chứng minh phục hồi hoàn toàn ngoại tuyến trên máy mới.
- Chỉ thử trình duyệt hiện có trên máy; chưa thử Windows khác, Linux, điện thoại thật hoặc mở CSV bằng Excel thật. CSV đã kiểm bằng parser và đối chiếu bản ghi.
- Chưa diễn tập hỏng một phần backup, nâng schema, concurrent restore, khôi phục sau mất ổ hoặc chuyển máy chủ production; không triển khai trực tuyến.
- Bản phục hồi chứa cả dữ liệu sao lưu thật và dữ liệu QA mới, chỉ là môi trường diễn tập. Không chép SQLite đã thử trở lại dự án gốc. Muốn dùng lại bản sạch cần tạo **thư mục mới khác** từ snapshot nguyên vẹn và kiểm manifest trước.
- Báo cáo này được viết sau khi khóa backup nên chưa nằm trong `project-private` của snapshot 12B; có bản sao báo cáo cùng bằng chứng trong bản phục hồi. Không thêm tệp vào backup đã niêm phong.
