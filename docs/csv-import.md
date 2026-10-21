# TASK 08B — Nhập giao dịch CSV có xem trước

## Định dạng và cách sử dụng

Trong **Giao dịch → Nhập CSV có xem trước**, chọn **Tải mẫu CSV chỉ có header**. Endpoint yêu cầu đăng nhập, trả UTF-8 với đúng một dòng, không có tài khoản/giao dịch mẫu:

```text
date,kind,amount,category,description
```

- UTF-8, chấp nhận BOM ở đầu tệp; dấu phẩy phân cách. Header phải đúng thứ tự, chữ thường và đủ năm cột; từ chối cột thêm như `user_id`.
- `date`: đúng `YYYY-MM-DD`, ngày có thật; không nhận giờ, dạng ngày rút gọn hoặc tự sửa ngày.
- `kind`: đúng `income` hoặc `expense`, không tự sửa hoa/thường hoặc khoảng trắng.
- `amount`: chỉ chữ số ASCII, giá trị nguyên đồng VND lớn hơn 0, tối đa 15 chữ số có nghĩa theo giới hạn model. Không nhận dấu `+/-`, dấu phân cách hàng nghìn, phần thập phân, ký hiệu tiền, dạng mũ, NaN hoặc Infinity. Giá trị được đọc và cộng bằng Decimal, không qua float.
- `category`: tên danh mục thuộc người đang đăng nhập, đúng loại thu/chi. So khớp bằng `casefold()` trên tên, không bỏ khoảng trắng hay suy nhãn ML. Nếu có nhiều danh mục cùng khóa tên và loại, báo không xác định duy nhất, yêu cầu đổi tên/CSV. Không chọn theo danh mục đầu tiên hoặc danh mục của người khác, không tự tạo danh mục.
- `description`: tùy chọn, tối đa 500 ký tự theo model hiện có; để trống vẫn phải giữ cột. Nội dung được giữ nguyên, không dịch hoặc học từ dữ liệu này. Ô có dấu phẩy/xuống dòng phải đặt trong dấu nháy kép; dấu nháy kép bên trong ô được viết thành hai dấu nháy kép theo chuẩn CSV.
- Giới hạn **2.097.152 byte (2 MiB)** và **5.000 giao dịch** mỗi lần. Không tin đuôi tệp hoặc MIME: tệp `.csv` chứa nhị phân/sai header vẫn lỗi; nội dung CSV hợp lệ với đuôi khác vẫn được kiểm tra bình thường. Handler chặn byte vượt giới hạn trước khi chuyển thêm vào bộ nhớ/tệp tạm Django; parser cũng kiểm tra kích thước độc lập.

Luồng: **Tải tệp → Kiểm tra → Xem trước → Xác nhận nhập toàn bộ**. Tải tệp chưa ghi giao dịch. Tệp trống, chỉ có header, sai UTF-8, NUL, cú pháp CSV sai, sai số cột hoặc dòng trắng đều cần sửa. Không bỏ qua dòng trắng, không tự sửa trường lỗi. Tệp vượt số dòng bị dừng ở bản ghi thứ 5.001 và không được xác nhận.

Số dòng trong lỗi/cảnh báo là **dòng vật lý bắt đầu bản ghi**: header dòng 1, giao dịch thường bắt đầu dòng 2; ô có xuống dòng được tính đầy đủ. Tối đa 100 lỗi và 100 cảnh báo được hiển thị, kèm tổng số thông báo. Bản xem trước hiển thị tối đa 20 giao dịch hợp lệ; tổng thu/chi chỉ tính các dòng hợp lệ của tệp, không phải tổng tài khoản. Chỉ khi toàn bộ tệp hợp lệ mới có nút xác nhận; không cho nhập phần hợp lệ của một tệp còn lỗi.

## Lưu tạm, hạn dùng và bảo vệ dữ liệu

`CsvImportBatch` lưu UUID ngẫu nhiên, chủ sở hữu, SHA-256 byte tệp gốc, payload nhị phân gốc, danh sách ID danh mục đã đối chiếu, thời điểm/hạn dùng/trạng thái. Payload ở **SQLite phía máy chủ**, không đặt trong cookie/session, hidden input, URL hoặc static. Trình duyệt chỉ gửi UUID lô qua URL và CSRF khi xác nhận; không gửi lại toàn bộ giao dịch để máy chủ tin theo.

Lô có hạn **30 phút** kể từ lúc tải. Hết hạn không hiển thị payload hoặc cho xác nhận, yêu cầu tải lại. Payload được xóa ngay khi nhập thành công. Lô hết hạn được dọn theo hai cách:

1. Khi POST tải tệp, dọn các lô hết hạn của chính tài khoản đó.
2. Chủ máy chạy lệnh sau để dọn mọi lô hết hạn, ví dụ lúc bắt đầu/kết thúc buổi làm việc:

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py cleanup_csv_imports
```

Chưa thiết lập bộ lập lịch tự chạy. Hạn xác nhận được kiểm tra theo thời gian thực; việc xóa vật lý payload hết hạn chờ một trong các lần dọn trên. Lệnh không xóa tài khoản, danh mục, giao dịch hoặc dấu vết hash thành công. Khi lô bị dọn, URL xem trước không còn tồn tại.

`CsvImportReceipt` giữ tối thiểu tài khoản/hash/thời điểm/số giao dịch và liên kết lô nếu còn tồn tại; không giữ mô tả hoặc tên tệp. SQLite, backup và tệp dữ liệu tiếp tục được `.gitignore` loại trừ. Không log nội dung CSV, tên danh mục hoặc mô tả; lỗi cơ sở dữ liệu được trả bằng thông báo chung. Dữ liệu xem trước được Django escape, trang có header không cache; không xử lý mô tả như công thức hoặc HTML.

Các endpoint mẫu/tải/xem trước/xác nhận yêu cầu đăng nhập; mọi truy vấn lô và danh mục đều giới hạn theo tài khoản. Tài khoản khác xem hoặc POST UUID của lô nhận 404. Xác nhận chỉ nhận POST, có CSRF; GET không nhập. Luồng không sửa/xóa giao dịch cũ, không gọi ML hoặc dự báo, không coi khoảng ngày trong CSV là lịch sử thu chi đầy đủ.

## Xác nhận nguyên tử và chống nhập hai lần

Trong một `transaction.atomic()`:

1. Câu lệnh đầu tiên là UPDATE có điều kiện `user + UUID + pending + chưa hết hạn` sang `processing`. Trên SQLite đây là khóa ghi thực; không dựa vào `select_for_update()` vì SQLite không hỗ trợ khóa hàng.
2. Đọc lại dữ liệu phía máy chủ, xác minh hash payload, kiểm tra hạn dùng và phân tích lại toàn bộ CSV với các danh mục hiện tại của đúng tài khoản/loại.
3. Đối chiếu ID danh mục với bản xem trước ban đầu. Nếu danh mục bị đổi tên, loại, chủ sở hữu, xóa, có thêm tên gây nhập nhằng hoặc bị thay bằng ID khác, chặn lô. Không âm thầm chuyển sang danh mục mới trùng tên.
4. Tạo dấu vết thành công với ràng buộc duy nhất `(user, sha256)`, ghi toàn bộ giao dịch đã kiểm tra bằng `bulk_create` chia lô nhỏ, rồi đánh dấu hoàn tất và xóa payload tạm.

Nếu lỗi ở bất kỳ bước nào, mọi giao dịch mới, dấu vết thành công và trạng thái claim đều rollback. Dữ liệu cũ không bị cập nhật. Trạng thái lô và ràng buộc hash chặn cả bấm xác nhận lại lẫn hai bản xem trước của cùng tệp. Nếu SQLite đang bận/khóa, phản hồi yêu cầu kiểm tra lại trạng thái/thử lại; không đánh dấu thành công khi chưa commit.

## Trùng dữ liệu và các giới hạn

Khóa cảnh báo giao dịch giống nhau gồm ngày, loại, Decimal số tiền, ID danh mục, mô tả nguyên văn. Kiểm tra cả trùng trong tệp và trùng với giao dịch đang có của người dùng. Chỉ cảnh báo theo dòng; **không xóa, gộp hoặc bỏ bản ghi trùng**. Mọi bản ghi hợp lệ vẫn được thêm khi người dùng chủ động xác nhận.

Nhận diện tệp đã nhập thành công bằng SHA-256 **byte gốc**, theo từng tài khoản, và chặn nhập lại. Một tài khoản khác vẫn được nhập tệp đó nếu danh mục của họ đáp ứng quy tắc. Chỉ tải/xem trước chưa tạo dấu vết thành công. Dọn lô tạm hoặc tự xóa giao dịch sau này không xóa dấu vết hash và không mở lại quyền nhập tệp đó. Giao diện không có nút bỏ qua chặn hash.

Thay BOM, xuống dòng, thứ tự dòng hoặc nội dung khiến hash khác. Đây **không phải** cơ chế phát hiện mọi giao dịch trùng giữa các tệp khác nhau. Cảnh báo theo các trường cũng không chứng minh hai giao dịch là một: không có mã giao dịch ngân hàng để xác nhận. Người dùng phải tự xem lại khi các bản xuất có phần lịch sử giao nhau.

## Tệp thay đổi

- `finance/models.py`: hai model lô tạm và dấu vết hash; không sửa schema giao dịch cũ.
- `finance/migrations/0003_csvimportbatch_csvimportreceipt.py`: tạo hai bảng mới, không seed/backfill.
- `finance/forms.py`: biểu mẫu chọn tệp/giới hạn dung lượng.
- `finance/csv_import.py`: parser, Decimal, cảnh báo, lưu tạm, xác nhận và dọn.
- `finance/csv_views.py`, `finance/urls.py`: endpoint mẫu/tải/xem trước/xác nhận.
- `finance/upload_handlers.py`, `config/settings.py`: chặn tệp vượt giới hạn khi nhận dữ liệu. Hiện chỉ có luồng upload CSV trên website.
- `finance/management/commands/cleanup_csv_imports.py` và các `__init__.py` hỗ trợ: lệnh dọn.
- `templates/finance/csv_upload.html`, `csv_preview.html`, `includes/csv_inspection.html`: giao diện định dạng, lỗi/cảnh báo và xem trước.
- `templates/finance/transaction_list.html`, `static/css/app.css`: lối vào nhập CSV và bố cục responsive.
- `finance/test_csv_import.py`: kiểm thử mới.
- `finance/test_category_migration.py`: vẫn kiểm tra migration nhãn 08A, bổ sung khôi phục các migration mới nhất sau kiểm thử để không làm thiếu bảng ở các test khác.
- `README.md`, `docs/csv-import.md`: hướng dẫn và tài liệu này. Không cần sửa `.gitignore`; mẫu CSV được tạo động từ header cố định, không có bản ghi mẫu được commit.

## Kiểm tra thực tế

Lệnh dùng Python hiện có trong `.venv`, không cài thư viện, không thay đổi requirements:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 manage.py test --verbosity 1
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py makemigrations --check --dry-run
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate
```

Các ca mới dùng test DB riêng: BOM, chỉ header, sai encoding/nhị phân/cú pháp/header/cột, không tin MIME/đuôi, số tiền/ngày/loại/danh mục/mô tả không hợp lệ, dòng đa dòng, giới hạn byte và số dòng, nhập đủ 5.000 dòng, tổng Decimal lớn, mẫu 20 dòng, tên nhập nhằng, tách tài khoản, hết hạn/dọn, giữ receipt sau dọn, kiểm tra lại danh mục/hash, trùng hợp lệ, chặn lại tệp và POST lặp, CSRF/đăng nhập/escape HTML, rollback sau một lần ghi từng phần và hai xác nhận đồng thời (cùng UUID hoặc hai UUID cùng hash). Không tạo tài khoản/giao dịch mẫu trong SQLite đang dùng.

Kết quả: **73 kiểm thử Django đạt** (49 kiểm thử cũ và 24 kiểm thử CSV mới), **6 kiểm thử JavaScript gợi ý phân loại đạt**. `manage.py check` không có lỗi; `makemigrations --check --dry-run` không còn thay đổi; migration `0003_csvimportbatch_csvimportreceipt` đã áp dụng thành công. Chạy lệnh dọn trên máy sau migration: 0 lô hết hạn, không đổi dữ liệu cũ. Đã mở trang nhập CSV bằng phiên trình duyệt đang đăng nhập và xác nhận có hướng dẫn định dạng, mẫu header, giới hạn và nút kiểm tra/xem trước. Các ca ghi giao dịch chỉ chạy trong test DB riêng, không tải tệp cá nhân hoặc tạo giao dịch thử trên website đang dùng.

Trước migration đã tạo backup SQLite riêng tại `backups/task08b-20261020-210543/`. Sau migration, đối chiếu hash/số dòng/ID trên các cột cũ của bảng tài khoản, danh mục và giao dịch: giữ nguyên. Đối chiếu 78 tệp requirements, cấu hình/kết quả thí nghiệm, metadata, script thí nghiệm và artifact mô hình: hash không đổi. Backup và dữ liệu không được đưa vào Git.
