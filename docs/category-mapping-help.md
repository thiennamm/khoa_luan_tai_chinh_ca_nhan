# TASK 19A — Làm rõ liên kết danh mục với nhãn mô hình

Ngày kiểm chứng: 27/10/2026, giờ Việt Nam. Làm trên dự án chính; dữ liệu thử nằm trong SQLite QA mới, ngoài repository. Chưa commit/push/deploy.

## Ý nghĩa và cách dùng

Tên danh mục do người dùng đặt; nhãn mô hình chỉ giúp tìm danh mục khi chủ động yêu cầu gợi ý. Không có yêu cầu mọi danh mục phải tương ứng một nhãn.

- Trường **Liên kết với nhãn mô hình — tùy chọn** có lựa chọn đầu tiên **Chưa ánh xạ**, giá trị rỗng; danh mục mới không tự chọn nhãn đầu tiên. Sửa danh mục giữ nguyên giá trị hiện có.
- Hướng dẫn ngay dưới trường: “Chỉ chọn khi ý nghĩa phù hợp. Không tìm thấy nhãn phù hợp, hãy để Chưa ánh xạ. Bạn vẫn có thể dùng danh mục để ghi giao dịch.”
- Mục **Xem phạm vi 17 nhãn mô hình** có tên tiếng Việt, tên gốc và phạm vi/ranh giới của từng mã. Mã lưu vẫn giữ nguyên, kể cả `Personal Care`.
- Giải trí (`Entertainment`): vé/hoạt động giải trí, nội dung mua lẻ. Ăn uống chế biến sẵn (`Restaurants`): món đã nấu, đồ uống pha sẵn, phục vụ bữa ăn. Du lịch (`Travel`): chuyến nghỉ, lưu trú/dịch vụ cấu thành chuyến đi. Đây là hướng dẫn để tự quyết định, không dùng từ khóa tên danh mục để cấm hoặc tự sửa lựa chọn.
- `Income` chỉ liên kết loại thu; các nhãn chi chỉ liên kết chi theo kiểm tra hiện có. `Transfer` được giải thích trong danh sách 17 mã nhưng không nằm trong lựa chọn liên kết thu/chi; vẫn cần xem lại.
- Bộ 11 danh mục mẫu giữ nguyên 7 liên kết rõ nghĩa, 4 mục chưa ánh xạ: **Ăn uống, Nhà ở, Hóa đơn, Thu nhập khác**. Không đổi danh mục hoặc liên kết của người dùng.

## Căn cứ phạm vi và giới hạn

Đã đọc và đối chiếu:

1. `finance/classification_labels.py`: 17 mã EN/VI và quy tắc loại tương thích đang dùng.
2. [Quy tắc dữ liệu VI v1, mục 3](vietnamese-classification-data.md) và tệp cục bộ `data/vietnamese/classification/vi-authored-v1/label-rules.md`: định nghĩa vận hành khi biên soạn dữ liệu tiếng Việt.
3. [Kiểm định nguồn EN, mục 4–5](classification-data-audit.md): các trường hợp chồng lấn và giới hạn khi suy bản chất từ mô tả/chiều tiền.
4. `finance/category_defaults.py`, dịch vụ gợi ý EN/VI và `finance/classification_feedback.py`.

Phạm vi hiển thị nằm trong `finance/category_mapping_help.py`, đủ 17 mã. Đây là lời giải thích theo quy tắc VI v1 do dự án/AI biên soạn, chưa có duyệt độc lập; không khẳng định tác giả nguồn EN định nghĩa mọi nhãn giống hệt. Ví dụ ranh giới Shopping/Healthcare, Transportation/Travel còn phụ thuộc mục đích; mô tả thiếu thông tin, khoản hoàn tiền, khoản gộp nhiều mục đích có thể không có một nhãn phù hợp. Không làm rõ được thì để **Chưa ánh xạ**. Hướng dẫn không bảo đảm mô hình luôn dự đoán theo phạm vi này.

## Thông báo trung tính và đổi tên

Form tải các liên kết chỉ của người đang đăng nhập, nhóm theo loại và mã nhãn, loại trừ chính danh mục đang sửa. Chọn một mã đã được danh mục khác cùng loại sử dụng sẽ hiện:

> Nhãn này đang liên kết với các danh mục: …

Không coi đây là lỗi; người dùng vẫn lưu được. JavaScript chỉ cập nhật chữ, không đổi trường, không gửi request và không suy luận tên. Tên được truyền bằng `json_script` và hiển thị bằng `textContent`; bản HTML dùng autoescape. Tên chứa dấu nháy, dấu `<`, `&` không trở thành mã thực thi.

Khi JavaScript tắt, điền đầy đủ biểu mẫu và bấm **Kiểm tra liên kết (chưa lưu)**: POST có CSRF, xác thực form như cũ, render lại các trường và thông báo, không lưu. Sau đó tự bấm **Lưu danh mục**. Nếu không dùng bước kiểm tra, POST lưu vẫn kiểm tra liên kết và thông báo sau khi lưu. Đây là thông tin tại thời điểm đọc; không phải ràng buộc duy nhất hay cam kết danh sách không thay đổi bởi phiên khác.

Danh mục đang có giao dịch hiện cảnh báo trước khi lưu:

> Tên mới cũng xuất hiện trên các giao dịch đang thuộc danh mục này. Đổi tên không tự chuyển giao dịch sang danh mục khác.

Đổi tên giữ khóa chính và khóa ngoại giao dịch, không sửa số tiền hoặc chuyển danh mục. Snapshot tên/nhãn trong phản hồi đã lưu không bị viết lại. Gợi ý đang còn hiệu lực không bị thu hồi chỉ vì mở form/đổi tên; Apply/Lưu vẫn xác minh quyền sở hữu, loại, mã nhãn hiện tại, thời hạn và trạng thái receipt theo dịch vụ cũ. Nếu người dùng chủ động đổi liên kết, việc Apply phải đáp ứng liên kết hiện tại như trước.

## Kiến trúc và phạm vi thay đổi

| Tệp | Vai trò |
|---|---|
| `finance/category_mapping_help.py` | Nội dung phạm vi, hướng dẫn và truy vấn danh mục cùng nhãn của chính tài khoản |
| `finance/forms.py` | Đổi nhãn/help/hiển thị lựa chọn ở CategoryForm; giữ mã và validation model |
| `finance/views.py` | Context và POST kiểm tra liên kết không ghi, thông báo sau lưu |
| `templates/finance/category_form.html` | Hướng dẫn, phần mở rộng 17 mã, cảnh báo đổi tên |
| `templates/finance/category_list.html` | Cách gọi liên kết tùy chọn nhất quán |
| `static/js/category-mapping.js` | Cập nhật thông báo trung tính trên cùng form, không gọi dịch vụ ngoài |
| `finance/test_category_mapping_help.py`, `scripts/test_category_mapping.js` | Kiểm thử hành vi mới |
| `README.md`, `docs/getting-started.md`, `docs/classification-integration.md`, tài liệu này | Hướng dẫn và bằng chứng |

Không thay `models.py`, schema, MAPPING_CHOICES của model, chính sách khóa catalog, endpoint suy luận, receipt/feedback, artifact, dataset, dependency, CSV hoặc số tiền. Chỉ thay lời hiển thị trong form, vì vậy không tạo migration chỉ để đổi metadata model. `makemigrations --check --dry-run`: **No changes detected**. Chỉ áp dụng migration hiện có đến 0013 để khởi tạo SQLite QA mới; không migrate SQLite thật/production. Không gửi tên danh mục hoặc dữ liệu riêng ra dịch vụ ngoài.

## Kiểm thử thực tế

Runtime local: Python 3.13.16, Django 5.2.18. Cấu hình QA import `config.base`, chỉ định đích SQLite mới; không dùng `config.local`/Render cho thao tác dữ liệu.

- **8 kiểm thử mới đạt**: mặc định rỗng, lưu và dùng danh mục chưa ánh xạ, nhãn trùng được phép, không chặn theo tên, POST preview không ghi, tách tài khoản/loại, mã sai/Transfer, quyền sở hữu, CSRF/login, đổi tên giữ ID/giao dịch/snapshot, gợi ý chưa dùng vẫn xác minh và Apply được.
- Bộ `finance`: **374 trường hợp; 368 đạt, 6 bỏ qua** vì `.venv` local không cài dependency Render. 8 mới đã nằm trong 374, không cộng thêm.
- 6 trường hợp Render bị bỏ qua ở runtime local đã chạy riêng bằng venv QA có sẵn (`D:\POSTGRESQL QA\application-16e-20261024\.venv`): **6/6 đạt**, không cài dependency. Đây là 6 trường hợp trong 374, không cộng thành 380. Các test này chặn kết nối DB/mạng theo thiết kế sẵn có.
- JavaScript: **33/33 đạt** trong 5 script kiểm thử (3 mới, 30 hồi quy). Kiểm thông báo cập nhật theo nhãn/loại, không tự chọn, dùng text an toàn và xử lý thiếu phần tử/JSON lỗi.
- Django system check: **0 vấn đề**. Kiểm tra migration: **không có thay đổi**.

Collectstatic bổ sung dùng cấu hình `config.render` với override production QA, DEBUG=False, dummy database localhost:1 và chặn mọi `ensure_connection`: **8 tệp copied, 16 post-processed**. Đã kiểm manifest, URL static template và gzip; bao gồm `js/category-mapping.js`. Không có kết nối database; đây là đóng gói trên Windows, không phải deploy Linux/Render.

Không huấn luyện hoặc chạy lại thí nghiệm ML. Kiểm thử gợi ý/receipt dùng boundary giả lập hiện có, không coi đây là đánh giá chất lượng mô hình.

## Bằng chứng trình duyệt

Thư mục ngoài Git: `D:\SAO LUU KHOA LUAN\qa-19a-20261027`.

Edge Chromium headless, locale vi-VN, giờ Asia/Ho_Chi_Minh; viewport **1280×900** và **390×844**. Dùng hai tài khoản QA mới, tên/mô tả mô phỏng và một giao dịch QA. Đã thử:

- Mở form mới để **Chưa ánh xạ**, chọn nhãn trùng, kiểm tra rồi lưu hợp lệ.
- Mở đủ 17 giải thích, xem cảnh báo đổi tên ở danh mục có giao dịch.
- Đổi tên qua browser; kiểm tra database QA xác nhận giữ ID/liên kết giao dịch.
- Danh mục tài khoản thứ hai không xuất hiện trong HTML hoặc thông báo.
- Desktop/mobile bật JavaScript: không page error, không tràn ngang toàn trang tại các trang đã thử.
- Mobile tắt JavaScript: xem phạm vi bằng details/summary và gửi form bằng bàn phím thành công. Playwright có lần timeout kiểm tra độ ổn định vị trí nút khi click; đã dùng thao tác Enter gốc của trình duyệt để hoàn tất, không giả lập HTTP thay cho UI.

Ảnh PNG full-page được chụp ở các viewport trên:

| Ảnh | Bằng chứng |
|---|---|
| `desktop-mapping-preview.png`, `mobile-mapping-preview.png` | Thông báo trùng nhãn và chưa lưu |
| `desktop-label-scopes.png`, `mobile-label-scopes.png` | Đủ 17 mã và giải thích |
| `desktop-rename-warning.png`, `mobile-rename-warning.png` | Cảnh báo tên mới trên giao dịch cũ |
| `mobile-nojs-mapping-preview.png`, `mobile-nojs-label-scopes.png`, `mobile-nojs-rename-warning.png` | Form/chi tiết/cảnh báo khi JavaScript tắt |

`browser-checks.json` ghi kết quả từng viewport; log kiểm thử và cấu hình/credential QA chỉ nằm ngoài repository. Server QA cổng 8023 và trình duyệt headless đã dừng sau kiểm tra. Chưa kiểm điện thoại vật lý, Safari/Firefox, screen reader hoặc giao diện production. Không có thay đổi schema/truy vấn ràng buộc mới; chưa chạy PostgreSQL thật trong TASK 19A.

## Rà soát bàn giao

Không commit/push ở bước này. Đã rà diff/bí mật: chỉ 12 tệp mã, template, JavaScript, kiểm thử và tài liệu liên quan; `git diff --check` đạt. Hash SQLite thật và hai artifact EN/VI trước/sau giống nhau; bản ghi giao dịch QA giữ nguyên ID, category_id, ngày, số tiền sau đổi tên. Kết quả ở `final-verification.json` trong thư mục QA; log test `regression.log`, `render-tests.log`, static `handoff-static-report.json`. Không đưa database, credential, cấu hình QA hoặc ảnh ngoài thư mục QA vào Git. Dữ liệu người dùng cũ không được sửa; mọi bản ghi thử chỉ nằm ở QA.
