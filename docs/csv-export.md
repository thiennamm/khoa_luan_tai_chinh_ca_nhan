# TASK 11E — Xuất CSV theo bộ lọc

Thực hiện **21/10/2026**. Đã đọc TransactionFilterForm/apply_filters, danh sách giao dịch và parser/import CSV hiện có. Không thay dữ liệu thật, mô hình, thí nghiệm hoặc quy tắc import; không deploy hoặc commit/push.

## Sử dụng và phạm vi

Trên **Giao dịch**, đặt điều kiện và bấm **Lọc**, sau đó **Xuất CSV**. Liên kết xuất mang những điều kiện **đã áp dụng**, không phải các giá trị vừa gõ nhưng chưa bấm Lọc. Xuất toàn bộ kết quả, không chỉ 20 dòng hoặc trang hiện tại. Tệp rỗng vẫn tải được BOM + một header. Không áp giới hạn 5.000 dòng/2 MiB của chức năng nhập vào chức năng xuất; không tự cắt, bỏ hoặc gộp bản ghi.

Endpoint GET `/giao-dich/xuat-csv/` yêu cầu đăng nhập. Dùng lại **TransactionFilterForm** để validation và **apply_filters** để lọc; không có bản sao thuật toán lọc. Bắt đầu từ Transaction.objects.filter(user=request.user), không dùng user_id do trình duyệt gửi. Sắp `-date, -id` giống danh sách. `page` không phải điều kiện lọc, không được áp dụng khi xuất.

Bộ lọc sai trả **400 HTML** với lỗi của cùng form danh sách, không Content-Disposition/tệp CSV và không rơi về xuất tất cả. Nút xuất chỉ có khi bộ lọc hợp lệ. Danh mục người khác/không tồn tại nhận cùng lỗi chung. Theo tháng hoặc khoảng ngày vẫn loại trừ nhau đúng quy tắc 11B; khoảng ngày gồm cả hai biên.

## Định dạng và phản hồi

```text
date,kind,amount,category,description
```

- UTF-8, **BOM EF BB BF** ở đầu, dòng CSV kết thúc CRLF, phân cách dấu phẩy.
- Python `csv.writer` ghi header và từng bản ghi; các ô dữ liệu đều được quote, dấu nháy trong nội dung được escape đúng chuẩn CSV. Header không thêm trường nội bộ.
- Ngày ISO YYYY-MM-DD; kind income/expense; amount từ Decimal nguyên đồng, không ký hiệu, phân cách nghìn hoặc qua float. Quote quanh số trong tệp không làm đổi nội dung số khi đọc CSV.
- Category/description là văn bản, giữ tiếng Việt, dấu phẩy, nháy, xuống dòng (ngoại trừ **thêm tiền tố bảo vệ** nếu có nguy cơ). Description trống vẫn đủ năm ô.
- Không có user_id, ID giao dịch, khóa, hash mật khẩu hoặc trường nội bộ trong CSV.
- Tên tệp chỉ tạo từ ngày/tháng đã validation, ví dụ `transactions-202610.csv` hoặc `transactions-20261001-20261031.csv`; không dùng tên người dùng, chuỗi tìm hoặc tên danh mục vào header HTTP.
- StreamingHttpResponse + queryset.iterator(chunk_size=1000), không ghi tệp lên server/repository, không đưa toàn bộ bản xuất vào bộ nhớ. `chunk_size` chỉ là kích thước đọc, không phải giới hạn số giao dịch.
- Content-Type text/csv; charset=utf-8, attachment, nosniff, Cache-Control có private/no-store và Vary: Cookie. Không cho cache dùng chung các bản xuất của người dùng.

Đếm giao dịch bằng csv.reader/DictReader, không đếm dòng vật lý vì một mô tả có thể chứa xuống dòng. Không xóa các giao dịch giống nhau. Đây là ảnh dữ liệu đọc lúc xuất, không khóa snapshot của lần mở danh sách trước đó: nếu dữ liệu được sửa giữa hai thao tác, kết quả có thể thay đổi. Lỗi DB/kết nối trong lúc streaming có thể làm tải dang dở; không có cơ chế resume hay checksum cuối tích hợp trong tệp. Không bắt lỗi để âm thầm bỏ dòng. Tệp rất lớn chưa được benchmark trên máy này.

## Formula injection và tương thích

Đã tra trực tiếp ngày 21/10/2026: [OWASP CSV Injection](https://community.owasp.org/attacks/CSV_Injection) và [OWASP WSTG — CSV Injection](https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/07-Injection/21-CSV_Injection/). Hướng dẫn nêu rủi ro ký tự mở đầu công thức, giới hạn của chỉ quoting/apostrophe và cách dùng tab trong ô quoted cho luồng Excel; không có cách làm an toàn phổ quát cho mọi bảng tính hoặc save/reopen.

**Chính sách cụ thể của dự án**, chỉ áp dụng hai cột category và description:

1. Xét ký tự đầu có ý nghĩa sau khoảng trắng và control/format đầu chuỗi. NFKC chỉ dùng nhận diện ký tự mở đầu tương đương, **không dùng sửa nội dung ô**.
2. Nếu có ký tự control/format ở đầu (bao gồm tab, CR, LF, NUL, BOM/zero-width) hoặc ký tự mở đầu sau đó là `=`, `+`, `-`, `@`/biến thể fullwidth tương ứng, thêm **một tab U+0009 trước nguyên văn ô**. Khoảng trắng đứng trước dấu công thức cũng không vượt kiểm tra.
3. `csv.writer(quoting=QUOTE_ALL)` đặt toàn bộ ô vào dấu nháy và escape nháy; tab nằm bên trong ô quoted. Không coi quoting riêng là biện pháp chống công thức. Ô bình thường không bị thêm tiền tố.

Ví dụ giá trị sau khi csv.reader đọc (ký hiệu `\t` dưới đây là một tab thật trong tệp):

| Giá trị DB | Giá trị CSV đọc lại |
|---|---|
| `=1+1` | `\t=1+1` |
| `  ＋1+1` | `\t  ＋1+1` |
| `\t=1+1` | `\t\t=1+1` |
| `Tiền điện, "nhà"` | Giữ nguyên văn bản và nháy khi parse CSV |

Đây là biện pháp **hạn chế rủi ro**, không là chứng nhận tệp luôn an toàn. Chưa kiểm chứng Excel thật hoặc thao tác lưu/đóng/mở lại, LibreOffice hay mọi locale/import wizard. Cách phần mềm diễn giải UTF-8, dấu phân cách, ký tự Unicode/control hoặc bỏ ký tự đầu có thể khác nhau. Không tự mở công thức để thử; các payload kiểm thử là phép tính vô hại, không DDE/đường dẫn thực thi/liên kết mạng. Không bật nội dung hoạt động hoặc bỏ bảo vệ của phần mềm chỉ để kiểm tệp.

Tab trở thành dữ liệu, không chỉ định dạng hiển thị. **Không tuyên bố round-trip nguyên văn:** description có thể dài thêm một ký tự, tên danh mục có thể không khớp danh mục gốc; ô đang ở giới hạn 500/80 ký tự có thể vượt giới hạn nhập. Chức năng import giữ nguyên kiểm tra và **không tự gỡ tab**, không tạo ánh xạ danh mục theo tên đã loại tiền tố. Tệp lớn hơn giới hạn nhập cũng không nhập lại nguyên tệp được. Trước khi dùng cho công cụ khác, cần quy trình đối chiếu có chủ đích; không tự strip/normalize rồi coi không đổi dữ liệu.

## Kiểm thử

- **45 kiểm thử liên quan đạt**: csv-export, transaction-filters và csv-import; hồi quy **188 kiểm thử Django đạt** (178 trước + 10 mới).
- System check không lỗi; `makemigrations --check --dry-run`: không có thay đổi, không cần migrate DB thật.
- Các ca mới: BOM/header, mặc định tháng, phối hợp mọi bộ lọc, hai ngày biên, 26 dòng từ trang 2, tổng Decimal lớn chính xác/order trùng danh sách, tách tài khoản, bộ lọc sai không download, tệp rỗng, tên tệp không nhận chuỗi CRLF từ q, cache riêng/nosniff, tiếng Việt/comma/nháy/xuống dòng, các tiền tố công thức/control/fullwidth/khoảng trắng, bảo vệ cả hai cột, import không tự gỡ tab, liên kết bỏ page, chỉ đọc/đăng nhập/GET-only.

### Tải qua trình duyệt thật, SQLite QA riêng

Thư mục QA **`D:\SAO LUU KHOA LUAN\qa-11e-20261021-211804`**, SQLite mới `qa.sqlite3`, cổng **8007**, settings/secret/cookie riêng. Hai tài khoản tự sinh; không copy hoặc xuất giao dịch thật. Tài khoản A có 25 khoản chi 1.000..25.000đ (tổng 325.000đ), một khoản thu 900.000đ trong 10/2026; thêm khoản ngoài tháng để kiểm lọc. Tài khoản B có khoản chi 9.999.999đ riêng, không xuất. Category có chuỗi giống công thức; mô tả gồm tiếng Việt, nháy, newline và biến thể công thức vô hại.

| Kiểm tra UI | Kết quả thực tế |
|---|---|
| Desktop 1280×900: lọc QA XUẤT, 01–31/10, trang 2 | UI 26 kết quả/6 dòng trên trang; thu 900.000đ, chi 325.000đ, chênh lệch 575.000đ |
| Bấm Xuất CSV và bắt sự kiện download trình duyệt | Tệp nhận được, BOM đúng, **26 giao dịch**, tổng và thứ tự khớp bộ lọc; không có bản ghi tài khoản B; đủ multiline/quotes và tiền tố bảo vệ |
| Mobile 390×844: thêm loại expense/danh mục, trang 2 | UI 25 kết quả/5 dòng; bấm tải nhận đủ **25 khoản chi, 325.000đ** |
| Mobile tìm không có kết quả rồi Xuất CSV | Tệp đúng BOM + header, không có giao dịch |
| Mở URL xuất có ngày bắt đầu sau kết thúc | Trang lỗi bộ lọc, không có nút/tệp tải xuống |

Trình duyệt thực sự phát sinh download, không dùng HTTP 200 hoặc tệp dựng thủ công thay bằng chứng tải. Trình duyệt lưu vào thư mục Downloads; đã sao chép bản QA sang `desktop-export.csv`, `mobile-export.csv`, `empty-export.csv` **ngoài repository** và parse bằng Python csv.DictReader. Chưa mở các tệp bằng Excel thật. Tệp xuất QA không phải dữ liệu sản phẩm để phục hồi.

Receipt cục bộ `desktop-verification.json`, `mobile-verification.json` ghi số giao dịch, tổng tiền và SHA-256; không ghi mật khẩu. Ảnh riêng `desktop-export-page2.png`, `mobile-export.png`, `mobile-empty-export.png`, `mobile-invalid-export.png`. Mobile document 375px (trừ scrollbar) trong viewport 390px, không tràn toàn trang. Bảng responsive/lọc là logic TASK 11B dùng lại; chưa kiểm điện thoại vật lý/Safari.

## Bảo toàn và thay đổi

Trước sửa tạo SQLite backup API tại `backups/task11e-20261021-211340/before.sqlite3`, integrity_check=ok. Sau kiểm tra **172 tệp** dữ liệu/model/artifact/thí nghiệm, requirements, SQLite thật và parser import giữ nguyên SHA-256. Toàn bộ dòng trong các bảng finance QA giữ nguyên trước/sau lọc/tải (`before-ui.json`, `preservation.json`). Không có tệp xuất nào vào repository hoặc staging.

Thêm `finance/csv_export.py`, `finance/test_csv_export.py` và tài liệu này; sửa finance/urls, template danh sách và README. Không sửa bộ lọc, parser import, models, ML hoặc logic dự báo. Giữ các thay đổi trước task 11E đang có trong workspace. Không cài thư viện hoặc tạo migration.

Đã trả viewport về mặc định, đóng tab và dừng QA. Máy chủ cục bộ cấu hình bình thường đã khởi động lại tại `http://127.0.0.1:8001/` để nhận route mới, chỉ kiểm cổng đang nghe; không tải hoặc xuất dữ liệu của tài khoản thật trong lượt kiểm này.
