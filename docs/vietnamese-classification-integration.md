# TASK 10C — Gợi ý tiếng Việt thử nghiệm

Ngày thực hiện: 21/10/2026. Đã đọc báo cáo TASK 10B và dịch vụ TASK 08A. Không huấn luyện, refit, đổi nhãn, split, dữ liệu hoặc kết quả thí nghiệm. Không deploy.

## Artifact và chuẩn hóa

| Chế độ | Artifact | SHA-256 |
|---|---|---|
| `vi` — Tiếng Việt — thử nghiệm | `data/experiments/classification-vietnamese/task10b-vi-v1/models/char_linearsvc_C_10.joblib` | `19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55` |
| `en` — Tiếng Anh — thử nghiệm | `data/experiments/classification/task06b-v1-final/models/char_linearsvc_C_10p0.joblib` | `362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345` |

Cả hai là Pipeline TF-IDF ký tự + LinearSVC C=10 riêng biệt; không ghép hoặc chuyển ngôn ngữ tự động. Tiếng Việt giữ đúng model fit trên 464 train ở TASK 10B, không refit train+validation. Toàn bộ mô hình/dữ liệu nằm ngoài Git.

`finance/classification.py` và bộ nhãn được giữ nguyên byte vì source hash nằm trong khóa thí nghiệm. `finance/classification_modes.py` định tuyến theo lựa chọn rõ ràng, tái sử dụng suy luận tiếng Anh và hàm `normalize_description` đã khóa. Chuẩn hóa thuần: bỏ **một** tiền tố debit/credit ở đầu, NFC, casefold, gộp khoảng trắng; giữ dấu. Không dịch, bỏ dấu, mở rộng viết tắt, dùng ID/nhãn hay khóa chẩn đoán làm đầu vào. Không dùng danh sách 48 câu mơ hồ làm blacklist.

Loader tiếng Việt so nhãn chọn/hash trong metadata TASK 10B và mục `files[models/char_linearsvc_C_10.joblib]` của artifact-manifest. Hash kỳ vọng còn được khóa trong mã; metadata và manifest không tự cho phép một artifact khác. Đọc/hash lại byte và kiểm tra kích thước trước mỗi lần dùng, kể cả khi có cache. Chỉ giải tuần tự chính byte đã kiểm bằng BytesIO, rồi kiểm cấu trúc Pipeline, char_wb (3,5), min_df=1, lowercase=False, strip_accents=None, sublinear_tf=True, LinearSVC C=10 và đủ 17 nhãn. Cache tiếng Việt độc lập tiếng Anh.

Joblib chỉ dùng cho artifact đáng tin cậy do dự án tạo. Hash không làm cho một artifact bất kỳ từ bên ngoài trở nên an toàn. Request không được cung cấp đường dẫn, metadata hay tệp mô hình. Không import script thí nghiệm/adapter CLI, không fit hoặc cài thư viện trong request. Suy luận thật trên máy hiện tại chạy được mà không can thiệp DLL; lỗi runtime được báo, không chuyển mô hình.

## Cấu hình máy chủ

| Setting | Nguồn |
|---|---|
| `CLASSIFICATION_MODEL_PATH` | Biến môi trường `DJANGO_CLASSIFICATION_MODEL_PATH`; mặc định artifact tiếng Anh ở trên |
| `CLASSIFICATION_METADATA_PATH` | `docs/metadata/classification-experiment-results.json`, giữ nguyên |
| `VI_CLASSIFICATION_MODEL_PATH` | Biến môi trường `DJANGO_VI_CLASSIFICATION_MODEL_PATH`; mặc định artifact tiếng Việt ở trên |
| `VI_CLASSIFICATION_METADATA_PATH` | `docs/metadata/vietnamese-classification-experiment-results.json` |
| `VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH` | Biến môi trường `DJANGO_VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH`; mặc định `artifact-manifest.json` trong run TASK 10B |

Xem lệnh PowerShell trong README. Khởi động lại tiến trình Django sau khi đổi cấu hình. Không sửa hash để bỏ qua lỗi toàn vẹn. Máy mới cần chuyển riêng artifact và manifest từ bản cục bộ đáng tin cậy; thiếu chúng không ảnh hưởng nhập giao dịch thủ công.

## Luồng sử dụng và bảo vệ

Trong Thêm/Sửa giao dịch, chọn ngôn ngữ mô hình (mặc định tiếng Việt), nhập mô tả/loại rồi bấm **Gợi ý danh mục**. Nhắc ngắn: “Gợi ý có thể sai. Hãy kiểm tra trước khi áp dụng.” Thông tin mở rộng nêu tiếng Việt học từ dữ liệu mô phỏng nhỏ do AI biên soạn trong dự án, chưa kiểm chứng trên dữ liệu thật đại diện người Việt; tiếng Anh học từ dữ liệu tổng hợp tiếng Anh. Không hiện accuracy của thí nghiệm như xác suất giao dịch, không xuất decision score.

Endpoint POST `giao-dich/goi-y-danh-muc/` yêu cầu đăng nhập, CSRF, mode `vi` hoặc `en`, loại income/expense và mô tả tối đa 500 ký tự. Mode thiếu/sai trả 400, không tự chọn mô hình phía endpoint. Không cache HTTP kết quả. Rỗng/chỉ tiền tố/vector không có đặc trưng trả `no_suggestion`; thiếu/sai model/metadata/manifest hoặc lỗi runtime trả `unavailable` (503), vẫn có thể lưu thủ công. Log suy luận chỉ chứa loại lỗi, không chứa mô tả, đường dẫn, secret hoặc transaction.

Chỉ ánh xạ `canonical_label` tường minh, thuộc tài khoản đăng nhập và đúng loại. Không suy từ tên danh mục. Nhiều kết quả yêu cầu tự chọn; chưa ánh xạ chỉ hiện nhãn. Transfer luôn yêu cầu xem lại, không gán vào thu/chi; nhãn khác loại không áp dụng. Không tạo danh mục, lưu giao dịch hoặc học lại từ gợi ý.

JavaScript giữ snapshot mô tả/loại/mode và số thế hệ request. Mọi thay đổi đầu vào/chế độ hủy kết quả, danh sách áp dụng và phản hồi cũ; đổi lại mode cũ vẫn cần yêu cầu lại. Kiểm lại sau cả `fetch` và `response.json` để chặn phản hồi đến muộn. Nút Áp dụng kiểm lại snapshot và danh mục tồn tại, đúng loại trong form. Danh mục thủ công không bị ghi đè khi nhận gợi ý. Người dùng tự bấm Áp dụng rồi Lưu giao dịch; không có request lưu do thao tác áp dụng.

## Kiểm tra thực tế

- Hồi quy Django: **147 kiểm thử đạt** (gồm 10 kiểm thử mới); không dùng database thật để kiểm thử. Sau thay đổi cuối chỉ làm rõ câu thông báo thiếu mô hình, chạy lại **27 kiểm thử phân loại liên quan**, đều đạt.
- JavaScript Node: **10 kiểm thử đạt**. Có ca đổi mode qua lại, phản hồi chậm khi fetch/đọc JSON, không áp dụng snapshot cũ, chỉ POST gợi ý với CSRF, không fallback.
- `manage.py check`: không lỗi; `makemigrations --check --dry-run`: không thay đổi schema.
- `run_vietnamese_classification_experiment.py verify`: verified=true, test_unchanged=true, fit_count=7, refit=false. Lệnh chỉ xác minh thí nghiệm cũ, không fit mới.
- Kiểm thử loader dùng cả hai artifact thật: đúng SHA, đúng chuẩn hóa có dấu, suy luận được; hash sai/metadata sai/manifest sai bị chặn trước joblib.load, kể cả sau khi cache đã có model.
- Kiểm thử endpoint cả hai mode: tách tài khoản, nhiều ánh xạ, sai loại, không ánh xạ, Transfer, input rỗng/vector rỗng, độ dài, CSRF, yêu cầu đăng nhập, thiếu VI không fallback EN, lưu thủ công được.

### Trình duyệt thật — SQLite QA riêng

IAB điều khiển trực tiếp, **desktop 1280×900** và **mobile 390×844**. Thư mục QA: `D:\SAO LUU KHOA LUAN\qa-10c-20261021-104650`; SQLite `qa.sqlite3`, hai tài khoản chỉ kiểm thử, danh mục ánh xạ riêng. Cổng 8002 dùng hai model thật; cổng 8003 cố tình cấu hình thiếu model tiếng Việt, tiếng Anh vẫn còn. Không dùng tài khoản hoặc dữ liệu thật.

| Thao tác | Kết quả quan sát |
|---|---|
| Desktop, mô tả tự viết “Đóng học phí học kỳ đại học”, mode VI | Nhãn Education, chỉ danh mục học phí của tài khoản QA; danh mục thủ công vẫn giữ nguyên |
| Đổi mode VI → EN sau khi chọn gợi ý | Kết quả/nút áp dụng cũ bị hủy; cần bấm gợi ý lại |
| Desktop, “Grocery shopping at Whole Foods”, mode EN | Nhãn Groceries; chủ động áp dụng rồi lưu thành công vào QA SQLite |
| Mobile, mode VI, sửa mô tả rồi đổi loại thu/chi | Mỗi thay đổi đều hủy gợi ý; cần yêu cầu lại |
| Mobile, mở thông tin mô hình, áp dụng Education rồi lưu | Thông tin giới hạn đọc được; danh mục chỉ thay khi bấm Áp dụng; lưu thành công |
| Mobile, thiếu model VI trên cổng 8003 | Hiện không có gợi ý, không dùng EN thay thế; lưu thủ công thành công |
| Mobile, chủ động chọn EN trên cổng 8003 | Mô hình EN vẫn trả Groceries; lỗi VI không làm mất chức năng EN |
| Bố cục mobile | document.scrollWidth = innerWidth = 390; không tràn ngang biểu mẫu |

Ảnh bằng chứng cục bộ trong thư mục QA: `desktop-vi.png`, `desktop-saved.png`, `mobile-vi-applied.png`, `mobile-saved.png`, `mobile-missing-vi.png`, `mobile-en.png`. Đây là mô tả tự viết để thử chức năng, không phải dữ liệu thực tế hay kiểm thử accuracy bổ sung. Phân quyền/CSRF và các ca sai hash được kiểm bằng kiểm thử tự động, không khẳng định mọi ca lỗi đều đã thao tác trong trình duyệt.

## Bảo toàn và tệp thay đổi

Trước sửa có snapshot cục bộ tại `backups/task10c-20261021-104452`: SQLite backup API, integrity_check=ok, dấu vân tay các bảng tài khoản/finance và hash 208 tệp. Sau kiểm tra đối chiếu lại dữ liệu thật, artifact, dữ liệu/thí nghiệm cũ, requirements và mã chuẩn hóa; không thay chúng. Tệp đã có trong snapshot duy nhất được sửa là script kiểm thử UI `scripts/test_transaction_suggestion.js`, đúng phạm vi. Kết quả đối chiếu lưu tại `after-verification.json` trong thư mục snapshot. Không đổi .gitignore, không commit/push dữ liệu/model/QA.

Đã dừng hai máy chủ QA sau kiểm tra, giữ SQLite/ảnh QA riêng để đối chiếu. Website cục bộ chạy cấu hình bình thường tại `http://127.0.0.1:8001/`; chưa triển khai trực tuyến.

Thêm `finance/classification_modes.py`, `finance/test_vietnamese_classification.py` và tài liệu này; sửa `config/settings.py`, `finance/forms.py`, `finance/views.py`, template giao dịch, JavaScript biểu mẫu, kiểm thử endpoint tiếng Anh (gửi mode tường minh), kiểm thử Node và README. Không cần migration.

Giới hạn: mô hình tiếng Việt từ tập mô phỏng nhỏ có hỗ trợ AI, chưa duyệt nhãn độc lập và còn 24 cảnh báo gần giống xuyên tập chưa duyệt độc lập. Không khẳng định xử lý tổng quát câu mơ hồ, tiếng Việt đời thực hoặc merchant mới. Người dùng chịu trách nhiệm xem lại trước khi áp dụng; chế độ là lựa chọn mô hình, không phải phát hiện ngôn ngữ.
