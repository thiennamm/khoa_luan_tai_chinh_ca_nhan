# TASK 18A — Mục tiêu tiết kiệm

Ngày thực hiện ban đầu: 25/10/2026; kiểm chứng PostgreSQL thật tại localhost và bàn giao local: **26/10/2026** (các mục cuối). Làm trên dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`. Migration đã chạy trên SQLite QA riêng, PostgreSQL QA của TASK 16 và SQLite local thật sau khi sao lưu được kiểm tra. Dữ liệu nghiệp vụ cũ giữ nguyên; model ML, dependency và các thí nghiệm không thay đổi. Không truy cập production. Các server QA đã dừng; mã được bàn giao lên main theo yêu cầu, kết quả push/SHA báo trong tin nhắn cuối.

## Cách dùng và ý nghĩa số liệu

Mở **Kế hoạch → Mục tiêu tiết kiệm**, tạo mục tiêu bằng tên (100 ký tự), số tiền cần đạt, ngày bắt đầu, hạn dự kiến tùy chọn và ghi chú (300 ký tự). Hạn không trước ngày bắt đầu; có thể lập mục tiêu bắt đầu trong tương lai nhưng chưa ghi nhận khoản nào trước ngày đó.

Trạng thái được tính lại từ lịch sử, không lưu một cờ “đã đạt” có thể lỗi thời:

1. Có thời điểm lưu trữ: **Đã lưu trữ**, ưu tiên cao nhất.
2. Chưa lưu trữ và tích lũy ≥ số cần đạt: **Đã đạt**.
3. Còn lại: **Đang thực hiện**.

Quá hạn (hạn trước hôm nay theo Việt Nam, chưa đủ tiền và chưa lưu trữ) chỉ là cảnh báo; vẫn được đóng góp/rút. Sửa hạn mức làm trạng thái cập nhật ngay, giữ mọi bản ghi. Được vượt mục tiêu: tỷ lệ và tích lũy phản ánh đầy đủ, thanh vẽ chặn ở 100%, còn thiếu tối thiểu 0.

**Số tích lũy do người dùng tự ghi nhận, không phải số dư ngân hàng hoặc tiền được hệ thống giữ hộ.** Đóng góp/rút chỉ là phân bổ, không tạo Transaction, không đọc chênh lệch thu–chi để coi là tiết kiệm. Chưa liên kết giao dịch hoặc ngân hàng. Không có khuyến nghị tiết kiệm theo ngày/tháng.

## Lịch sử và xác nhận thay đổi

- Mỗi khoản có loại Đóng góp/Rút, tiền nguyên dương, ngày thực tế và ghi chú 300 ký tự. Tiền mục tiêu/mỗi khoản cùng giới hạn **1–999999999999999**, dùng Decimal, cùng field/widget TASK 17C nhận `50000` hoặc `50.000`, hiển thị `50.000 VND`.
- Ngày thực tế không trước ngày bắt đầu và không sau hôm nay theo `Asia/Ho_Chi_Minh`; kiểm phía server, không chỉ HTML. Sửa ngày bắt đầu mục tiêu cũng phải hợp lệ với toàn lịch sử.
- Tích lũy = tổng đóng góp − tổng rút. Đọc từng giá trị Decimal để cộng, không dùng SUM SQLite có thể làm tròn tổng lớn. Không lưu một số dư tổng hợp để có thể bị cập nhật lệch.
- Khi kiểm lịch sử, sắp xếp **ngày tăng dần, ID tăng dần**. Cùng ngày giữ thứ tự ghi nhận; khoản mới nằm sau các bản ghi cũ cùng ngày. Sửa bản ghi giữ ID. Không tự đảo khoản đóng góp lên trước để hợp thức hóa rút tiền.
- Từ chối nếu tích lũy âm tại **bất kỳ thời điểm nào**, kể cả tổng cuối còn dương. Ví dụ góp ngày 1, rút ngày 2, góp ngày 3: không được xóa/chuyển khoản góp ngày 1 sang ngày 4 nếu làm âm tại ngày 2.
- Sửa khoản có checkbox xác nhận; xóa có trang xác nhận bằng POST. Xóa thành công thực sự bỏ bản ghi đó, không giữ một bản sao ghi chú riêng; không phải sổ kế toán bất biến/audit log của mọi phiên bản.
- Lưu trữ không xóa lịch sử và chặn cả thêm/sửa/xóa khoản lẫn sửa thông tin mục tiêu. **Mở lại** có trang xác nhận riêng, sau đó thao tác bình thường. Không có chức năng xóa mục tiêu trong UI.
- Danh sách 12 mục tiêu/trang; chi tiết 20 bản ghi/trang, hiển thị ngày/ID giảm dần. Tổng hợp luôn tính toàn lịch sử. Tổng quan chọn tối đa 3 mục tiêu đang thực hiện, mới nhất trước, độc lập tháng báo cáo đang xem; không bao gồm đã đạt hoặc lưu trữ.

## Kiến trúc và chống gửi lặp

| Bảng mới | Dữ liệu |
|---|---|
| `SavingsGoal` | FK chủ tài khoản; tên, amount Decimal(15,0), start/due date, note; archived_at, version, created_at |
| `SavingsEntry` | FK goal; kind, amount Decimal(15,0), date, note, version; chủ sở hữu suy qua goal, không nhận user_id thứ hai |
| `SavingsOperation` | UUID duy nhất, FK user/goal, action, SHA-256 payload chuẩn hóa, created_at; không sao chép nội dung ghi chú |

`finance/savings.py` là đường ghi dùng chung cho tất cả view mới. Biểu mẫu không gọi ModelForm.save để tự bỏ qua dịch vụ. GET chỉ đọc và phát token có chữ ký, không tạo bản ghi chờ trong database. Token chứa nonce ngẫu nhiên, user, hành động, goal/entry và phiên bản liên quan; có hạn **2 giờ**, được Django ký phía server. Hidden input không phải nguồn đáng tin: backend kiểm chữ ký, thời hạn và đúng quyền/tài nguyên/hành động.

Khi POST hợp lệ:

1. Trong `transaction.atomic`, INSERT receipt trước mọi đọc dữ liệu nghiệp vụ trong transaction. PK UUID chặn nonce trùng; INSERT lấy khóa ghi SQLite trước khi kiểm lịch sử, tránh nâng khóa từ một snapshot đọc cũ.
2. Với mục tiêu đã có, UPDATE `version=version` có điều kiện owner/ID để lấy khóa hàng PostgreSQL hoặc khóa ghi SQLite, rồi đọc lại mục tiêu hiện tại. Mọi thao tác ledger/goal cùng dùng khóa này.
3. Sửa thông tin/lưu trữ/mở lại kiểm goal.version; sửa/xóa khoản kiểm entry.version. Form cũ không ghi đè thay đổi khác. Khoản mới độc lập không bị cấm chỉ vì cùng ngày/số tiền; sau khi lấy khóa, luôn dùng trạng thái và lịch sử mới nhất.
4. Kiểm Decimal, ngày, trạng thái lưu trữ; thực hiện thay đổi và kiểm lại **toàn lịch sử** trong cùng transaction. Lỗi rollback cả bản ghi, phiên bản và receipt. Không còn receipt mồ côi từ thao tác thất bại.
5. Receipt được gắn goal trước khi commit. Gửi lại token/payload thành công cũ trả về mục tiêu ban đầu, không thêm khoản. Token đã dùng với payload khác bị từ chối. Sửa/xóa cũng có chống lặp, kể cả POST xóa gửi lại sau khi khoản đã biến mất.

Receipt không phải bộ dò mọi khoản trùng: mở form mới có nonce mới thì cùng ngày/tiền vẫn là hai khoản riêng. Token hết hạn phải mở lại form. Không tự gửi lại thao tác hoặc chạy vòng retry vô hạn khi database bận; SQLite báo khóa được chuyển thành lỗi rõ trên form, cho thử lại cùng token. Lỗi database không thuộc trường hợp khóa vẫn được đưa ra cơ chế lỗi thông thường, không báo lưu thành công.

Quy tắc không âm/toàn lịch sử và quyền sở hữu liên bảng được bảo đảm bởi **dịch vụ ứng dụng**, không phải CHECK liên hàng trong database. ORM/SQL ghi trực tiếp không phải đường ghi được hỗ trợ: không dùng bulk_create/update/delete thủ công cho ledger, không bổ sung đường ghi mới mà bỏ khóa/validate_history. Không có Django admin/endpoint khác cho các bảng mới trong task này.

## Quyền riêng tư và cách ly nghiệp vụ

Mọi view yêu cầu đăng nhập, giới hạn goal theo request.user trước khi đọc dữ liệu, POST + CSRF cho thay đổi và never-cache. Entry phải thuộc đúng goal đã kiểm quyền. Không nhận chủ tài khoản đích từ biểu mẫu. Token tài khoản khác/hành động khác/tài nguyên khác, bị sửa hoặc hết hạn bị từ chối. Nội dung tên/ghi chú được template escape; không ghép vào JavaScript.

Không thêm signal cho tiết kiệm, không gọi Transaction.save, hook coverage/forecast hoặc dịch vụ phản hồi ML. Không tự huấn luyện, xuất phản hồi hay gán ML. Kiểm thử đối chiếu toàn bộ bảng finance cũ, gồm dữ liệu giao dịch, ngân sách, coverage, phiên bản/kết quả dự báo và phản hồi ML đã tồn tại.

Lưu trữ giữ ledger/receipt cùng chủ tài khoản. Xóa tài khoản qua Django cascade xóa các mục tiêu, khoản và receipt; FK chặn bản ghi mồ côi. Không cung cấp chức năng xóa tài khoản mới ở task này. Sau khi khoản bị xóa theo xác nhận, receipt giữ nonce/digest và FK mục tiêu, không giữ một bản sao ghi chú của khoản. Receipt được giữ cùng mục tiêu/tài khoản, chưa thêm tác vụ dọn riêng.

## Migration và triển khai sau khi duyệt

Migration **`finance/migrations/0013_savings_goals.py`**, phụ thuộc 0012 và AUTH_USER_MODEL. Chỉ tạo ba bảng, FK, index `(goal,date,id)`, CHECK tiền dương trong giới hạn/nguyên đồng, loại khoản hợp lệ và due_date ≥ start_date. Không sửa bảng tiền cũ, backfill giao dịch hoặc gọi mô hình.

Đã kiểm trên hai SQLite QA riêng:

- `qa.sqlite3`: migrate mới đến 0013, dùng cho browser QA.
- `upgrade.sqlite3`: migrate đến 0012, tạo tài khoản/danh mục/giao dịch mô phỏng (khoản 999999999999999), rồi migrate đến 0013. Đối chiếu trước/sau: tài khoản và tất cả bảng finance cũ giữ nguyên. `integrity_check=ok`, `foreign_key_check` không lỗi.

Các kiểm tra integrity dùng connection Django để đăng ký các hàm SQLite mà CHECK cũ cần (như `django_date_extract`); kết nối sqlite3 thuần không có các hàm này không đủ để kiểm schema hiện tại.

Trong giai đoạn QA ban đầu chưa migrate SQLite local thật; **bàn giao local ngày 26/10 đã áp dụng 0013 như mục cuối**. Production chưa được kết nối hoặc chạy migration trong task. Mã mới đọc bảng tiết kiệm trên Tổng quan, nên database chưa có 0013 không thể chạy đầy đủ bản mới. Với máy khác/lần triển khai tiếp theo, chỉ sau khi duyệt: sao lưu nhất quán bằng SQLite backup API, kiểm bản sao/hash/integrity/khóa ngoại theo quy trình đã có, rồi trên đúng dự án chính và runtime local:

```powershell
# Chỉ thực hiện sau khi được duyệt và đã kiểm bản sao SQLite local thật.
Set-Location 'D:\KHÓA LUẬN TỐT NGHIỆP'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

Với Render: thực hiện backup PostgreSQL và kiểm backup trước lần triển khai được duyệt; start script hiện tại (`deploy/render-start.sh` → `scripts/render_start.py`) chịu trách nhiệm migrate, không dùng đường dẫn SQLite hoặc URL production trong QA. Chưa push/deploy ở task này. Không rollback migration 0013 tùy tiện sau khi đã có khoản thật, vì reverse sẽ bỏ bảng tiết kiệm; cần sao lưu trước và có kế hoạch bảo toàn ledger.

### PostgreSQL và đồng thời — rà ngoại tuyến ban đầu 25/10

Đã rà FK/unique nonce/CHECK/index và **biên dịch 16 câu SQL PostgreSQL ngoại tuyến** với version giả định cho compiler 18.0 (`pg_version=180000`), mọi kết nối database bị chặn. Có các bảng numeric(15,0), UUID, identity, FK deferrable tới user/goal. Không có SQL ghi dữ liệu hoặc thay bảng cũ. **Không phải migration PostgreSQL thật, không xác minh server/version đang chạy trên Render.**

Dịch vụ dùng transaction + UPDATE khóa goal, nonce PK unique; thiết kế dựa trên PostgreSQL READ COMMITTED mặc định của Django. Tại lần rà ngoại tuyến chưa kiểm database thật; lần kiểm **26/10** ở mục cuối đã bổ sung migration, schema và ba tình huống HTTP đồng thời. Chưa kiểm tải hoặc mọi lịch deadlock. Numeric(15,0) có thể làm tròn phần lẻ khi SQL trực tiếp ép kiểu; vì vậy vẫn phải dùng validation ứng dụng, không dựa riêng CHECK để chặn mọi SQL đầu vào sai.

Ba bài đồng thời dùng **SQLite QA có file**, hai connection/thread, kiểm hai khoản góp riêng, hai khoản rút không thể vượt và cùng nonce chỉ một khoản. Khi SQLite trả database-locked, bài kiểm thử thử lại tuần tự cùng nonce, rồi đối chiếu kết quả. Đây là chứng cứ không nhân đôi/không âm trong kịch bản SQLite đó, **không chứng minh cả hai request luôn thành công đồng thời** hoặc mọi lịch tranh chấp PostgreSQL.

Mỗi thay đổi kiểm toàn bộ ledger; danh sách cộng Decimal từ các khoản của tài khoản. Chưa đo tải với lịch sử rất lớn, chưa có tác vụ nền hoặc cache số dư để tối ưu. Không thêm đường cập nhật nhanh bỏ qua kiểm lịch sử.

## Kiểm thử và QA thực tế

| Nhóm | Kết quả | Giới hạn/cách đếm |
|---|---|---|
| `finance.test_savings` | 25/25 đạt | Mới, gồm 3 bài đồng thời; thuộc suite sau |
| Hồi quy toàn `finance` | **350/350 đạt**, 206,333 giây | 325 cũ + 25 mới; không cộng lại các lượt kiểm cùng nhóm |
| Tiết kiệm sau tinh chỉnh UI cuối | 25/25 đạt | Chạy lại phần liên quan; không phải 25 bài bổ sung |
| JavaScript dùng chung | **30/30 đạt** | Không sửa/thêm JS ở task này; kiểm tiền, form feedback, nhập nhanh, ML Apply |
| Django system check QA | Không lỗi | Không dùng cấu hình/database production |
| `makemigrations --check --dry-run` | Không thay đổi sau 0013 | Không cần migration thứ hai |

Các bài mới kiểm tạo/sửa/lưu trữ/mở lại, đạt/vượt/quá hạn, thay hạn mức, góp/rút/zero/bounds, ngày Việt Nam, sửa/xóa âm giữa lịch sử, thứ tự cùng ngày, số lớn Decimal, nonce trùng/giả/hết hạn/sai owner, form cũ, rollback/retry, ownership/CSRF/GET không ghi, phân trang, XSS và cascade. Có bảng tài chính cũ đã có dữ liệu khi kiểm tính cách ly.

Runtime sẵn có: `D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe`, Python 3.13, Django 5.2 hiện có; không cài dependency. Wrapper/settings tách riêng tại **`D:\SAO LUU KHOA LUAN\qa-18a-20261025`**, không trong Git:

```powershell
& 'D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe' -X utf8 'D:\SAO LUU KHOA LUAN\qa-18a-20261025\manage_qa.py' test finance --noinput --settings=qa18a_test_settings
node --test scripts/test_money.js scripts/test_quick_entry.js scripts/test_transaction_suggestion.js scripts/test_form_feedback.js
& 'D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe' -X utf8 'D:\SAO LUU KHOA LUAN\qa-18a-20261025\manage_qa.py' check
```

### Trình duyệt và ảnh

Đợt UI SQLite QA đã dùng **http://127.0.0.1:8020/muc-tieu-tiet-kiem/**, SQLite mới, tài khoản thử riêng, banner **QA 18A · Dữ liệu mô phỏng, không phải tài khoản thật**. Edge/Chromium headless, timezone Việt Nam, **1280×900** và **390×844**. Khi chốt kiểm chứng PostgreSQL ngày 26/10, cổng 8020 đã đóng; đây là URL của bằng chứng cũ, không phải server đang chạy.

Đã thao tác qua UI trên cả hai viewport: tạo mục tiêu, góp 50.000, rút 25.000, sửa rút thành 20.000 có checkbox, xóa khoản rút có xác nhận, lưu trữ/mở lại, giảm mục tiêu để thành Đã đạt. Kiểm thêm rút vượt: lỗi luôn hiện, giữ số nhập; phân trang lịch sử 24 dòng thành 20 + 4; dashboard tối đa 3 mục tiêu; menu mobile; không tràn ngang toàn trang. Bảng lịch sử cuộn vùng riêng, ngày/tiền không bị bẻ chữ. Tài khoản QA thứ hai (context tắt JS) chỉ thấy mục tiêu riêng, truy cập goal tài khoản đầu trả 404. Không có pageerror trong phiên QA.

Seed ban đầu có 6 mục tiêu của tài khoản chính (đang làm, vượt, lưu trữ, quá hạn, chưa có khoản) và 1 mục tiêu tài khoản thứ hai. Hai lượt thao tác UI tạo thêm 2 mục tiêu chính: ảnh danh sách cuối có **8 mục tiêu chính**, tổng database có 9; chi tiết quỹ học tập giữ **960.000 VND, 24 khoản**. Không trộn số lượng các thời điểm. Sau UI đã so hash nội dung mọi bảng finance cũ: không đổi; SQLite thật và model EN/VI cũng giữ hash.

Tất cả ảnh và bằng chứng ở `D:\SAO LUU KHOA LUAN\qa-18a-20261025`, ngoài Git:

| Bằng chứng | Tệp |
|---|---|
| Danh sách cuối (có trạng thái/vượt/zero/quá hạn) | `desktop-savings-list.png`, `mobile-savings-list.png` |
| Chi tiết và lịch sử | `desktop-savings-detail.png`, `mobile-savings-detail.png` |
| Mobile cuộn tới thao tác | `mobile-savings-detail-actions.png` |
| Form tiền VND và lỗi rút vượt | `{desktop,mobile}-savings-form.png`, `{desktop,mobile}-savings-error.png` |
| Tóm tắt Tổng quan | `desktop-savings-dashboard.png`, `mobile-savings-dashboard.png` |
| Thao tác/kiểm UI | `browser-checks.json` |
| Kiểm thử và schema | `regression.log`, `savings-final-tests.log`, `javascript.log`, `upgrade-report.json`, `postgresql-offline-report.json`, `postgresql-0013-offline.sql` |
| Hash/integrity/cách ly dữ liệu và rà diff | `verification-report.json`, `diff-review.json`, `evidence-manifest.json` |

Chưa kiểm Safari/Firefox, thiết bị/bàn phím điện thoại vật lý, screen reader hoặc UI production. Context tắt JS được kiểm danh sách/phân quyền; chưa thao tác toàn bộ CRUD tiết kiệm bằng trình duyệt tắt JS. Form vẫn submit server theo Django và nội dung chính không phụ thuộc JS. Đây là QA tính năng và hồi quy đã nêu, không tuyên bố chứng minh mọi tải đồng thời hoặc bảo mật tổng thể.

## Tệp bàn giao

- Thêm: migration 0013, `finance/savings.py`, `savings_calendar.py`, `savings_forms.py`, `savings_views.py`, `test_savings.py`; bốn template `savings_list/detail/form/confirm.html`; năm include `savings_card/fields/notice/pagination/summary.html`; tài liệu này.
- Sửa: `finance/models.py` (chỉ thêm model tiết kiệm), `urls.py`, `views.py` (tóm tắt dashboard), `templates/base.html`, `templates/finance/dashboard.html`, `templates/includes/navigation.html`, `templates/includes/icon.html`, CSS và README.
- Không sửa model ML, hash, dependency, thuật toán/thí nghiệm, CSV, parser nhập nhanh, signals tài chính hoặc `.gitignore`. Database, credential/settings QA, ảnh/log/bằng chứng không đưa vào Git. Đã rà **25 tệp** mới/sửa và quét mẫu credential, đường dẫn riêng tư đang theo dõi: không phát hiện bí mật hoặc artifact riêng tư trong thay đổi; `git diff --check` đạt. Quét mẫu bổ sung cho rà thủ công, không bảo đảm phát hiện mọi dạng bí mật. Commit/push chỉ gồm các tệp bàn giao này; SHA được đối chiếu và báo sau push.

## Bổ sung kiểm chứng PostgreSQL thật — 26/10/2026

### Đúng đích và bảo toàn dữ liệu

Dùng lại cluster TASK16D/16E **`D:\POSTGRESQL QA\rehearsal-20261023\data-attempt2`**, PostgreSQL **18.6** (`180006`), database **`qa_restore_20261023`**, chỉ **127.0.0.1:55432**, system identifier **`7699798773140758112`** khớp bằng chứng TASK16. Không restore lại archive, không initdb, tạo service hoặc dùng URL Render.

Vùng bằng chứng/cấu hình riêng: **`D:\POSTGRESQL QA\savings-18a-20261025`**, ACL theo SID hiện tại/SYSTEM, ngoài Git. Tên thư mục giữ ngày bắt đầu 25/10; kết quả kiểm PostgreSQL hoàn tất ngày 26/10. Dùng Python/requirements có sẵn của TASK16E, không cài hoặc đổi dependency. Profile kế thừa `config.base`, địa chỉ/database/role cố định; loại PG*/DATABASE_URL kế thừa khỏi process. Guard kiểm identity và READ COMMITTED trước mọi request/thao tác; admin còn đối chiếu data_directory. TLS tắt chỉ cho loopback QA này.

Mật khẩu admin database QA trước đây đã được hủy sau TASK16E: đã đặt lại ngẫu nhiên bằng single-user khi cluster dừng, rồi tạo role **qa_web_18a** riêng cho HTTP (không superuser/CREATEDB/CREATEROLE). Migration dùng admin QA. Không đổi mật khẩu Django của tài khoản đã phục hồi. Mật khẩu/token/URL riêng tư không in ra log công khai hoặc đưa vào source. Một tài khoản Django **mới chỉ dành QA**, không đăng nhập các tài khoản đã phục hồi.

Trước migration đã giữ digest theo PK của **161 bản ghi có sẵn** trong các bảng public. Sau migration và sau toàn bộ HTTP test: **0 bản ghi cũ thay đổi hoặc mất**. Migrate chỉ bổ sung bảng/ràng buộc cùng metadata Django; dữ liệu thử chỉ thuộc tài khoản QA mới. SQLite local thật, model EN/VI và archive gốc được đối chiếu SHA-256: **4/4 tệp giữ nguyên**.

### Migration và schema thực tế

`migrate finance 0013` và Django system check trên QA đạt. Đây là migration PostgreSQL thật, tách biệt với compile ngoại tuyến ở mục trước:

- Có đủ ba bảng SavingsGoal/Entry/Operation, 3 PK, 4 FK tới user/goal; constraints đã validated.
- **8 index** valid/ready, gồm index `savings_entry_goal_date` và PK UUID nonce.
- Sáu phép thử trực tiếp được PostgreSQL từ chối đúng: goal tiền âm, goal bằng 0, hạn trước ngày bắt đầu, entry tiền âm, kind sai, entry tham chiếu goal không tồn tại. Mỗi phép thử rollback, không giữ bản ghi probe.
- Cuối phiên: 0 constraint chưa validated, 0 receipt không có goal hoặc khác owner; không bỏ/tắt ràng buộc để đạt.

### Hai HTTP request đồng thời, CSRF và hai connection thật

Website QA dùng **Waitress 4 threads tại 127.0.0.1:8004**, hai session đăng nhập riêng cùng tài khoản QA, GET lấy form/token thật rồi POST có CSRF. Không thay dịch vụ/thuật toán để kiểm, không mock database hoặc bỏ transaction.

Để xác lập tranh chấp thực sự: một connection điều phối QA giữ `FOR UPDATE` trên **mục tiêu mới của tài khoản thử**. Gửi hai POST song song; quan sát `pg_stat_activity` có **hai backend PID riêng cùng chờ Lock**, rồi nhả khóa điều phối. Hai request sau đó tiếp tục qua code hiện có. Cùng nonce có thể chờ unique receipt trước, khác nonce chờ khóa goal. Chỉ ghi PID/loại chờ và thống kê mô phỏng; không lưu query body hoặc bản ghi riêng tư vào tài liệu.

| Kịch bản mô phỏng | Kết quả thực tế |
|---|---|
| Có 100.000 VND; hai mã khác nhau cùng rút 80.000 VND | Một POST 302, một POST 200 với lỗi làm âm lịch sử. Chỉ **1 khoản rút 80.000 VND**, còn **20.000 VND** |
| Hai POST cùng mã góp 50.000 VND | Cả hai 302; chỉ **1 khoản 50.000 VND**. Gửi lại tuần tự vẫn không thêm; dùng mã đó với amount 60.000 bị từ chối (200 lỗi) |
| Cùng ngày, tiền 50.000 VND, ghi chú giống nhau nhưng hai mã hợp lệ khác nhau | Cả hai 302; **2 khoản riêng**, tích lũy **100.000 VND**, không gộp vì trùng ngày/tiền |

Kiểm độc lập bằng PostgreSQL **SUM(CASE …) OVER(PARTITION BY goal ORDER BY date,id)** trên dữ liệu của tài khoản QA: **0 thời điểm âm**, giá trị lịch sử nhỏ nhất 20.000 VND. Cách đối chiếu này không chỉ gọi lại hàm validate_history của ứng dụng. Cuối ba kịch bản có **3 mục tiêu / 5 khoản / 8 receipt thành công**; receipt của lần rút bị từ chối rollback đúng.

Không phát hiện lỗi nghiệp vụ phải sửa trong source. Đã sửa lỗi import của settings QA ngoài Git trước khi migrate. Phiên bị gián đoạn làm server QA dừng không sạch; sau xác minh không còn process/listener cũ, PostgreSQL tự phục hồi WAL lúc khởi động lại, rồi identity guard/schema/hash được kiểm lại. Không sửa/xóa đè cluster hoặc che lỗi ứng dụng.

### Collectstatic production QA và cách đếm kiểm thử

Đã import **config.render**, DEBUG=False, WhiteNoise **CompressedManifestStaticFilesStorage** bằng settings thử riêng; host `.invalid`, secret sinh trong bộ nhớ, URL PostgreSQL dummy localhost:1. Chặn `BaseDatabaseWrapper.ensure_connection` trước setup: không kết nối database trong collectstatic, không dùng Render thật.

Kết quả: **7 files copied, 14 post-processed**, system check không lỗi. Cả 7 asset có manifest/hash/URL static đúng, bản gzip giải ra khớp byte; CSS chứa giao diện tiết kiệm mới. CSS đóng gói **`css/app.eb5d3e249d42.css`**, SHA-256 **`c0f0132769e4b3d6ec2082d2627eba85a09b5513b4326db707d04aa1c3531897`**. Output nằm ở `static-production-18a-handoff` trong vùng QA, không có database/model/dataset/credential.

Không sửa mã ứng dụng trong đợt kiểm PostgreSQL nên tận dụng **350 Django / 30 JavaScript** đã đạt, không chạy lại hoặc cộng ba kịch bản HTTP/sáu probe schema vào tổng 350. Đây là kiểm HTTP/DB thực tế mới, không tự đổi thành bằng chứng browser/JavaScript PostgreSQL. Collectstatic chạy Windows, chưa phải build Linux hoặc kiểm online Render.

### Dừng dịch vụ, bằng chứng và giới hạn

Đã dừng đúng process Waitress QA sau kiểm chứng; xác minh cluster trước `pg_ctl -m fast -w stop`, exit **0**. Kiểm độc lập TCP: **55432, 8004 và 8020 đều đóng**. Không tạo Windows service. Đã xóa `credentials.json` và passfile admin tạm trong vùng QA; cluster/bằng chứng được giữ, không phục hồi đè hay xóa dữ liệu thử để làm lại kết quả.

Các bằng chứng dưới đây ở `D:\POSTGRESQL QA\savings-18a-20261025`, **không đưa vào Git**:

| Tệp | Ý nghĩa |
|---|---|
| `database-identity.json` | Cluster/database/host/port/version đã xác minh |
| `migration.log`, `migration-schema-report.json` | 0013 thật, schema/index/constraint và các probe rollback |
| `http-concurrency-report.json` | HTTP status, số khoản/tiền và hai backend chờ Lock từng trường hợp |
| `final-verification.json` | 161 hàng cũ được bảo toàn; SQL window không âm; hash 4 tệp được bảo vệ |
| `handoff-static-report.json`, `handoff-collectstatic.log` | Collectstatic production QA, manifest/gzip |
| `shutdown-report.json`, `evidence-manifest.json` | Dừng server/cổng đóng, dọn bí mật và hash bằng chứng |

Baseline row digest/native/application logs là bằng chứng riêng tư, giữ trong vùng ACL; không sao chép nội dung vào tài liệu/repository. Không giữ credential để tự kết nối lại sau bàn giao.

Giới hạn còn lại: ba lịch tranh chấp có điều phối, chưa kiểm tải nhiều người/dữ liệu lớn, timeout/deadlock trong mọi trình tự hoặc isolation khác READ COMMITTED. Không chứng minh mọi chức năng cũ trên PostgreSQL hoặc UI/JavaScript đã kiểm hết. Đợt kiểm PostgreSQL không truy cập production hoặc migrate SQLite thật; lần bàn giao local tiếp theo được ghi riêng dưới đây.

## Bàn giao local và mã nguồn — 26/10/2026

Theo yêu cầu bàn giao, đã rà lại migration 0013 và luồng ghi của dịch vụ: token có chữ ký/owner/action/tài nguyên/thời hạn, UUID receipt chặn gửi lặp, khóa goal trước kiểm toàn ledger, version chặn form sửa lỗi thời, rollback cùng transaction. Không phát hiện lỗi phải sửa mã ứng dụng trong lượt bàn giao. Giữ kết quả **350/350 Django**, **30/30 JavaScript**, ba tình huống HTTP đồng thời PostgreSQL và sáu probe schema; không cộng các nhóm/lượt chạy chồng lấn thành tổng mới.

### Backup trước migration

- Bản sao mới: **`D:\SAO LUU KHOA LUAN\task18a-local-handover-20261026-180007\db.sqlite3`**; không ghi đè bản sao cũ.
- Phương thức **sqlite3.Connection.backup**, bản sao **372.736 byte**, schema trước 0013.
- SHA-256: **`02318308130f7aaed0fb968a29c551b1df98406f0b64af86999f6978148e612d`**; đã kiểm lại sau migration.
- Trước khi migrate: integrity_check=**ok**, foreign_key_check **0 vi phạm**, fingerprint/số hàng tất cả bảng của bản sao khớp nguồn; kiểm lại nguồn không đổi trong lúc sao lưu.
- Thư mục có ACL riêng và `manifest.json`, `backup_and_migrate.py`, `migration-check.log`; chứa dữ liệu tài khoản nên giữ ngoài Git. Manifest chỉ chứa metadata/count/hash, không in nội dung bản ghi, mật khẩu hoặc SECRET_KEY.

### Migration và xác minh local

Runtime **`D:\KHÓA LUẬN TỐT NGHIỆP\.venv\Scripts\python.exe`**, Python **3.13.16**, Django **5.2.18**, settings buộc **config.local**. Guard chỉ cho mở SQLite dự án chính và bản sao mới; chặn kết nối mạng trong process thao tác local. Không đọc URL production hoặc mở PostgreSQL.

Migration plan chỉ có **finance.0013_savings_goals**. Migrate thành công, Django system check không lỗi, migrate --check đạt, makemigrations --check --dry-run không có thay đổi. Integrity_check của local sau migration **ok**, kiểm khóa ngoại **0 vi phạm**.

Đối chiếu fingerprint: mọi bảng nghiệp vụ cũ giữ nguyên. Các hàng framework cũ cũng giữ nguyên, chỉ thêm đúng **3 content type, 12 quyền và 1 hàng django_migrations**. Ba bảng SavingsGoal/Entry/Operation mới có **0/0/0** bản ghi. Không tạo tài khoản, giao dịch, ledger tiết kiệm hoặc thời gian QA trong SQLite thật.

Đã gọi dịch vụ tổng hợp và render GET danh sách mục tiêu bằng RequestFactory với các tài khoản local hiện có, chỉ đọc, không đăng nhập/tạo session. Danh sách trống đúng trạng thái; fingerprint tất cả bảng trước/sau khớp. Đây là kiểm local chỉ đọc, không gọi là đã thao tác đóng góp/rút trên tài khoản thật; các luồng ghi được chứng minh bằng QA SQLite/HTTP PostgreSQL ở trên.

Không đổi model EN/VI, dependency hoặc thí nghiệm. Rà diff/staged và các đường dẫn đã theo dõi để loại SQLite, dump/cluster, dữ liệu, ảnh, model, secret và settings QA. Repository xác minh đúng **thiennamm/khoa_luan_tai_chinh_ca_nhan**, tài khoản **thiennamm**, vẫn **Private**; giữ main/remote/quyền truy cập, không force-push. Kết quả commit, SHA local/remote và working tree báo trong tin nhắn cuối; không nhúng SHA của chính commit vào nội dung tệp.

### Phục hồi và giới hạn sau bàn giao

Nếu cần phục hồi local: dừng các tiến trình ghi, kiểm SHA-256/integrity/khóa ngoại của backup bằng connection có các hàm SQLite của Django, giữ riêng database hiện tại trước khi phục hồi. Backup này là schema **0012**, chưa có lịch sử tiết kiệm; dùng mã tương ứng trước TASK 18A hoặc áp dụng lại 0013 có kiểm tra. Không chép đè database đang phục vụ và không dùng bản sao SQLite này để ghi đè PostgreSQL production. Lần bàn giao đã kiểm bản sao, **không diễn tập restore mới**.

Giữ các giới hạn PostgreSQL ở trên: ba kịch bản đồng thời có điều phối, chưa kiểm tải lớn/mọi deadlock hoặc isolation khác. Server QA đã dừng, không bật lại trong bàn giao. Push main có thể kích hoạt auto-deploy nếu hosting đã cấu hình; push thành công không chứng minh production đã migrate/UI hoạt động. Không kết nối hoặc sửa database production trong task này.
