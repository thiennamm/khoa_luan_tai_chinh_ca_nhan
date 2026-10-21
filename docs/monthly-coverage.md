# TASK 08C — Mức đầy đủ của lịch sử theo tháng

## Ý nghĩa và sử dụng

Trang **Lịch sử ghi chép** (`/lich-su-ghi-chep/`) lọc theo năm, hiển thị các tháng lịch đã kết thúc theo `Asia/Ho_Chi_Minh`. Mỗi dòng có tháng, tổng chi VND đã ghi, số giao dịch thu và chi, trạng thái và thời điểm xác nhận hiện hành nếu có.

Ba trạng thái theo từng tài khoản/tháng:

| Mã | Hiển thị | Ý nghĩa |
|---|---|---|
| `unknown` | Chưa xác nhận | Mặc định, kể cả khi chưa có bản ghi trạng thái |
| `incomplete` | Chưa đầy đủ | Người dùng cho biết chưa ghi đủ |
| `complete` | Đã xác nhận đầy đủ | Người dùng chủ động xác nhận tháng đó |

Đây là **lời xác nhận của người dùng**, không phải hệ thống chứng minh độ phủ. Không suy ra sự đầy đủ từ số giao dịch, khoảng ngày của CSV, ngày giao dịch đầu/cuối hoặc việc không có giao dịch. Thay đổi trạng thái không thêm, sửa, xóa hoặc gán nhãn cho giao dịch.

Người dùng chọn **Xác nhận đầy đủ** để mở trang xem lại tổng chi/số giao dịch rồi POST xác nhận có CSRF. Nếu không có khoản chi đã ghi, kể cả tháng chỉ có thu nhập, trang hỏi đúng **“Bạn xác nhận tháng này không có khoản chi?”** và yêu cầu checkbox riêng. Không tự coi số 0 quan sát là tháng không có chi. **Chưa đầy đủ** và **Hủy xác nhận** cũng là POST có CSRF; GET chỉ xem, không đổi trạng thái. Mọi thao tác dùng người đang đăng nhập, không nhận chủ sở hữu từ POST.

Tháng hiện tại/tương lai không được xác nhận đầy đủ, kể cả gửi POST thủ công hoặc gọi dịch vụ. Ranh giới tháng lấy múi giờ Việt Nam rõ ràng, không theo múi giờ trình duyệt/UTC hoặc một timezone khác đang được activate. Trang theo năm chỉ liệt kê tháng đã kết thúc; năm tương lai hiển thị trạng thái trống.

## Lưu trữ và migration

`MonthlyCoverage` gồm FK `user`, `month` (ngày đầu tháng), `status`, `confirmed_at`. Không có dòng trạng thái tương đương `unknown`; không tạo bù trạng thái khi đọc hoặc khi nhập CSV.

Ràng buộc cơ sở dữ liệu:

- Duy nhất `(user, month)`.
- Ngày phải là ngày 1, trạng thái thuộc đúng ba mã.
- `complete` bắt buộc có `confirmed_at`; `unknown`/`incomplete` bắt buộc thời điểm này là NULL.

Quy tắc tháng đã kết thúc được kiểm tra trong model và dịch vụ vì phụ thuộc thời gian hiện tại. Khi hủy, đánh dấu chưa đầy đủ hoặc giao dịch thay đổi, xóa thời điểm xác nhận hiện hành. Đây không phải bảng lưu toàn bộ lịch sử các lần xác nhận.

Migration `0004_monthlycoverage` chỉ tạo bảng mới và các ràng buộc, không backfill/seed, không sửa bảng tài khoản, danh mục, giao dịch hoặc lô CSV. Chạy bằng Python hiện có:

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate
```

## Bao phủ các đường ghi dữ liệu

Không đặt việc hủy xác nhận riêng ở view. Những đường hiện có đã được rà soát: ModelForm.save trong thêm/sửa, Model.delete trong xóa, `bulk_create` trong `confirm_batch` của CSV, cùng các API queryset thường dùng.

| Đường ghi | Cơ chế | Tháng mất xác nhận |
|---|---|---|
| `Transaction.save` / `objects.create` / ModelForm.save | Atomic tại model, đọc bản cũ và bản thực sự đã lưu | Chủ sở hữu/tháng cũ và mới |
| `QuerySet.update`, gồm biểu thức F | QuerySet tùy chỉnh, atomic, chụp ID và đọc lại giá trị đã lưu | Tất cả cặp tài khoản/tháng trước và sau |
| `bulk_update` | Django gọi QuerySet.update ở trên | Các tháng trước/sau của bản ghi cập nhật |
| `bulk_create` thông thường | QuerySet tùy chỉnh, atomic | Mọi tháng có bản ghi mới |
| Model.delete / QuerySet.delete / xóa cascade | `post_delete` đăng ký qua AppConfig.ready, nằm trong atomic của Django Collector | Tài khoản/tháng của từng bản ghi xóa |
| CSV thành công | `confirm_batch` vẫn atomic toàn lô; bulk_create đi qua manager chung | Mọi tháng thật sự có dòng nhập, kể cả dòng thu nhập |
| CSV chỉ tải/xem trước hoặc nhập thất bại | Không có bản ghi giao dịch mới được commit | Không đổi trạng thái |

Tất cả thay đổi giao dịch đều được xử lý bảo thủ, kể cả sửa mô tả hoặc bấm lưu lại không thay giá trị: tháng liên quan trở về `unknown`, thời điểm NULL. Các tháng không bị tác động và tài khoản khác giữ nguyên. Khi `save(update_fields=...)`, tháng mới lấy từ bản đã lưu, không lấy ngày thay đổi trong bộ nhớ nhưng chưa được ghi.

Hook không tạo trạng thái cho tháng chưa có dòng: mặc định của tháng đó vốn là `unknown`. Không sửa danh mục hoặc giao dịch cũ để thực hiện việc reset. Đổi tên/nhãn ánh xạ của danh mục không thay dữ liệu giao dịch hoặc tổng tiền và không tự đặt trạng thái.

`save`, queryset update/bulk_create và thay đổi trạng thái dùng cùng database/transaction. UPDATE trạng thái không đổi giá trị được đặt trước việc đọc trong các transaction ghi để lấy khóa ghi SQLite ngay từ đầu, kể cả khi chưa có dòng trạng thái; không dựa vào `select_for_update` trên SQLite. Xóa sử dụng transaction của Collector. Nếu reset trạng thái lỗi, việc ghi/xóa giao dịch cũng rollback. Nếu toàn bộ import rollback sau khi đã ghi một phần/all dòng và reset, trạng thái/thời điểm cũ cũng được khôi phục.

Bulk insert không hỗ trợ `ignore_conflicts`, `update_conflicts` hoặc tùy chọn vị trí; cần dùng insert thông thường với tham số đặt tên như CSV hiện có. Không có đường raw SQL/`_raw_delete` ghi giao dịch trong website. Những API nội bộ bỏ qua ORM/signal hoặc sửa SQLite trực tiếp không nằm trong cơ chế này; nếu thêm đường ghi mới sau này phải dùng lớp ghi chung và bổ sung kiểm thử. Lệnh flush/migration không được coi là thao tác người dùng.

## Trang xác nhận cũ và tính nhất quán

Trang xem lại tạo token có chữ ký Django chứa tài khoản, tháng và hash của các trường giao dịch liên quan. Token không chứa mô tả/bản ghi nguyên văn, không được dùng làm bằng chứng độ phủ. Khi POST xác nhận, dịch vụ giữ khóa ghi, đọc lại các giao dịch và so hash với token (hạn 30 phút). Nếu sai tài khoản/tháng, token hỏng/hết hạn hoặc dữ liệu đổi, yêu cầu mở lại để xem. Trường hợp xóa khoản chi cuối cùng sau khi mở trang cũng không thể bỏ qua câu hỏi tháng không có chi.

Nếu xác nhận commit trước một thay đổi giao dịch, hook thay đổi sau đó reset. Nếu giao dịch đổi trước xác nhận, token cũ bị từ chối. Dịch vụ đọc tổng hợp dùng transaction đọc để tổng tiền và trạng thái thuộc cùng một snapshot SQLite. Không ghi mô tả hoặc giao dịch vào log phục vụ việc kiểm tra token.

## Dịch vụ lịch tháng chuẩn bị cho dự báo

API nội bộ trong `finance/coverage.py`:

```python
monthly_history(user, first, last)
```

`first` và `last` là `datetime.date` ngày đầu tháng, khoảng **bao gồm cả hai đầu**. Thứ tự tăng dần, giữ mọi tháng liên tiếp, tự cắt tháng hiện tại/tương lai khỏi kết quả. Nếu cả khoảng nằm trong hiện tại/tương lai, trả danh sách rỗng. Không tự chọn khoảng lịch sử từ ngày giao dịch đầu/cuối.

Mỗi phần tử có:

| Trường | Kiểu / ý nghĩa |
|---|---|
| `month` | date đầu tháng |
| `recorded_expense` | Decimal tổng giao dịch loại expense đã ghi, có thể 0 |
| `transaction_count` | Số giao dịch thu + chi đã ghi |
| `status`, `status_display` | Trạng thái và nhãn tiếng Việt |
| `confirmed_at` | datetime có timezone hoặc None |
| `forecast_expense` | Decimal nếu complete; **None** nếu unknown/incomplete |

Tiền được cộng từng dòng bằng Decimal, không dùng float hoặc SUM SQLite để tránh mất chính xác với tổng lớn. Thu nhập không cộng vào tổng chi nhưng vẫn tính số giao dịch và vẫn làm mất xác nhận khi thay đổi.

Ví dụ ngữ nghĩa (không phải dữ liệu được tạo trong website): tháng A đã xác nhận có chi, tháng B không giao dịch nhưng chưa xác nhận, tháng C chưa đầy đủ có chi → giữ cả A/B/C; `forecast_expense` ở B/C là None. Nếu người dùng xác nhận rõ tháng B không có khoản chi thì B mới thành Decimal(0). Không bỏ B để nối A/C, không nội suy, không tự điền tháng thiếu bằng 0. API này chưa tạo đặc trưng, huấn luyện, chọn mô hình hay trả dự báo.

## Tệp của TASK 08C

- `finance/models.py`, `finance/migrations/0004_monthlycoverage.py`: model trạng thái và hook lưu giao dịch.
- `finance/coverage_calendar.py`: lịch tháng theo múi giờ Việt Nam.
- `finance/coverage_state.py`, `finance/transaction_queries.py`, `finance/signals.py`, `finance/apps.py`: cơ chế reset chung cho ghi/xóa và giao dịch theo lô.
- `finance/coverage.py`: tổng hợp, token xem lại và chuyển trạng thái.
- `finance/coverage_views.py`, `finance/forms.py`, `finance/urls.py`: trang theo năm, xem lại, POST xác nhận/hủy/chưa đầy đủ.
- `templates/finance/monthly_history.html`, `templates/finance/coverage_confirm.html`, `templates/base.html`, `static/css/app.css`: giao diện và điều hướng.
- `finance/test_monthly_coverage.py`, `finance/test_coverage_migration.py`: kiểm thử.
- `README.md`, `docs/monthly-coverage.md`: hướng dẫn.

Không sửa script, cấu hình, dữ liệu hoặc mô hình thí nghiệm; không huấn luyện, tạo dự báo hoặc deploy. CSV tiếp tục dùng logic/transaction hiện có, việc reset được bổ sung qua manager chung thay vì sửa riêng view CSV.

## Kiểm tra thực tế

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 manage.py test --verbosity 1
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py makemigrations --check --dry-run
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate
```

**98 kiểm thử Django đạt**: 73 kiểm thử hồi quy và 25 kiểm thử mới. Bao phủ tách tài khoản/token, mặc định chưa biết, xác nhận rõ không chi, hủy/chưa đầy đủ và thời điểm, hiện tại/tương lai, ranh giới nửa đêm Việt Nam khi timezone active khác, ràng buộc DB, trang cũ sau sửa, CRUD web/model/queryset/bulk, đổi ngày cả hai tháng, update_fields, CSV thành công/không hợp lệ/rollback/đã nhập/hết hạn, lỗi reset làm rollback ghi/xóa, khoảng tháng thiếu qua năm, tổng Decimal lớn và migration giữ nguyên dữ liệu cũ/CSV mà không tạo xác nhận. Các tài khoản và giao dịch thử chỉ trong test DB riêng. Sáu kiểm thử JavaScript gợi ý phân loại hồi quy cũng đạt.

Migration `0004` đã áp dụng. `manage.py check` không có lỗi; `makemigrations --check --dry-run` không có thay đổi chưa tạo migration. Trước migration có backup SQLite riêng tại `backups/task08c-20261020-214027/`; không đưa backup, payload CSV, database hoặc dữ liệu tài chính vào Git.

Sau migration, đối chiếu các cột cũ, ID, giá trị và số dòng của tài khoản, danh mục, giao dịch, lô CSV và receipt: không thay đổi. Bảng trạng thái mới vẫn có 0 dòng, không tự xác nhận tháng nào trong dữ liệu thật. Đối chiếu 141 tệp nguồn dữ liệu, mô hình, cấu hình/kết quả thí nghiệm, metadata, script nghiên cứu và requirements với snapshot trước thay đổi: hash giữ nguyên.

Trình duyệt đã mở được trang lịch sử năm hiện tại, các tháng đã kết thúc có trạng thái mặc định, không có tháng hiện tại/tương lai trong bảng. Đã mở trang xem lại một tháng không có chi và kiểm tra có câu hỏi/checkbox xác nhận riêng; không bấm xác nhận hoặc thay trạng thái trên dữ liệu thật. Máy chủ cục bộ chạy tại `http://127.0.0.1:8001/`.
