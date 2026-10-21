# TASK 08A — Gợi ý phân loại trong biểu mẫu giao dịch

Ngày thực hiện: 20/10/2026. Website chạy cục bộ, không deploy. Giữ nguyên thí nghiệm 06B/07B, dữ liệu và mô hình đã đánh giá; không huấn luyện hoặc cài thêm thư viện.

## Dịch vụ suy luận

- Artifact: `data/experiments/classification/task06b-v1-final/models/char_linearsvc_C_10p0.joblib`.
- Pipeline TF-IDF `char_wb` (3–5) + LinearSVC `C=10`, được chọn theo validation ở TASK 06B; không refit.
- SHA-256: `362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345`, xác minh với cả `selection` và `models` trong metadata hiện có, đồng thời khóa hash mong đợi trong dịch vụ.
- Đọc tệp mô hình từ settings phía máy chủ, hash byte trước khi `joblib.load(BytesIO(...))`; không mở lại một tệp khác sau khi kiểm tra. Pipeline đã xác minh được cache trong tiến trình, nhưng vẫn đọc/hash tệp và kiểm tra metadata ở mỗi lần gợi ý.
- Chuẩn hóa giống `body()` trong script kiểm định: regex `^\s*\[(debit|credit)\]\s*` không phân biệt hoa/thường, chỉ bỏ **một** tiền tố đầu; sau đó Unicode NFC, `casefold`, gom khoảng trắng bằng `split/join`. Không dịch dữ liệu.
- Mô tả rỗng hoặc vector TF-IDF `nnz=0`: không có gợi ý, không gọi classifier. Không xuất decision score, phần trăm hoặc xác suất.
- Không nhận đường dẫn, tệp mô hình hoặc ID tài khoản để tải mô hình. Không có upload mô hình, huấn luyện trong request hoặc tự học sau xác nhận. Không dùng launcher/patch DLL trong web server.
- Lỗi metadata, hash, thiếu tệp/thư viện hoặc runtime: HTTP 503 với thông báo chung, nhập và lưu thủ công vẫn hoạt động. Log chỉ chứa loại lỗi, không chứa mô tả hoặc nội dung exception.

## Ánh xạ và thao tác người dùng

`Category.canonical_label` tùy chọn, mặc định rỗng. Mã giữ đúng nhãn tiếng Anh của mô hình; phần hiển thị tiếng Việt chỉ giúp đọc nhãn, không biến dữ liệu huấn luyện thành dữ liệu tiếng Việt.

Người dùng tự chọn ánh xạ trong Thêm/Sửa danh mục, không suy từ tên. `Income` chỉ cho loại thu; 15 nhãn tiêu dùng/phí còn lại chỉ cho loại chi. `Transfer` được nhận diện trong kết quả nhưng không nằm trong lựa chọn ánh xạ thu/chi, luôn cần xem lại. Đây là quy tắc tương thích của chức năng gợi ý, không xác minh được bản chất tài chính của từng giao dịch.

Endpoint `POST /giao-dich/goi-y-danh-muc/` yêu cầu đăng nhập, CSRF, `kind` hợp lệ, mô tả tối đa 500 ký tự. Phản hồi không cache. Danh mục trả về lọc đồng thời theo người đăng nhập, loại đã chọn và mã nhãn. Không sửa loại giao dịch. Không ánh xạ được thì chỉ hiển thị nhãn. Nhiều danh mục cùng ánh xạ được trả về để người dùng chọn; không chọn hộ.

Khung **Gợi ý thử nghiệm** có chú thích dữ liệu tổng hợp tiếng Anh và chưa kiểm chứng tiếng Việt. Chỉ khi chọn danh mục trong khung và bấm **Áp dụng danh mục đã chọn** mới thay trường danh mục của biểu mẫu. Không có request lưu khi bấm Áp dụng. Người dùng vẫn phải bấm **Lưu giao dịch**. Đổi mô tả/loại hủy gợi ý cũ; kết quả request đã cũ bị bỏ qua. Nội dung kết quả và tên danh mục được gán qua `textContent`, không qua HTML động.

## Kiểm tra thực tế

- Python dùng: `.venv/Scripts/python.exe`, với `-X utf8`; requirements giữ nguyên SHA-256 `467c587b5c488e5a89350100b5ea0387c8234bbf0af3521ab15461badcd00686`.
- `manage.py check`: không có lỗi.
- `manage.py makemigrations --check --dry-run`: không có thay đổi chưa tạo migration.
- `manage.py migrate`: áp dụng `finance.0002_category_canonical_label` thành công. Trước khi chạy có bản sao SQLite riêng ở `backups/task08a-20261020-204718/` (ngoài Git). Đối chiếu SHA-256 trên các cột cũ theo thứ tự ID của bảng tài khoản, danh mục, giao dịch trước/sau: dữ liệu, ID và số dòng giữ nguyên. Không ghi nội dung tài khoản/giao dịch vào tài liệu.
- **49 kiểm thử Django đạt**: gồm 31 kiểm thử website cũ và 18 kiểm thử mới, trong đó có kiểm thử migration với dữ liệu cũ ở test DB riêng. Bao phủ CSRF, giới hạn đầu vào, đăng nhập, tách tài khoản, ánh xạ sai loại, nhiều ánh xạ, chưa ánh xạ, Transfer, thiếu mô hình vẫn nhập thủ công, hash/metadata sai bị từ chối trước giải tuần tự, lỗi runtime, chuẩn hóa và vector không có đặc trưng.
- **6 kiểm thử JavaScript đạt**, chạy bằng Node có sẵn trong bộ công cụ (không cài vào môi trường dự án). DOM/fetch giả chỉ ở tiến trình test; kiểm tra trực tiếp script giao diện: gợi ý và chọn chưa đổi danh mục, chỉ Áp dụng mới đổi; không gửi request lưu; có CSRF; không áp dụng Transfer/chưa ánh xạ; giữ thao tác thủ công khi lỗi; hủy gợi ý cũ và bỏ qua đáp ứng đến muộn; chặn độ dài.
- Trình duyệt đăng nhập hiện có, gọi mô hình thật qua endpoint trên `http://127.0.0.1:8001/giao-dich/them/`: `[debit] grocery store purchase` trả `Groceries`, thông báo chưa ánh xạ; mô tả rỗng trả không có gợi ý; `transfer to savings` trả `Transfer`, cảnh báo xem lại, không có thao tác áp dụng. Đây là chuỗi thử chức năng, không phải bản ghi giao dịch được lưu hay đánh giá độ chính xác mới.
- Trên tài khoản đang dùng chưa có danh mục ánh xạ nên không tạo thêm danh mục/giao dịch để thử Áp dụng trong DB thật. Thao tác Áp dụng được kiểm tra bằng kiểm thử sự kiện JavaScript nói trên; phân quyền/kiểm tra khi lưu bằng bộ kiểm thử Django. Ảnh kiểm tra được lưu riêng trong thư mục backup, không đưa Git.
- Suy luận trực tiếp và qua Django đều chạy được mà không dùng launcher DLL. Hash runner và kết quả thí nghiệm phân loại được đối chiếu không thay đổi. Mô hình vẫn ở vị trí cũ ngoài Git.

Mô hình vẫn có giới hạn dữ liệu tổng hợp tiếng Anh, khả năng trùng merchant/mẫu chưa phát hiện như báo cáo thí nghiệm. Không suy ra mức độ chắc chắn cho mô tả cá nhân, không khẳng định dùng tốt cho tiếng Việt hoặc đặt ngưỡng tự gán.

## Tệp của TASK 08A

Thêm mới:

- `finance/classification.py`: tải, kiểm tra và suy luận Pipeline.
- `finance/classification_labels.py`: nhãn chuẩn và quy tắc tương thích thu/chi.
- `finance/migrations/0002_category_canonical_label.py`: chỉ thêm trường tùy chọn, không backfill/seed.
- `finance/test_classification.py`: kiểm thử dịch vụ, endpoint và ánh xạ.
- `finance/test_category_migration.py`: kiểm thử giữ dữ liệu qua migration.
- `scripts/test_transaction_suggestion.js`: kiểm thử sự kiện Áp dụng và trạng thái giao diện.
- `docs/classification-integration.md`: tài liệu này.

Cập nhật:

- `config/settings.py`: đường dẫn mô hình cục bộ phía máy chủ.
- `finance/models.py`, `finance/forms.py`: trường ánh xạ, kiểm tra loại và giới hạn đầu vào gợi ý.
- `finance/views.py`, `finance/urls.py`: endpoint POST yêu cầu đăng nhập.
- `templates/finance/transaction_form.html`: khung gợi ý và nút Áp dụng.
- `templates/finance/category_form.html`, `templates/finance/category_list.html`: chọn và xem ánh xạ.
- `static/js/transaction-form.js`: gọi gợi ý, chọn/áp dụng rõ ràng, hủy kết quả cũ.
- `static/css/app.css`: bố cục khung gợi ý hỗ trợ màn hình hẹp.
- `README.md`: cấu hình artifact và hướng dẫn sử dụng/kiểm thử bằng PowerShell.

`.gitignore` không cần sửa. Dữ liệu, backup SQLite, ảnh kiểm tra, log cục bộ và mô hình tiếp tục nằm ngoài Git. Không commit/push trong TASK 08A.
