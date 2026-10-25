# TASK 17B — Nhập nhanh và gợi ý danh mục gọn

Ngày 25/10/2026, giờ Việt Nam. Thực hiện trên dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`, tiếp sau commit TASK17A `9656351`. Các lượt đầu giữ mã local để xem trước; **đợt chốt bàn giao được phép commit/push main** sau kiểm tra dưới đây. Ghi chú chưa commit/push trong các mục trước là trạng thái tại thời điểm QA. Không thêm dependency, schema/migration, thay model/hash hoặc dữ liệu/thí nghiệm.

## Kiến trúc và phạm vi

Nhập nhanh là **parser theo quy tắc**, không phải NLP/ML, chatbot hoặc API ngoài. Một câu cho một giao dịch trên trang **Thêm giao dịch**; trang Sửa giữ nhập thường và dùng giao diện gợi ý ML gọn. Endpoint nội bộ `POST /giao-dich/nhap-nhanh/` chỉ trả JSON điền trước; không chạy suy luận, không tạo giao dịch, receipt hoặc phản hồi.

`finance/quick_entry.py` lấy giới hạn độ dài và số chữ số tiền từ model hiện có; dùng Decimal để chuyển đơn vị, không float, không làm tròn khoản tiền lẻ thành số nguyên. Endpoint yêu cầu đăng nhập, POST, CSRF; tối đa 500 ký tự, từ chối text rỗng/nhiều giá trị hoặc xuống dòng. Response không cache. Không ghi câu nhập vào log hoặc lưu thêm bản sao trong database. Exception không chứa câu nhập.

Kết quả vẫn không đáng tin để ghi DB: JavaScript chỉ gán các trường thông thường. Lưu tiếp tục qua `TransactionForm` → `save_with_feedback` → `Transaction.save` hiện có; kiểm lại quyền sở hữu, loại, danh mục, tiền/ngày và receipt. Không đổi nghiệp vụ tổng tiền, coverage, ngân sách, dự báo, CSV hoặc chính sách ngày CRUD.

## Quy tắc v1 đã hỗ trợ

| Nội dung | Quy tắc / ví dụ |
|---|---|
| Tiền | `45k`, `45 K`, `45 nghìn` → 45000; `1,5 triệu` → 1500000; `45000đ`, `45000 ₫`, `45000 VND` → 45000. Không phân biệt hoa/thường của đơn vị |
| Thập phân | Dấu phẩy là phần thập phân cho k/nghìn/triệu. Chỉ chấp nhận nếu kết quả là số nguyên VND, ví dụ `0,001k` → 1. Không hiểu dấu phẩy là phân cách hàng nghìn; số ghi trực tiếp bằng đ/₫/VND phải toàn chữ số |
| Giới hạn | 1–999999999999999 VND; từ chối dấu âm/dương, zero, tiền có phần lẻ VND hoặc vượt giới hạn. Không dùng dấu chấm hoặc khoảng trắng phân nhóm như `1.000đ`, `45 000đ` |
| Ngày | `hôm nay`, `hôm qua` tính bằng `timezone.localdate()` tại Asia/Ho_Chi_Minh; ngày cụ thể đúng hai chữ số ngày/tháng và bốn chữ số năm: `25/10/2026` |
| Thiếu ngày | Dùng hôm nay; kết quả có nhãn **Ngày (mặc định hôm nay)** và nhắc rõ ngày dd/mm/yyyy |
| Ngày tương lai | Ngày cụ thể hợp lệ vẫn được điền, kèm nhắc kiểm tra. Không áp quy tắc cấm ngày tương lai của riêng luồng định kỳ sang CRUD |
| Loại | Chỉ tiền tố đầu câu `Thu:`, `Thu nhập:`, `Chi:`, `Chi tiêu:` (không phân biệt hoa/thường). Không có tiền tố này thì để trống và yêu cầu chọn, kể cả có từ ăn, mua, lương hoặc nhận chuyển khoản |
| Danh mục | Luôn để trống sau khi điền nhập nhanh; người dùng chọn thủ công hoặc chủ động hỏi ML. Không có bảng từ khóa đoán danh mục |
| Mô tả | Chuẩn hóa NFC, bỏ đúng các đoạn đã nhận diện (tiền, ngày, tiền tố loại), thu gọn khoảng trắng. Mọi phần khác còn nguyên để hiển thị **Mô tả sau xử lý**; có thể sửa lại trước khi lưu |

Ví dụ `Ăn trưa 45k hôm nay` → tiền 45000, ngày hôm nay, mô tả `Ăn trưa`, **loại chưa chọn**, danh mục trống. `Chi: Đi chợ 1,5 triệu hôm qua` → loại Chi, tiền 1500000, ngày hôm qua, mô tả `Đi chợ`, danh mục trống. Parser không tự gọi ML cho hai ví dụ này.

## Mơ hồ và giới hạn

- Nhiều khoản tiền có đơn vị hoặc nhiều biểu thức ngày (kể cả hai ngày giống nhau) → từ chối toàn bộ, không lấy số đầu tiên hoặc điền một phần.
- Nhiều dấu hiệu `Thu:/Chi:` → yêu cầu tách giao dịch. Một lần không hỗ trợ danh sách nhiều giao dịch hoặc xuống dòng.
- `45000` không có đơn vị, số điện thoại, mã hóa đơn hoặc một ngày đơn lẻ **không được coi là tiền**. Khi có đúng một khoản tiền rõ và các số khác trong mô tả, các số khác được giữ nguyên với cảnh báo chưa diễn giải; không cộng chúng hoặc khẳng định ý nghĩa của chúng.
- Không nhận ISO `2026-10-25`, `25/10` thiếu năm, `2/3/2026`, ngày vô hiệu như 31/02, `ngày mai`, `hôm kia`, tuần/tháng trước/sau. Không sửa ngày, không dịch/đoán nội dung.
- Đơn vị USD/EUR/đô la hoặc viết tắt chưa hỗ trợ như `tr`, `ngàn`, số kèm `tỷ/tỉ/đồng` bị từ chối; không đổi tỷ giá. Không bỏ qua một khoản dùng đơn vị chưa hỗ trợ để chỉ lấy khoản còn lại. Các từ viết khác ngoài tập nhận diện có thể được giữ như phần mô tả, không phải parser ngôn ngữ tự nhiên tổng quát.
- Số có dấu viết sát chữ (`ăn-45k`) hoặc thêm số có đơn vị nhưng dính vào chữ (`45k vàabc50k`) bị từ chối toàn câu; không bóc riêng phần dương hoặc tự lấy một khoản. Từ “đồng” trong “đồng nghiệp” không bị coi là đơn vị tiền khi không đứng sau số.
- Có thể còn từ nối như “ngày” hoặc dấu câu sau xử lý; cố ý không xóa thêm phần chưa nhận diện. Người dùng được xem/sửa mô tả. Không tuyên bố parser hiểu mọi cách ghi tiền/ngày tiếng Việt hoặc giải quyết mọi câu mơ hồ.

## Trạng thái giao diện và bảo vệ dữ liệu nhập

1. Bấm **Điền vào biểu mẫu** mới gửi câu tới endpoint; gõ không tạo request phân tích hoặc ML.
2. Form trống (ngoài ngày mặc định) được điền trực tiếp sau cú bấm rõ ràng; hiện thông tin nhận diện và phần cần kiểm tra, thông báo **chưa lưu**.
3. Nếu đã có loại/tiền/danh mục/mô tả hoặc ngày đã thay, chỉ hiện preview. **Xác nhận thay thế biểu mẫu** mới thay các trường và bỏ lựa chọn danh mục cũ; **Giữ dữ liệu hiện tại** không đổi trường nào.
4. Đổi câu khi đang chờ làm phản hồi cũ bị bỏ qua. Sửa form sau khi đã có preview chờ xác nhận hủy preview đó; cần phân tích lại. Nếu người dùng nhập form trong lúc request đang chạy, response không được ghi đè, phải qua xác nhận.
5. Lỗi phân tích, mất mạng, hết phiên giữ nguyên dữ liệu form; không tự lưu. Các kết quả/mô tả được đưa vào DOM bằng `textContent`, không dùng HTML từ câu nhập.
6. Parser không có kho lưu nháp hoặc tự lưu khi tải lại trang. Khi JS tắt/lỗi, form HTML thường vẫn có thể nhập và POST; ô nhập nhanh mặc định vô hiệu khi JS chưa khởi động, có hướng dẫn noscript.

## Gợi ý ML và phản hồi giữ nguyên

Ngay dưới Mô tả là lựa chọn **VI — Tiếng Việt / EN — Tiếng Anh**, nút **Gợi ý danh mục**, nhãn thử nghiệm và câu nhắc kiểm tra. Tên chế độ đầy đủ có trong aria-label. Chi tiết nguồn mô phỏng/giới hạn và phản hồi chuyển vào **Về mô hình và phản hồi**.

Không xây thêm luồng suy luận. Các ID, endpoint, POST CSRF, receipt 15 phút, chữ ký, quyền sở hữu, chống dùng lại và quy tắc Transfer giữ nguyên. `transaction-form.js`/`classification_feedback.py` không sửa. Sau điền nhập nhanh, phát sự kiện thay loại/mô tả qua listener có sẵn để xóa receipt trên UI và gửi revoke tới server. Backend tiếp tục đối chiếu digest của mô tả/loại/chế độ khi Lưu; lỗi mạng không làm bỏ bước kiểm này. Không có receipt hợp lệ thì lưu thủ công không suy diễn phản hồi. Apply và Lưu vẫn riêng; không hiển thị phần trăm của decision score, không tự học/huấn luyện.

## Kiểm thử và QA

SQLite QA mới: **`D:\SAO LUU KHOA LUAN\qa-17b-20261025\qa.sqlite3`**, cổng **8018**, settings/cookie/secret riêng và nhãn vàng **QA 17B · Dữ liệu mô phỏng**. Khởi tạo/migrate chỉ QA này; không copy dữ liệu thật. Hai tài khoản với mật khẩu ngẫu nhiên ngoài Git, sáu danh mục ánh xạ; ban đầu không có giao dịch/phản hồi.

Runtime QA có sẵn: `D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe` (Python 3.13 và các thư viện đang dùng). Chỉ dùng runtime; QA17B trỏ rõ SQLite mới, không dùng cấu hình/kết nối PostgreSQL QA16E. Không cài gói hoặc đưa launcher DLL vào server.

### Kiểm mã

| Kiểm tra | Kết quả |
|---|---|
| Django parser/endpoint + phản hồi ML | **33/33 đạt** |
| Django hồi quy `test finance --settings=qa17b_test_settings --noinput` | **318/318 đạt**; log kết quả cuối `regression-final.log` |
| Kiểm tra lại riêng parser/endpoint sau bổ sung chặn token tiền dính chữ/đơn vị chưa hỗ trợ | **10/10 đạt**, `parser-final.log`; không cộng số này thành số bài hồi quy độc lập mới |
| Node `--test scripts/test_quick_entry.js scripts/test_transaction_suggestion.js scripts/test_form_feedback.js` | **23/23 đạt**, trong đó 6 bài mới về điền trước, xác nhận, lỗi, race, text an toàn và receipt ML |
| Backend parser | Tiền/đơn vị/Decimal/biên giới hạn, ngày nhuận/vô hiệu/nhiều ngày, ranh giới nửa đêm/năm Việt Nam, dữ liệu rỗng/dài, số điện thoại/hóa đơn, giữ mô tả chưa hiểu |
| Backend endpoint | Đăng nhập, POST, CSRF, duplicate text, không cache; phân tích qua RequestFactory **0 truy vấn** và toàn bộ bảng finance giữ nguyên, không gọi suy luận |
| Backend lưu | Dữ liệu parse bị sửa vẫn kiểm lại; danh mục người khác/sai loại/tiền zero bị chặn. Receipt cũ sau đổi mô tả bị từ chối; receipt mới Apply → Lưu tạo đúng phản hồi |

Lượt hồi quy đầu có một lỗi vì rút nhãn “Gợi ý thử nghiệm” thành nhãn ngắn khác. Đã khôi phục nhãn rõ ràng, làm lựa chọn VI/EN ngắn để không bị cắt trên mobile; giữ tên đầy đủ cho khả năng tiếp cận. Không sửa kỳ vọng kiểm thử hoặc tắt kiểm tra. Log lượt đầu `regression.log` được giữ riêng; dùng `regression-final.log` cho kết quả cuối.

Lượt rà cuối bổ sung từ chối số có dấu viết sát chữ và khoản tiền thứ hai chưa đúng định dạng/đơn vị. Sau lượt hồi quy 318 bài, chạy lại riêng 10 bài parser/endpoint với mọi ca mới; browser cũng kiểm `45k và 1 tỷ`, `45k vàabc50k` bị từ chối và số tiền đang nhập vẫn giữ 45000. JavaScript và nghiệp vụ lưu không thay đổi sau lượt 23 bài JS đã đạt.

### Trình duyệt thực tế

Microsoft Edge/Chromium headless, viewport **1280×900** và **390×844**, locale vi-VN, timezone Asia/Ho_Chi_Minh; mọi thao tác trên tài khoản QA:

- Desktop: câu thiếu loại chỉ điền tiền/ngày/mô tả; xác nhận/hủy thay thế, sau lỗi nhiều tiền vẫn giữ dữ liệu cũ.
- Desktop: nhập nhanh → suy luận VI thật bằng artifact hiện có → Apply → bấm Lưu; tạo giao dịch 45.000 VND và phản hồi.
- Mobile: nhập nhanh → suy luận EN thật → Apply; đổi qua câu có mô tả/loại khác phải xác nhận, receipt cũ bị xóa, danh mục bỏ trống. Yêu cầu receipt EN mới → Apply → Lưu; phản hồi thứ hai xuất hiện. Không huấn luyện hoặc đổi model.
- Context JS **tắt thực sự**: nút nhập nhanh vô hiệu và hướng dẫn hiện; nhập tay/lưu 57.000 VND thành công, không thêm phản hồi ML.
- Tài khoản thứ hai không thấy phản hồi hoặc mở giao dịch của tài khoản đầu (404).

`after-analysis-counts.json` ghi sau các thao tác parse/preview: **0 giao dịch, 0 suggestion, 0 feedback**, chỉ sáu danh mục QA. Sau các lần Lưu có chủ đích: ba giao dịch QA (hai ML, một nhập tay), hai phản hồi; không phải dữ liệu kiểm thử mô hình hoặc nhãn đã kiểm định.

`workflow-aggregate-evidence.json` xác nhận ba giao dịch QA tổng **147.000 VND**, hai phản hồi cùng nhãn/có Apply (mỗi chế độ VI/EN một), một receipt cũ đã bị revoke ở server. Chỉ lưu thống kê tổng hợp trong bằng chứng; không sao mô tả vào tài liệu.

Ảnh ở thư mục QA, ngoài Git; `final-*` là lượt chức năng đầu, **`compact-*` là giao diện sau tinh chỉnh** bên dưới. `desktop-replacement-review.png` được chụp trước khi rút ngắn chữ trên lựa chọn VI/EN, chỉ dùng bằng chứng luồng xác nhận. Giữ nguyên ảnh cũ để đối chiếu; ảnh/bằng chứng mới có manifest riêng.

| Bằng chứng | Đường dẫn ảnh trong thư mục QA |
|---|---|
| Biểu mẫu cuối desktop/mobile | `final-desktop-form.png`, `final-mobile-form.png` |
| Đã điền trước, có mô tả/tiền/ngày/loại cần kiểm tra | `final-desktop-prefill.png`, `final-mobile-prefill.png` |
| Một viewport đã điền trước | `final-desktop-prefill-viewport.png`, `final-mobile-prefill-viewport.png` |
| Xác nhận thay dữ liệu hiện có | `desktop-replacement-review.png`, `mobile-confirm-replace.png` |
| ML VI/EN thật và Apply | `desktop-vi-apply.png`, `mobile-en-apply.png`, `mobile-en-compact-viewport.png` |
| Lỗi giữ nguyên biểu mẫu | `final-mobile-error-preserves-form.png` |
| Khoản tiền thứ hai không hỗ trợ, không lấy riêng khoản đầu | `final-mobile-ambiguous-unit-preserves-form.png` |
| Không JavaScript / phản hồi | `mobile-nojs-manual.png`, `mobile-feedback-two.png` |

[Nhập nhanh desktop](<D:/SAO LUU KHOA LUAN/qa-17b-20261025/final-desktop-prefill.png>) · [nhập nhanh mobile](<D:/SAO LUU KHOA LUAN/qa-17b-20261025/final-mobile-prefill.png>) · [ML gọn trên mobile 390×844](<D:/SAO LUU KHOA LUAN/qa-17b-20261025/mobile-en-compact-viewport.png>).

`browser-final-checks.json` ghi hai viewport không tràn ngang toàn trang, các trường đang hiển thị đều có label; không ghi nhận pageerror trong lượt cuối. `final-counts.json` và `after-analysis-counts.json` tách rõ trạng thái trước/sau các thao tác Lưu có chủ đích. Không dùng HTTP 200 thay bằng chứng UI.

Chưa thử Safari/Firefox, điện thoại vật lý, screen reader hoặc production. Các smoke test UI không thay thế toàn bộ kiểm thử; không dùng kết quả các câu mô phỏng để công bố chất lượng ML.

## Tệp thay đổi và cách chạy

- `finance/quick_entry.py`, `finance/quick_entry_views.py`, `finance/urls.py`: parser và endpoint.
- `templates/finance/transaction_form.html`, `templates/finance/includes/quick_entry.html`, `templates/finance/includes/compact_suggestion.html`: nhập nhanh và ML cạnh mô tả.
- `static/js/quick-entry.js`, `static/css/app.css`, `templates/base.html`: tương tác và CSS phiên bản 17b.2.
- `finance/test_quick_entry.py`, `scripts/test_quick_entry.js`, `README.md`, tài liệu này.

Không cần migration khi dùng mã mới. Chạy local như README; QA xem tại **http://127.0.0.1:8018/**, có thể tự đăng ký tài khoản thử mới. Nếu server QA đã dừng, chạy `& 'D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe' 'D:\SAO LUU KHOA LUAN\qa-17b-20261025\serve.py'`.

Không commit/push trong task này. Giữ nguyên model/dependency, không đưa settings, credentials, SQLite hoặc ảnh QA vào repository. Hash SQLite thật và hai model được đối chiếu trước/sau; system check và rà diff/bí mật thực hiện trước bàn giao.

Rà cuối: **13 tệp thay đổi**, không có tệp staged; HEAD vẫn `9656351dd140fc0b56f1b09bf82442db3d9eabb4`. Kiểm tra `makemigrations --check --dry-run` báo **No changes detected**, system check không lỗi, `git diff --check` không lỗi. `final-audit.json` xác nhận SQLite thật/hai model không đổi hash và quét mẫu credential không phát hiện; kết hợp đọc diff thủ công, không coi quét chuỗi là chứng minh mọi định dạng bí mật đều được nhận diện.

## Tinh chỉnh giao diện nhập nhanh — 25/10/2026

Chỉ chỉnh template, CSS, JavaScript trình bày và kiểm thử UI. Parser, endpoint, JavaScript ML và dịch vụ phản hồi **không đổi byte** so với trước đợt tinh chỉnh (`compact-protected-before.json`, đối chiếu hash khi bàn giao). Không thay xác nhận thay thế, thứ tự gán trường/phát sự kiện hủy receipt, schema, model hoặc dependency.

- Đổi ô nhập thành `input type=text` một dòng, vẫn tối đa 500 ký tự; desktop đặt nút cùng hàng, mobile nút dưới ô để dễ bấm. API vẫn có kiểm tra xuống dòng như trước.
- Sau điền thành công, hiện **Đã điền, chưa lưu.** trong vùng xanh và tóm tắt thông tin nhận diện, ví dụ **30.000đ · 25/10/2026 · Chưa chọn loại**. Tiền hiển thị bằng cách nhóm chuỗi số nguyên từ server, không chuyển sang float.
- Lỗi ở vùng `role=alert` bên ngoài phần thu gọn, nền/viền đỏ kèm chữ. Các trường phải bổ sung (loại, danh mục), ngày mặc định và các cảnh báo như ngày tương lai/số trong mô tả chưa hiểu cũng luôn hiện bên ngoài dưới dạng ngắn.
- Bảng nhận diện, mô tả sau xử lý và toàn bộ giải thích/cảnh báo gốc nằm trong **Xem chi tiết**, mặc định đóng. Cảnh báo chưa biết không tự bị giấu: giữ nguyên chữ ở vùng cần kiểm tra. Mục này cũng có hướng dẫn định dạng trước khi phân tích và mở được bằng HTML gốc.
- Nếu form đã có dữ liệu, preview vẫn chưa thay form: thông báo và hai nút xác nhận/giữ dữ liệu nằm **ngoài** Xem chi tiết. Tóm tắt là kết quả phân tích của câu nhập nhanh, không thay cho việc kiểm tra các trường biểu mẫu cuối cùng trước khi Lưu.

### Kết quả kiểm tra đợt tinh chỉnh

| Kiểm tra | Kết quả |
|---|---|
| Node: quick entry + ML suggestion + form feedback | **25/25 đạt**, gồm hai bài mới cho tóm tắt, trường thiếu, ngày mặc định, cảnh báo tương lai/không biết và chuỗi tiền lớn; `compact-js-tests.log` |
| Django: quick entry, classification EN/VI, classification feedback | **60/60 đạt**, 32,160 giây; `compact-django-tests.log` |
| System check QA | Không lỗi |
| Hash phần cần giữ | Parser, endpoint, JS ML, feedback service không đổi so với trước tinh chỉnh |
| Dữ liệu | SQLite thật và hai model vẫn khớp hash ban đầu; không migrate hoặc kết nối production |

Tái sử dụng hồi quy 318 bài đã ghi ở trên; không chạy lại toàn bộ vì lần này chỉ thay trình bày. Không viết kiểm thử theo tên class CSS. Hai viewport không tràn ngang, không ghi nhận pageerror trong lượt thử. Ô nhập cao **48px desktop / 46px mobile**; khối nhập nhanh đã điền trong kịch bản mẫu cao **396px / 448px** khi đóng chi tiết.

Đã thao tác thật trên Edge/Chromium headless ở **1280×900 và 390×844**:

1. Nhập `Ăn trưa 30k hôm nay`: tóm tắt đúng, thông báo chưa lưu nổi bật, yêu cầu chọn loại và danh mục thấy rõ khi chi tiết đóng.
2. Mở/đóng Xem chi tiết: bảng và cảnh báo đầy đủ vẫn đọc được.
3. Form có 30000, phân tích câu mới 50000: chưa ghi đè, nút xác nhận/giữ dữ liệu hiện ở ngoài phần đóng; Hủy giữ 30000, Xác nhận mới đổi thành 50000.
4. Câu nhiều tiền: lỗi hiện bên ngoài, không đổi 50000 đang nhập. Thiếu ngày: nhắc ngày mặc định; ngày tương lai: cảnh báo hiện dù chi tiết đóng.

Bằng chứng `compact-browser-checks.json`. Các thao tác này **không bấm Lưu**, không gọi gợi ý ML. `compact-account-counts.json` đối chiếu riêng tài khoản fixture do dự án chuẩn bị vẫn có ba giao dịch, hai phản hồi, ba receipt như trước. Không so tổng toàn SQLite QA đang mở cho người dùng thử với con số lịch sử; không sửa/xóa các bản ghi QA của tài khoản khác.

Ảnh mới ở `D:\SAO LUU KHOA LUAN\qa-17b-20261025`, hash trong `compact-evidence-manifest.json`:

| Nội dung | Desktop | Mobile |
|---|---|---|
| Đã điền, chi tiết đóng | `compact-desktop-filled.png` | `compact-mobile-filled.png` |
| Một viewport | `compact-desktop-filled-viewport.png` | `compact-mobile-filled-viewport.png` |
| Chi tiết mở | `compact-desktop-details-open.png` | `compact-mobile-details-open.png` |
| Chờ xác nhận thay thế | `compact-desktop-replacement.png` | `compact-mobile-replacement.png` |
| Lỗi nằm ngoài phần thu gọn | `compact-desktop-error-viewport.png` | `compact-mobile-error-viewport.png` |

[Ảnh desktop mới](<D:/SAO LUU KHOA LUAN/qa-17b-20261025/compact-desktop-filled-viewport.png>) · [ảnh mobile mới](<D:/SAO LUU KHOA LUAN/qa-17b-20261025/compact-mobile-filled-viewport.png>) · [ngày mặc định](<D:/SAO LUU KHOA LUAN/qa-17b-20261025/compact-mobile-default-date.png>).

Giữ giới hạn chưa kiểm Safari/Firefox, thiết bị thật và screen reader. Bản QA cổng 8018 giữ chạy để xem trước. **Chưa commit/push/deploy.**

## Chốt bàn giao TASK17B — 25/10/2026

### Rà luồng trước commit

- `quick_entry_views.analyze` yêu cầu đăng nhập/POST/CSRF, trả JSON từ parser, không gọi save, ML hoặc tạo receipt. Kiểm thử xác nhận 0 truy vấn và không đổi các bảng finance khi chỉ phân tích.
- `quick-entry.js` chỉ gửi request phân tích khi bấm nút. Form đã có dữ liệu phải qua xác nhận thay thế; đổi câu/form trong lúc chờ không áp dụng kết quả cũ. Các nút nhập nhanh/xác nhận đều `type=button`, không submit giao dịch.
- Khi thật sự điền, giữ nguyên thao tác gán trường và phát `change`/`input` để listener ML hiện có xóa token, thu hồi receipt phía server và bỏ Apply cũ. Không xây thêm luồng suy luận hoặc ghi phản hồi.
- Luồng Lưu vẫn đi qua `TransactionForm` và `save_with_feedback` hiện có: kiểm dữ liệu, quyền sở hữu/danh mục, digest mô tả/loại/chế độ, chữ ký, thời hạn và trạng thái receipt. Dữ liệu parse không được tin để ghi DB. Không có thay đổi đối với Transfer hoặc ML Apply đang chờ.
- Diff gồm **13 tệp** đã liệt kê, không đổi model/schema/migration, dependency, thuật toán, hash artifact hoặc cơ chế tính tiền/coverage/ngân sách/dự báo/CSV. Không sửa thêm mã khi chốt bàn giao; tái sử dụng các kiểm thử đã đạt theo từng lượt.

### Kết quả kiểm thử, không cộng trùng

| Phạm vi | Kết quả đã kiểm | Cách hiểu |
|---|---|---|
| Hồi quy Django toàn finance trước tinh chỉnh UI cuối | 318/318 đạt | Không cộng thêm 60 bài ở dòng sau vì chúng là một phần của suite này |
| Parser/endpoint sau chặn định dạng mơ hồ | 10/10 đạt | Các bài thuộc nhóm Django, không phải mười bài độc lập bổ sung vào tổng hồi quy |
| Django liên quan sau UI cuối: quick entry, classification EN/VI, feedback | 60/60 đạt | Kết quả cập nhật cho phần bị ảnh hưởng; có chồng lấn với 318 và 10 |
| JavaScript sau UI cuối | 25/25 đạt | Thay thế kết quả 23/23 trước đó, không cộng 23 + 25 |
| Collectstatic và system check production QA trong đợt bàn giao | Đạt | Kiểm đóng gói riêng, không coi là số bài Django/JS bổ sung |

Không công bố một “tổng số kiểm thử” bằng cách cộng các nhóm trên. Các log `regression-final.log`, `parser-final.log`, `compact-django-tests.log`, `compact-js-tests.log` và ảnh/bằng chứng tiếp tục nằm ngoài Git.

### Collectstatic bằng profile Render QA

Import **`config.render` thực tế**, `DEBUG=False`, WhiteNoise `CompressedManifestStaticFilesStorage`. Settings QA và đầu ra nằm ngoài repository: `D:\SAO LUU KHOA LUAN\qa-17b-20261025\static-production-17b-handoff`. Dùng host `.invalid`, secret ngẫu nhiên trong bộ nhớ và database PostgreSQL dummy localhost:1; chặn `BaseDatabaseWrapper.ensure_connection` trước setup nên **mọi kết nối database đều bị từ chối**, không dùng URL production, không fallback SQLite.

Kết quả: **6 static files copied, 12 post-processed**, system check không lỗi. Đã xác minh manifest, `{% static %}` trả URL tên hash, tệp có thật và giải gzip khớp byte cho cả sáu tài nguyên:

| Tệp nguồn | Tên đóng gói |
|---|---|
| `css/app.css` | `css/app.f362132d88dc.css` |
| `js/quick-entry.js` | `js/quick-entry.d1d72050fc60.js` |
| `js/transaction-form.js` | `js/transaction-form.93fd08bdff76.js` |
| `js/transaction-filters.js` | `js/transaction-filters.08166be8015f.js` |
| `js/form-feedback.js` | `js/form-feedback.23a41e39df0d.js` |
| `img/brand.svg` | `img/brand.749d6337c5ed.svg` |

Kiểm nội dung CSS/JS đã collect có giao diện tóm tắt mới, thông báo chưa lưu và CSRF; không có database, model, CSV, credential hoặc Python trong static output. Bằng chứng: `handoff-static-report.json`, `handoff-collectstatic.log`; script/settings chạy kiểm tra ở cùng thư mục QA, **không đưa vào Git**. Đây là kiểm đóng gói trên Windows, chưa phải build Linux/Render hoặc kiểm giao diện online.

### Bảo vệ dữ liệu và mốc bàn giao

Chỉ commit mã, kiểm thử và README/tài liệu phù hợp. Không đưa SQLite, dataset, giao dịch/receipt/phản hồi QA, ảnh hoặc cấu hình QA, static đã build và credentials vào repository. Đường dẫn ảnh trong tài liệu chỉ trỏ bản local ngoài Git; các số liệu minh họa được ghi rõ là mô phỏng.

Đã rà diff thủ công cùng quét mẫu credential và các đường dẫn đang theo dõi; không dùng quét chuỗi làm bảo đảm tuyệt đối mọi dạng bí mật. SQLite thật và hai model vẫn được đối chiếu hash, không migrate hoặc kết nối production trong bàn giao. Repository xác minh đúng `thiennamm/khoa_luan_tai_chinh_ca_nhan`, vẫn Private; giữ remote và main, không force-push.

Mốc mã có tiêu đề **`Add quick transaction prefilling and compact ML suggestions`**. SHA sau push, đối chiếu local/remote và trạng thái working tree được báo trong tin nhắn bàn giao; không tự nhúng SHA của chính commit vào nội dung.

Giữ rõ giới hạn: đã thử Edge/Chromium headless 1280×900 và 390×844, chưa thử Safari/Firefox, thiết bị vật lý, screen reader hoặc UI online sau push. Push không được coi là bằng chứng mọi chức năng trên Render đã hoạt động.
