# TASK 19C — Phản hồi thao tác, lỗi và bàn phím

Ngày kiểm chứng: 27/10/2026, giờ Việt Nam. Làm trên dự án chính; chỉ thao tác dữ liệu ở SQLite QA mới. TASK 19A/19B giữ nguyên; chưa stage/commit/push/deploy.

## Vấn đề đã rà và phần sửa

| Phát hiện | Xử lý |
|---|---|
| Đã có một handler submit POST dùng chung, chặn lần gửi tiếp theo và khôi phục pageshow | Mở rộng handler đó, không thêm một handler submit toàn cục thứ hai |
| Thông báo gửi form chỉ chung chung; khó biết việc nào đang chạy | `data-pending-label` cho lưu giao dịch/mục tiêu, nhập CSV, xử lý kỳ; mặc định vẫn “Đang xử lý…” |
| Form có lỗi theo trường nhưng chưa có tóm tắt/liên kết focus chung | Include tóm tắt server, link tới trường, focus sau pageshow; giữ giá trị bound form |
| Skip link có sẵn nhưng đích main không nhận focus rõ ràng | Chỉ thêm `tabindex=-1` cho main; không thêm main vào thứ tự Tab thông thường |
| Fragment #main/#id_amount có thể giành focus lại sau khi trang lỗi tải | Focus tóm tắt sau pageshow thay vì ngay khi script defer chạy; QA đã tái hiện và kiểm lại |
| Fetch nhập nhanh/ML chưa có timeout | Dùng chung `requestJson`, AbortController sau 20 giây, xóa timer trong finally; không tự retry |
| Nút gợi ý bị disabled ở DOM nhưng handler chưa chặn kích hoạt thứ hai | Thêm guard trước khi clear/bắt đầu request; giữ generation check bỏ phản hồi cũ |
| Sau lỗi Apply, danh sách lựa chọn cũ có thể còn hiện dù receipt đã bỏ | Clear receipt/lựa chọn cũ, báo chưa xác nhận được; cho yêu cầu gợi ý mới hoặc chọn thủ công |
| Bfcache có thể giữ nút fetch/Apply ở trạng thái chờ | Nhập nhanh/ML có phục hồi pageshow persisted, bỏ kết quả chờ cũ; dùng version để callback Apply cũ không mở khóa lượt mới |
| Lỗi CSV nằm dưới phần tải tệp và chưa nhận focus | Thêm focus target cho lỗi kiểm tra CSV và thông báo trạng thái lô lỗi/hết hạn |
| Khu vực ML có live region bao ngoài | Chuyển thành một live region trên chính dòng kết quả; cập nhật text khi khác, không dùng nested live region |

Không viết lại parser, suy luận, gán nhãn, receipt, transaction, khóa đồng thời, policy ngày, ngân sách/coverage/dự báo hoặc phân quyền. Giữ cơ chế thay thế dữ liệu có xác nhận của nhập nhanh. Không thêm handler chặn bàn phím/Tab hoặc menu tự viết: vẫn dùng native details/summary và nút HTML.

## Quy tắc đang xử lý và chống gửi lặp

Handler chung chỉ chạy khi submit POST chưa bị handler khác hủy. Submit bình thường đi qua constraint validation gốc của browser; form thiếu trường bắt buộc không bị khóa. Không đổi sang fetch cho các thao tác lưu tài chính.

Khi đã submit, form có aria-busy, thông báo trạng thái và lời nhắc kiểm tra danh sách nếu kết nối gián đoạn. Các nút submit có aria-disabled trong lúc chờ, **không** đặt disabled thực sự, không đổi name/value/type, không thêm input giả thay submitter. Lần submit thứ hai bị preventDefault bởi Map dùng chung. Vì vậy các nút như `action=preview_mapping` của TASK 19A vẫn gửi đúng giá trị. Enter vẫn dùng hành vi gốc của browser, không thêm keydown handler riêng.

Khi có response trang lỗi được xử lý bởi view, document mới có trạng thái sạch và tóm tắt lỗi. Khi quay lại bằng Back/Forward, pageshow khôi phục aria-busy/aria-disabled trước đó và bỏ các thông báo chờ. Nếu browser hiện trang lỗi mạng native, ứng dụng không thể sửa nội dung trang lỗi đó; dùng Back rồi kiểm tra danh sách/trạng thái trước khi gửi lại. Không tự mở khóa theo một timer rồi tự gửi lại POST tài chính đang chưa rõ kết quả.

Đây là hỗ trợ UX, không thay idempotency phía server. CSV, kỳ định kỳ, phân bổ tiết kiệm và receipt ML tiếp tục dùng ràng buộc/transaction/chống dùng lại hiện có. **Không bổ sung idempotency tổng quát cho POST nhập tay thông thường** trong task này; nếu không nhận được phản hồi thì phải kiểm tra danh sách trước khi gửi lại. Không suy rằng khóa nút có thể ngăn mọi lần gửi từ nhiều tab/client.

## Lỗi fetch, dữ liệu và quyền riêng tư

`form-feedback.js` cung cấp một helper JSON cho nhập nhanh, gợi ý và Apply/revoke. Timeout 20 giây bao gồm nhận response/đọc JSON. Abort chỉ kết thúc việc chờ phía client; không chứng minh server chưa xử lý hoặc đã rollback. Không tự retry sau timeout, lỗi mạng, redirect phiên đăng nhập, JSON lỗi hoặc lỗi HTTP.

- Nhập nhanh: chỉ lỗi validation 400 đúng cấu trúc được trình bày theo thông báo parser; các lỗi khác dùng câu an toàn. Không sửa trường nhập khi phân tích lỗi. Vẫn ghi rõ nhập nhanh không tự lưu.
- Gợi ý: vẫn chọn VI/EN rõ ràng, không tự fallback. Lỗi/không sẵn sàng vẫn cho nhập tay/lưu thủ công. Không hiển thị exception/response HTML nội bộ hoặc phần trăm tin cậy.
- Apply: khi chưa nhận được xác nhận, không đổi category theo giả định thành công. Bỏ receipt cũ khỏi form và yêu cầu gợi ý mới/chọn thủ công. Apply không tự tạo giao dịch.
- Các live region dùng role=status, aria-live=polite và aria-atomic. Không có timer lặp để đọc lại thông báo. Lỗi fetch nhận focus; tóm tắt lỗi server nhận focus sau trang tải. Per-field errors vẫn hiển thị bằng chữ, liên kết qua ID với input; không dùng màu làm tín hiệu duy nhất.
- Không đưa mô tả, mật khẩu, CSRF/operation token vào localStorage/sessionStorage, URL mới hoặc log mới. Không hiển thị traceback, raw Error.message hoặc response body lỗi HTTP. Hidden-field errors trong tóm tắt dùng lời nhắc mở lại biểu mẫu, không in token.
- Upload file không thể được browser điền lại sau response lỗi; người dùng phải chọn lại tệp. Các trường nhập tay bình thường được giữ theo bound form và định dạng tiền hiện có.

## Kiểm thử tự động

Runtime QA có sẵn: Python 3.13.16, Django 5.2.18; dùng settings QA chỉ định SQLite riêng, không import cấu hình database production và không cài dependency.

- Bộ `finance`: **394/394 đạt, không skip**. Bao gồm 6 kiểm thử mới và các hồi quy của TASK 19A/19B, quyền sở hữu, CSRF, ML receipt, CSV atomic import, kỳ định kỳ, tiết kiệm, coverage và dự báo. Không cộng các nhóm đã chạy lặp thành tổng lớn hơn 394.
- 6 kiểm thử mới: lỗi giao dịch giữ dữ liệu/link tới trường và không lưu; lỗi nhãn danh mục; rút tiết kiệm không đủ tiền; ngày định kỳ tương lai bị backend từ chối; dòng CSV lỗi không stage/import; lỗi hidden field có giải thích an toàn.
- JavaScript **43/43 đạt**. Bao gồm 35 có từ TASK 19A/19B và 8 bổ sung cho pending/submitter, timeout không retry, focus/live region, kích hoạt lặp và Back/Forward. Các mô phỏng DOM/fetch ở unit test không được gọi là bằng chứng browser/DB.
- System check **0 vấn đề**; makemigrations check **No changes detected**; không có schema hoặc migration mới.
- Collectstatic production QA: DEBUG=False, database giả localhost:1 và chặn mọi ensure_connection, **10 tệp copied / 20 post-processed**, manifest/URL/gzip đạt. Không kết nối database; không phải kiểm Render/Linux.

Lần chạy hồi quy đầu có một assertion mới kỳ vọng sai loại lỗi token; đã sửa fixture thành trường ẩn vượt giới hạn và chạy lại toàn bộ 394 đạt. Không sửa nghiệp vụ để ép kiểm thử đạt. Không chạy lại thí nghiệm ML.

## QA trình duyệt: bằng chứng thật và giả lập

Thư mục riêng ngoài Git: `D:\SAO LUU KHOA LUAN\qa-19c-20261027`. Server chỉ localhost:8025; SQLite mới đến migration 0013; tài khoản và dữ liệu đều mô phỏng. Không sao chép dữ liệu tài khoản thật vào QA.

Edge Chromium headless, desktop **1280×900** và mobile **390×844**, reduced motion. Đã kiểm:

| Tình huống | Bằng chứng / phạm vi |
|---|---|
| Tab → skip link → Enter | Focus thực sự tới main; không thêm một điểm Tab thừa |
| Thiếu required rồi Enter | Constraint validation của browser; không thêm pending/khóa form |
| Tiền sai định dạng gửi lên server | Lỗi backend thật; giữ raw input/mô tả; focus tóm tắt; Enter trên link lỗi focus đúng input |
| Hai kích hoạt nút liên tiếp | Hai `button.click()` trong DOM qua validation/submit thật, server QA cố ý chậm 1 giây; chỉ **1 POST**. Đã ghi nhận trạng thái pending từ DOM; nút disabled native=false, aria-disabled=true, có thông báo Đang lưu |
| Submitter của danh mục | Enter trên nút Kiểm tra liên kết gửi đúng action=preview_mapping, chưa lưu danh mục (hồi quy 19A) |
| Nhập nhanh bình thường | Request thật tới parser, giữ/cancel dữ liệu cũ, chỉ thay sau xác nhận; không tự lưu hoặc gọi ML |
| Nhập nhanh lỗi mạng | **Giả lập** route abort, không tới Django; giữ trường nhập, focus lỗi, khôi phục nút |
| Nhập nhanh HTTP 500 | **Giả lập** response HTML chứa text diagnostic giả; UI không in diagnostic đó |
| Timeout | Cố ý giữ request không gửi tới Django; timer client thật chờ 20 giây, phục hồi nút; **0 retry**. Đây là mạng giả lập, không phải sự cố production |
| VI → đổi mode → EN → Apply → Save | Suy luận **thật** qua hai model cấu hình dự án; receipt VI bị bỏ khi đổi mode, lấy receipt EN mới, Apply chủ động, lưu tạo phản hồi EN cùng nhãn/applied. Không coi ví dụ QA là đánh giá chất lượng mô hình |
| CSV | Tệp sai thật nhận focus lỗi dòng; tệp hợp lệ thật được xác nhận, một receipt/1 giao dịch |
| Kỳ định kỳ | Lỗi trường thật giữ mô tả; sửa lại và xác nhận bằng bàn phím; một kỳ ghi nhận, không phản hồi ML phát sinh từ kỳ |
| Tiết kiệm không đủ tiền | Lỗi nghiệp vụ thật, không ghi khoản rút; sửa thành đóng góp hợp lệ |
| Mất response sau ghi tiết kiệm | **Giả lập mất phản hồi** sau khi `route.fetch` đã nhận **302 thật** từ server. Sau đó kiểm tra chi tiết thay vì tự retry: DB QA có **1 khoản đóng góp 100.000 VND / 1 operation**. Không gọi lỗi kết nối là lưu thất bại |
| ML không sẵn sàng | **Giả lập** response 503; trường thủ công giữ nguyên, không có receipt, lưu giao dịch thật thành công và không thêm phản hồi ML |
| Back sau lỗi mạng native | Quay lại form/trạng thái không còn busy, sau đó kiểm tra danh sách. Unit test kiểm riêng nhánh pageshow persisted; không suy mọi lần Back đều dùng bfcache. Lượt Back bổ sung dùng document tải lại: các nút hết busy nhưng giá trị form không được browser khôi phục; không có lưu nháp phía client |
| Menu mobile/details | Dùng Enter mở/đóng native summary; form lỗi nhận focus; không tràn ngang toàn trang |
| JavaScript tắt | Nhập/lưu giao dịch thủ công bằng bàn phím thành công; nhập nhanh/ML vẫn cần JS như trước |
| CSRF thiếu token | HTTP check riêng trong QA nhận **403**, không gọi đây là thao tác UI |

`browser-checks.json` có 17 mục đạt và không page error; `database-verification.json` xác minh receipt/feedback, kỳ, savings operation và tài khoản thứ hai không có giao dịch. Một số lần chạy harness ban đầu bị sai kỳ vọng định dạng `99000`/`99.000` hoặc chưa chờ async/điều hướng; đã sửa harness, không sửa parser hoặc phép tính. Các lần đó có tạo giao dịch thử hợp lệ trong QA. Tổng 10 giao dịch QA cuối không phải số lần gửi của ca double activation: ca đó đo riêng 1 POST. Không dùng lỗi harness làm bằng chứng lỗi chống trùng backend.

Ảnh đã kiểm trực quan:

- `desktop-field-error.png`: lỗi theo trường, link và focus tiền.
- `mobile-field-error.png`: tóm tắt đang nhận focus, dữ liệu giữ nguyên ở 390×844.
- `desktop-csv-error.png`: lỗi dòng CSV đang nhận focus.

Log/bằng chứng: `regression-final.log`, `javascript.log`, `browser-checks.json`, `database-verification.json`, `handoff-static-report.json`, `final-verification.json`, `evidence-manifest.json`. Cấu hình QA, credential, database, script harness và ảnh đều ngoài repository; không đưa vào static/public/Git.

## Phạm vi tệp và bảo toàn 19A/19B

- JS dùng chung: `static/js/form-feedback.js`, `quick-entry.js`, `transaction-form.js`; CSS chỉ thêm các trạng thái/focus ở cuối `static/css/app.css`.
- Thêm `templates/includes/form_error_summary.html`; tích hợp vào `form_fields.html`, transaction form, savings fields và recurring confirm. Các template CSV có focus target cho lỗi; form tiết kiệm/CSV/định kỳ có pending label. Compact suggestion bỏ live region lồng nhau.
- `templates/base.html` chỉ thêm tabindex cho main bên cạnh block CSS TASK 19B đã có; không xóa block hoặc liên kết trước.
- Kiểm thử: `finance/test_interaction_accessibility.py`, `scripts/test_interaction.js`, cập nhật 3 script test form feedback/quick entry/suggestion dùng helper thật mới.
- README nối thêm hướng dẫn, không ghi đè nội dung 19A/19B. Tài liệu này ghi bàn giao.

Đối chiếu hash trước/sau: các tệp riêng 19A/19B khác base/README giữ nguyên; base chỉ khác tabindex của main, README giữ nguyên toàn bộ prefix cũ. SQLite thật và hai model EN/VI có SHA-256 không đổi. Không sửa models, services tài chính, dependency, schema hoặc thí nghiệm.

## Giới hạn

Đây là kiểm tra tương tác có phạm vi, **không phải đánh giá WCAG toàn diện**. Chưa thử screen reader, điện thoại vật lý, trình duyệt khác, mạng thiết bị thật, tải lớn hoặc PostgreSQL thật trong TASK 19C. Các bằng chứng PostgreSQL cũ không được gọi là đã chạy lại ở đây. Back/Forward không bảo đảm giữ bản nháp nếu browser nạp lại document; không lưu mô tả/tài chính vào storage để bù cho giới hạn này. Chưa kiểm mọi biểu mẫu ít dùng hoặc mọi tổ hợp lỗi; trang lỗi mạng native/HTTP 500 ngoài template xử lý vẫn do browser/server hiện có quản lý. Không có chức năng tự lưu, offline queue hay tự retry tài chính mới.

Chưa stage/commit/push/deploy. Server/browser QA được dừng sau kiểm tra; giữ bằng chứng ngoài Git để xem lại.
