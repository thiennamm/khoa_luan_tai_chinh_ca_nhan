# TASK 15B — Giao dịch định kỳ và khoản đến hạn

Ngày thực hiện và bàn giao: 22/10/2026, dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`. Đã đọc giao dịch/ModelForm/QuerySet/signals, coverage, forecast version, ngân sách, dịch vụ phản hồi ML và kiểm thử liên quan. Không có AGENTS.md trong repository. Không đổi model ML, hash, dependency hoặc dữ liệu/thí nghiệm. Giai đoạn triển khai chỉ migrate QA; giai đoạn bàn giao đã được cho phép sao lưu và migrate SQLite local thật (mục 10). Không truy cập database production.

## 1. Phạm vi và cách dùng

Trang `/giao-dich-dinh-ky/` yêu cầu đăng nhập, chỉ có quy tắc/kỳ của tài khoản hiện tại. V1 chỉ lặp **hàng tháng**. Quy tắc gồm tên (tối đa 80 ký tự), loại income/expense, số tiền VND nguyên dương `Decimal`, danh mục thuộc tài khoản và đúng loại, ngày 1–31, tháng bắt đầu và tháng kết thúc tùy chọn (bao gồm cả hai tháng).

Số tiền từ 1 đến 999.999.999.999.999 VND như giao dịch hiện có; không float để lưu/cộng tiền. Tháng được lưu bằng ngày đầu tháng. Nếu ngày đến hạn vượt số ngày trong tháng, lấy ngày cuối tháng: 31/02 thành 28/02 hoặc 29/02 năm nhuận; 31/04 thành 30/04. Mọi tính ngày định kỳ dùng giờ Việt Nam UTC+7, kể cả khi TIME_ZONE của tiến trình được đặt khác.

1. Tạo quy tắc (POST); **chưa có giao dịch hoặc kỳ xử lý nào được ghi**.
2. Xem các kỳ dự kiến theo tháng, lọc trạng thái. GET chỉ tính dữ liệu hiển thị, không tạo bản ghi kỳ/revision/event/giao dịch.
3. **Ghi nhận** mở biểu mẫu GET: ngày giao dịch thực tế mặc định **hôm nay theo giờ Việt Nam**, tiền mặc định dự kiến; ngày đến hạn hiển thị riêng để tham khảo. Cho chọn ngày quá khứ hợp lệ, chặn ngày tương lai phía server trong form ghi nhận định kỳ. Khi form lỗi giữ dữ liệu đã nhập. Kind cố định theo snapshot kỳ; field disabled phía server bỏ qua kind giả mạo từ browser. Chỉ xác nhận khoản thu/chi đã thực sự phát sinh; POST hợp lệ mới tạo giao dịch. Không đổi chính sách ngày của CRUD/CSV.
4. **Bỏ qua kỳ này** cần checkbox và POST, không tạo giao dịch. Có thể mở lại bằng một bước xác nhận riêng.

Không nhận user đích từ POST. Không tự suy luận ML, tạo phản hồi phân loại, tìm giao dịch nhập tay/CSV để ghép kỳ, hoặc tự tạo danh mục. Luồng sửa giao dịch thông thường về sau vẫn có gợi ý ML tùy chọn như trước; chỉ khi người dùng chủ động yêu cầu gợi ý hợp lệ thì luồng TASK 15A mới có thể ghi phản hồi.

## 2. Kỳ, ngày thực tế và trạng thái

Định danh kỳ là **(rule_id, tháng đến hạn)**, độc lập ngày trả/nhận thực tế. Ví dụ kỳ 10/2026 ghi nhận ngày 30/09/2026: kỳ vẫn là tháng 10; khoản thực tế chỉ cộng vào báo cáo/ngân sách tháng 9. Không lấy tháng đến hạn thay cho ngày giao dịch.

| Trạng thái hiển thị | Điều kiện |
|---|---|
| Sắp đến hạn | Chưa xử lý, ngày đến hạn sau hôm nay |
| Đến hạn / quá hạn | Chưa xử lý, ngày đến hạn bằng hoặc trước hôm nay |
| Đã ghi nhận | Có transaction liên kết, xác nhận thành công |
| Đã bỏ qua | Người dùng xác nhận bỏ qua; không có transaction |
| Giao dịch đã xóa — cần mở lại | Transaction liên kết đã bị xóa bằng ORM; không tự sinh giao dịch mới |

Hai trạng thái đầu được tính theo ngày khi xem, không cần job đổi trạng thái lúc nửa đêm. Tình trạng quá hạn không phải chứng minh chưa thanh toán ngoài đời; chỉ phản ánh thao tác ghi nhận trong website.

Khoản dự kiến nằm ngoài bảng Transaction, không cộng vào thống kê, ngân sách, coverage hoặc đầu vào dự báo. Các phép tính tiền thật vẫn đọc Transaction như trước. Tạo/sửa/tạm dừng/kích hoạt/bỏ qua/mở lại không hủy coverage hay tăng forecast data version.

## 3. Lịch hiệu lực và giới hạn tạo kỳ

- **Tạo mới:** revision có hiệu lực từ tháng tạo, không tạo bù tháng trước dù start_month nhập trong quá khứ. Nếu start_month ở tương lai, chờ đúng tháng bắt đầu; end_month đã qua có thể khiến quy tắc không có kỳ đủ điều kiện.
- **Sửa thông tin:** áp dụng từ tháng sau theo giờ Việt Nam, kể cả sửa tên, loại, tiền, category, ngày hoặc khoảng tháng. Kỳ tháng hiện tại chưa xử lý vẫn theo revision cũ; kỳ đã xử lý theo snapshot của nó. Lưu nhiều lần cho cùng tháng hiệu lực dùng bản lưu cuối cùng, không lưu audit mọi lần sửa quy tắc trong tháng.
- **Tạm dừng:** revision inactive từ tháng hiện tại, vô hiệu luôn các revision tương lai đang lên lịch. Không có kỳ mới cho những tháng bị dừng. Các tháng trước vẫn là khoản đến hạn cũ, không biến thành tháng đã bỏ qua. Các kỳ đã từng xử lý (kể cả đã mở lại thủ công) giữ snapshot và có thể xử lý độc lập; không coi chúng là kỳ mới tự sinh khi pause.
- **Kích hoạt lại:** có hiệu lực từ tháng sau. Các tháng dừng đã qua và tháng đang dừng vẫn inactive; không backfill. Nhấn pause lần nữa trước thời điểm resume cũng hủy lịch resume.
- Danh sách tháng chỉ cho **12 tháng đến tháng hiện tại, cộng xem trước tháng sau** (tổng 13 tháng lựa chọn). Chỉ xác nhận/bỏ qua/mở lại trong 12 tháng đến tháng hiện tại; không ghi nhận kỳ tháng sau. Có thể trả sớm trong tháng đang xét bằng ngày thực tế thích hợp.
- Kỳ chưa xử lý là dữ liệu tính tạm theo revision; chỉ khi POST xử lý hợp lệ mới lưu một RecurringOccurrence. Không loop từ start_month đến tận tương lai, không vật hóa các kỳ khi mở trang. Không tự đánh dấu bỏ qua hoặc điền giao dịch cho tháng ngoài cửa sổ.
- Lịch sử các kỳ đã từng xử lý được giữ và phân trang riêng theo quy tắc, kể cả ngoài cửa sổ. Kỳ cũ ngoài cửa sổ chỉ đọc, chưa có thao tác xử lý/mở lại kỳ quá 12 tháng trong V1. Người dùng vẫn có thể ghi giao dịch thủ công; website không tự liên kết lại giao dịch đó.

Tổng quan có tối đa 5 khoản cần chú ý: đến hạn/quá hạn trong cửa sổ 12 tháng, cộng kỳ sắp đến hạn trong 7 ngày (có thể qua tháng/năm). Sắp theo ngày đến hạn rồi rule ID, hiện tổng số và link trang định kỳ. Khu vực này tính từ **hôm nay**, độc lập bộ chọn tháng thống kê. Không tuyên bố đã liệt kê mọi khoản quá hạn từ khi tạo tài khoản.

## 4. Lược đồ và snapshot

| Model | Nội dung |
|---|---|
| `RecurringRule` | User, thông số người dùng lưu mới nhất, cờ bật/tạm dừng, thời điểm tạo/sửa; category FK PROTECT |
| `RecurringRevision` | Rule FK CASCADE, tháng hiệu lực, active, JSON snapshot thông số; UNIQUE(rule, effective_month) |
| `RecurringOccurrence` | User/rule FK CASCADE, tháng định danh, due_date, JSON snapshot dự kiến, status, OneToOne transaction nullable SET_NULL, thời điểm cập nhật; UNIQUE(rule, month) |
| `RecurringEvent` | Occurrence FK CASCADE, action record/skip/reopen/delete và timestamp; không có mô tả giao dịch |

Snapshot dự kiến gồm tên, kind, amount dạng **chuỗi Decimal**, ID/tên category, due_day, start/end month. Snapshot của occurrence và due_date được khóa khi xử lý lần đầu, không đổi khi sửa Rule/Revision/category về sau, cũng không đổi khi mở lại kỳ. ID category trong JSON là tham chiếu lịch sử, **không phải quyền chọn category**; biểu mẫu và service luôn kiểm category thật theo user/kind.

Khi category của revision cũ đã bị xóa hoặc đổi loại/chủ sau khi quy tắc chuyển sang category khác, form không mặc nhiên dùng ID cũ: bỏ giá trị mặc định, yêu cầu người dùng chọn category hợp lệ. Snapshot tên cũ vẫn được giữ như lịch sử dự kiến. Category hiện đang được Rule dùng không thể xóa (PROTECT), kể cả Rule tạm dừng; cần chuyển category trước. Model Category không cho đổi loại/chủ khi đang có Rule tham chiếu. Không sửa dữ liệu giao dịch cũ để giải quyết bảo vệ này.

RecurringEvent giữ trình tự các thao tác trên kỳ. Ví dụ record → delete → reopen → record. Không ghi đè một kỳ đã bỏ qua thành đã ghi nhận mà thiếu event và xác nhận mở lại. Không sao chép mô tả giao dịch vào revision/event; mô tả mặc định từ tên khoản chỉ được lưu ở Transaction khi người dùng xác nhận.

## 5. Transaction, chống trùng, sửa/xóa

`finance/recurring.py` là đường ghi chính; không có scheduler hoặc luồng inference song song. Trong `transaction.atomic()`, UPDATE cùng giá trị `updated_at` của rule (đã lọc user) lấy khóa ghi **trước khi đọc**; sau đó đọc/khóa occurrence, đọc category thật, tạo Transaction bằng TransactionForm/Model.save hiện có, lưu occurrence và event cùng transaction. SQLite có thể báo bận khi hai request cạnh tranh; view bắt OperationalError và yêu cầu tải lại/thử lại, không giả báo thành công. Không dùng process-global lock làm bảo đảm liên request.

Các bảo đảm database mới:

- UNIQUE rule/month chống hai occurrence cùng kỳ; UNIQUE transaction_id chống gắn một giao dịch cho nhiều kỳ.
- CHECK: status recorded bắt buộc có transaction; open/skipped/deleted bắt buộc không có transaction; không nhận trạng thái khác. Tháng đầu ngày 1.
- Rule có CHECK kind, ngày 1–31, tiền nguyên dương/giới hạn, start/end tháng hợp lệ và thứ tự; revision unique và tháng đầu ngày 1. FK kiểm tồn tại bản ghi.
- Quyền cùng tài khoản và category cùng kind được kiểm ở form/service/model server. Không tuyên bố FK hoặc CHECK liên bảng đã chứng minh ownership; không có trigger ownership mới cho Rule ở task này.

Gửi lại POST record của kỳ đã recorded trả về giao dịch cũ, không sửa tiền/ngày đã lưu và không tạo event thứ hai. Gửi lại skip giữ một event skip. Record vào kỳ skipped/deleted bị từ chối cho đến khi mở lại rõ ràng. Hai request record đồng thời bị serialize/unique bảo vệ; kiểm thử thực tế hai thread SQLite trong DB test đảm bảo chỉ một transaction/occurrence/event. Đây chỉ là chống trùng **cùng kỳ**, không phát hiện giao dịch nhập tay/CSV hay hai Rule khác nhau có nội dung giống nhau.

Nếu lưu Transaction/event/occurrence lỗi, toàn bộ transaction rollback, bao gồm reset coverage và bump forecast version do Transaction.save. Không có transaction mồ côi sau khi lưu occurrence thất bại.

**Sửa giao dịch liên kết:** giữ recorded và giữ liên kết; snapshot dự kiến và tháng định danh không đổi. Các thông tin thực tế sửa bằng CRUD hiện có (kể cả loại nếu chọn category hợp lệ) quyết định báo cáo thực tế; không viết lại Rule. Sửa ngày qua tháng tiếp tục hủy xác nhận ở tháng thực tế cũ và mới qua hook cũ. Trang chi tiết/sửa có nhắc kỳ gốc và chính sách này.

**Xóa giao dịch liên kết:** receiver `pre_delete` của Transaction cập nhật occurrence thành deleted, FK transaction null và thêm event delete trong atomic của Django Collector. Bao phủ Model.delete/QuerySet.delete, cùng với hook post_delete coverage hiện có. GET hoặc mở lại trang không tự tạo lại. Trang xác nhận xóa giải thích hậu quả; muốn xử lý lại cần checkbox + POST reopen, sau đó POST record riêng. Nếu đã nhập giao dịch thay thế thủ công, người dùng phải kiểm trùng trước khi mở lại. Không có liên kết mới tự suy từ tên/tiền/ngày.

CASCADE/SET_NULL/PROTECT ở đây là chính sách Django ORM/deletion collector, không khẳng định mọi `DELETE SQL` trực tiếp thực hiện cùng logic. Xóa SQL trực tiếp không phát signal, FK có thể chặn; không hỗ trợ dùng SQL ngoài luồng để sửa trạng thái.

## 6. Quyền riêng tư và xóa tài khoản

Mọi view có login_required; mọi POST có middleware CSRF, filter user/get_object_or_404 trước hành động. Rule ID/month/action không cho vượt quyền tài khoản khác. Danh sách/rule history/events theo quyền từ rule/occurrence sở hữu, không có API public hoặc export dữ liệu định kỳ. Tên khoản và category autoescape trong HTML; không ghép vào JavaScript.

Không log tên/mô tả/amount hoặc payload cá nhân mới, không đặt dữ liệu định kỳ vào cookie hoặc file tạm. Snapshot có nội dung tài chính do người dùng khai báo, nằm trong database bền vững và cần được bảo vệ khi backup; không đưa vào Git hoặc tập học ML.

Không thêm thao tác xóa Rule hoặc tài khoản vào UI. Nếu quản trị xóa Rule bằng ORM, revision/occurrence/event bị cascade xóa; Transaction thật không bị xóa theo chiều ngược. Xóa tài khoản theo chính sách hiện có có thể bị Category PROTECT chặn khi còn Rule, ngân sách hoặc Transaction. Quy trình quản trị phải xử lý các tham chiếu trước; khi tài khoản thực sự được xóa bằng ORM, Rule/Occurrence/User FK cascade loại bỏ dữ liệu định kỳ, không giữ dữ liệu vô chủ. Không nới chính sách xóa tài khoản cũ.

## 7. Migration và vận hành

Migration mới: `0011_recurringoccurrence_recurringevent_recurringrule_and_more.py`, phụ thuộc 0010 và AUTH_USER_MODEL. Chỉ tạo bốn bảng mới, FK/index/unique/check; không backfill hoặc thay giá trị hàng cũ. Python guard Category và signal Transaction được cập nhật trong mã; không sửa model/artifact ML.

**Local đã áp dụng 0011 trong bàn giao tại mục 10.** Với máy khác hoặc lần triển khai tiếp theo, không dùng mã mới với schema cũ; thực hiện:

1. Tạo **backup mới** của SQLite local bằng SQLite backup API, integrity/foreign_key_check và manifest/SHA-256 như mục bàn giao trong `docs/classification-feedback.md`; không chỉ copy tệp live, không ghi đè backup cũ.
2. Sau khi kiểm backup mới, chạy rõ settings local:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate --settings=config.local
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check --settings=config.local
& '.\.venv\Scripts\python.exe' -X utf8 manage.py showmigrations finance --settings=config.local
```

3. Kiểm schema/dữ liệu cũ; kiểm luồng bằng SQLite QA riêng hoặc transaction kiểm chứng được rollback hoàn toàn. Không seed tài khoản/mật khẩu mặc định, không để dữ liệu QA trong database thật.

Render: backup PostgreSQL và kiểm phục hồi riêng trước phát hành. Giữ quy trình startup migrate/advisory lock hiện có, không cần scheduler, shell trả phí, email hay dependency mới. Push main trong bàn giao có thể kích hoạt auto-deploy nếu Render đang bật; không coi push thành công là bằng chứng migration production thành công. Không đổi cấu hình Render hoặc kết nối production trong phiên bàn giao. Reverse migration xóa các bảng kế hoạch/lịch sử mới, nên chỉ làm với backup và kế hoạch phục hồi; không tự reverse trên dữ liệu thật.

### Rà PostgreSQL

- Compile offline schema bốn model: **17 DDL** và **4 dạng truy vấn** thành công, cấm connection/cursor. JSONField thành jsonb; DateField/date, amount numeric(15,0), FK user integer theo auth_user, FK rule/category/transaction/occurrence bigint, PK bigint identity.
- UNIQUE(rule_id, month), UNIQUE(rule_id, effective_month) và UNIQUE(transaction_id) với nullable FK tương thích PostgreSQL (nhiều NULL được phép). CHECK status/transaction ghi cả hai trường trong một UPDATE khi xóa, không để trạng thái recorded + null trung gian.
- Date day extraction và ROUND numeric trong CHECK được compiler PostgreSQL sinh hợp lệ; FK DEFERRABLE INITIALLY DEFERRED. Các bảng mới ban đầu rỗng, không áp NOT NULL mới lên bảng Transaction/User đã có dữ liệu. Việc tạo FK vẫn có thể chờ khóa bảng tham chiếu.
- UPDATE rule trước khi đọc occurrence sẽ khóa dòng tương ứng ở PostgreSQL; select_for_update category/occurrence và unique là lớp bảo vệ bổ sung. Chưa chứng minh hiệu năng/lock ordering dưới tải nhiều worker bằng thử nghiệm PostgreSQL thật.

**Chưa chạy migration, test CRUD/deletion collector hoặc đồng thời trên PostgreSQL thật; chưa dùng bản sao dữ liệu production PostgreSQL.** Kiểm SQLite/compile không chứng minh quyền role, timeout hoặc mọi tranh chấp khóa trên Render đã phù hợp.

## 8. Kiểm chứng

QA ngoài Git: `D:\SAO LUU KHOA LUAN\task15b-qa-20261022-160526`, SQLite `qa.sqlite3`, server `127.0.0.1:8016`. Runner riêng chỉ cho mở đúng SQLite QA; settings từ config.base dùng secret giả cho QA, không import local/production settings. Suite tự động dùng SQLite trong RAM có guard chặn tệp SQLite thật.

- `finance/test_recurring.py` + `test_recurring_migration.py`: **27 ca liên quan đạt** trước kiểm trình duyệt, gồm năm nhuận/không nhuận ngày 29/30/31, start/end, pause/resume, snapshot, đầu vào sai, CSRF, isolation, GET không ghi, pagination/filter, actual khác dự kiến, rollback, sửa/xóa/reopen, no ML feedback, coverage/forecast/budget và hai thread đồng thời.
- Test hai thread có thể trả một kết quả thành công và một lỗi locked trên shared-memory SQLite, hoặc cả hai trả cùng transaction; luôn chỉ một Transaction/Occurrence/Event. Không tuyên bố mọi request đồng thời đều thành công hoặc đây là kiểm PostgreSQL.
- Migration test từ 0010 có sẵn User/Category/Transaction/Coverage/Budget/Suggestion/Feedback QA: mọi hàng cũ so sánh values trước/sau khớp; bốn bảng mới rỗng. QA trên đĩa fresh migrate đến 0011 thành công; check và makemigrations --check đạt.
- Hồi quy toàn finance: **279/279 đạt** (137,099 giây) sau sửa câu thông báo bảo vệ danh mục. Lần đầu có một lỗi kiểm tra câu thông báo ngân sách cũ; đã tách nhánh thông báo định kỳ, giữ câu thông báo cũ khi không có Rule. Không thay thiết kế thí nghiệm để qua test.
- Sau chỉnh chữ hướng dẫn pause và nhãn checkbox cho Rule, nhóm recurring/migration/budget đạt **37/37** (16,510 giây). Không sửa JavaScript và không chạy lại thí nghiệm ML.
- Trình duyệt QA: đăng nhập; trạng thái trống; tạo Rule; mở form record chưa sinh period/Transaction (đối chiếu DB: 1 Rule, 0 Occurrence, 0 Transaction). Xác nhận kỳ 10 với **ngày thực tế 30/09/2026 và tiền 2.900.000 khác dự kiến 3.000.000**; trang chi tiết thể hiện đúng ngày/kỳ; xóa có cảnh báo → kỳ deleted; checkbox reopen → kỳ mở lại, chưa có giao dịch; skip → đã bỏ qua trên bố cục điện thoại. Các ca CSRF/rollback/concurrent/giữa hai tài khoản kiểm tự động, không gọi là mọi ca đã thao tác qua browser.
- Đã thử thêm pause/resume bằng checkbox trên điện thoại, kỳ tháng 10 đã bỏ qua giữ nguyên. Sửa tên/tiền/ngày thành kỳ mới dự kiến 3.100.000 VND ngày 25: tháng 10 vẫn snapshot cũ 3.000.000 ngày 20; xem trước tháng 11 dùng tên/tiền/ngày mới, không có nút Ghi nhận.
- Desktop dùng bố cục mặc định của browser; điện thoại sau hiệu chỉnh công cụ đo được **390×845 CSS**, `clientWidth=scrollWidth=367` (thanh cuộn), không tràn ngang. Chưa thử thiết bị vật lý. Đã lưu screenshot khung hẹp bằng API screenshot; kích thước bitmap phụ thuộc DPI/zoom công cụ, số đo CSS được đối chiếu riêng từ DOM.
- Ảnh trong thư mục QA trên: `recurring-deleted-desktop.png`, `recurring-mobile.png` (xác nhận pause), `recurring-preview-mobile.png` (xem trước tháng sau). Không chép ảnh/data QA vào Git. Sau khi hoàn tất các luồng, công cụ mất đồng bộ tab trong thao tác trở về tháng hiện tại/chụp ảnh cuối; không coi ảnh cuối đó là đã tạo. Đã gửi lại lệnh reset viewport thành công bằng capability browser, không cần thay đổi ứng dụng.
- Cuối kiểm tra database QA: 1 Rule, 2 Revision, 1 Occurrence đã bỏ qua, 4 Event; **0 Transaction, 0 ML feedback** sau khi xóa giao dịch và bỏ qua kỳ. `integrity_check=ok`, không có vi phạm khóa ngoại. Đây là số liệu mô phỏng QA, không phải dữ liệu tài khoản thật.

Giới hạn V1: chưa có chu kỳ tuần/năm, scheduler, báo email/push, trả góp, tự khớp giao dịch từ CSV/ngân hàng, xử lý kỳ ngoài cửa sổ 12 tháng, audit mọi lần sửa Rule hoặc phát hiện giao dịch trùng toàn hệ thống. Chưa deploy. Không gọi khoản dự kiến là giao dịch thực tế hoặc lịch sử chi tiêu đã đầy đủ.


## 9. Tệp thay đổi và rà diff

Các tệp của TASK 15B (mới hoặc sửa):

- `README.md`
- `docs/recurring-transactions.md`
- `finance/migrations/0011_recurringoccurrence_recurringevent_recurringrule_and_more.py`
- `finance/models.py`
- `finance/recurring.py`
- `finance/recurring_forms.py`
- `finance/recurring_views.py`
- `finance/signals.py`
- `finance/test_recurring.py`
- `finance/test_recurring_migration.py`
- `finance/urls.py`
- `finance/views.py`
- `templates/finance/confirm_delete.html`
- `templates/finance/dashboard.html`
- `templates/finance/includes/recurring_table.html`
- `templates/finance/recurring_action.html`
- `templates/finance/recurring_confirm.html`
- `templates/finance/recurring_history.html`
- `templates/finance/recurring_list.html`
- `templates/finance/recurring_rule_form.html`
- `templates/finance/transaction_detail.html`
- `templates/finance/transaction_form.html`
- `templates/includes/navigation.html`

Đã rà toàn bộ nội dung mới/sửa và đối chiếu bí mật local chỉ trong bộ nhớ: không thấy token, private key, URL chứa credential hoặc secret thật. Không có SQLite, model, dataset, ảnh QA trong diff. Dependencies, cấu hình, các loader ML, dịch vụ phản hồi TASK 15A, metadata, thí nghiệm và .gitignore không thay đổi. Bàn giao cho phép commit/push đúng 23 tệp trên; không force-push.

## 10. Bàn giao local và mã nguồn

- Backup mới, không ghi đè bản cũ: `D:\SAO LUU KHOA LUAN\task15b-local-handover-20261022-201846\db.sqlite3`. Thư mục kèm `manifest.json`, script backup/migrate và script kiểm chứng rollback; giữ ngoài Git vì bản sao chứa dữ liệu tài khoản.
- Dùng `sqlite3.Connection.backup`, kiểm `integrity_check=ok`, `foreign_key_check` không có vi phạm; fingerprint các bảng khớp nguồn trước khi migrate. SHA-256 bản sao: `4e48ff893258ca63a6767b2afcea36fca7c991c2feadfd8eb387fcedb7e33a5e`, đã kiểm lại sau migration.
- Runtime `.venv\Scripts\python.exe`, settings `config.local`; guard chỉ cho mở đúng SQLite dự án chính và bản sao mới, không kết nối PostgreSQL. Migration 0011 thành công; `check` không có lỗi, `migrate --check` đạt và `makemigrations --check --dry-run` không có thay đổi.
- Mọi hàng nghiệp vụ cũ giữ nguyên fingerprint; các hàng metadata framework cũ giữ nguyên, chỉ bổ sung content types/quyền cho model mới. Bốn bảng định kỳ rỗng sau migration. Integrity/khóa ngoại local đạt.
- Kiểm chứng local qua Django Client có CSRF trong một transaction: tạo quy tắc, GET không tạo kỳ, ghi nhận, POST lặp trả cùng giao dịch, xóa giao dịch chuyển kỳ thành deleted/thêm event, Tổng quan tải được và không sinh phản hồi ML. Cuối cùng rollback toàn bộ, fingerprint **mọi bảng** trước/sau giống nhau; không để lại tài khoản, session hoặc dữ liệu QA. Đây là kiểm phía server, không phải lần kiểm trình duyệt mới; bằng chứng browser QA nằm ở mục 8.
- Rà cuối migration/transaction/signals không yêu cầu sửa mã thực thi. Tận dụng kết quả 279/279 hồi quy và 37/37 liên quan đã chạy ở mục 8; không chạy lại toàn suite hoặc thí nghiệm ML chỉ để bàn giao. Chỉ cập nhật tài liệu trong lượt bàn giao.
- PostgreSQL: giới hạn ở rà schema/truy vấn và compile offline đã nêu mục 7. Chưa chạy migration/deletion collector/concurrency trên PostgreSQL thật, chưa xác nhận kết quả triển khai Render. Trước phát hành cần bản sao lưu PostgreSQL và theo dõi log migrate/check của quy trình triển khai; không bỏ unique/check hoặc đổi hash mô hình để né lỗi.
- Nếu cần phục hồi local: dừng các tiến trình ghi, xác minh hash/integrity bản sao, giữ riêng database hiện tại trước khi phục hồi. Backup này ở schema 0010; dùng mã tương ứng hoặc chạy lại migration 0011 có kiểm tra trước khi khởi động mã mới. Không ghi đè database đang phục vụ và không dùng backup local để thay database production.

Mã/migration/kiểm thử/tài liệu bàn giao được commit trên `main` và push bình thường tới remote hiện có; SHA commit và đối chiếu remote được báo trong kết quả bàn giao, không tự ghi SHA vào chính commit chứa tài liệu này.

## 11. TASK 15B.1 — Trạng thái quy tắc và ngày ghi nhận (22/10/2026)

### Nguyên nhân xác định từ mã

- Template cũ chỉ kiểm `rule.is_active` và in cố định “Đã bật / chờ tháng hiệu lực”. Cờ này biểu diễn ý định bật/tạm dừng mới nhất, không chứng minh revision đã có hiệu lực hôm nay. Ghi nhận xong một kỳ không có nghĩa quy tắc hàng tháng đã kết thúc.
- View cũ truyền `row['due_date']` làm initial của trường ngày. Do đó ngày 31/10 có thể đã được lưu nếu người dùng giữ mặc định; form/model lưu ngày hợp lệ được gửi, không có mã tự đổi ngày người dùng nhập sang ngày đến hạn. Không có payload/audit nhập liệu online để xác định người dùng đã giữ mặc định hay chủ động chọn 31/10. Không truy cập production hoặc sửa giao dịch đó trong task này.

### Trạng thái hiện tại

`recurring.rule_status()` dùng ngày Việt Nam UTC+7 và revision gần nhất có effective_month không sau tháng hiện tại, độc lập bộ lọc tháng và lịch sử kỳ. Thứ tự xét:

1. **Đã kết thúc:** tháng hiện tại sau end_month của revision đang hiệu lực (end_month được bao gồm trọn tháng). Trạng thái này ưu tiên hơn tạm dừng để không ngụ ý quy tắc còn trong hạn.
2. **Đã tạm dừng:** revision đang hiệu lực inactive, kể cả đã bấm kích hoạt lại nhưng lịch active mới từ tháng sau. Nếu có lịch kích hoạt lại, hiển thị thêm tháng hiệu lực rõ ràng.
3. **Chưa đến tháng bắt đầu:** revision active nhưng chưa tới start_month; trường hợp chưa có revision hiệu lực cũng chưa hoạt động.
4. **Đang hoạt động:** revision active và hiện tại trong khoảng tháng. Ghi nhận/bỏ qua một kỳ không thay trạng thái quy tắc này.

Sửa quy tắc vẫn hiệu lực từ tháng sau; trạng thái hiện tại theo revision cũ cho đến lúc đó. Bảng giữ thông số mới nhất người dùng đã lưu và nhắc riêng thay đổi đã lên lịch, không âm thầm áp thông số tương lai vào trạng thái hôm nay. Pause/resume, kỳ đã mở lại và snapshot lịch sử giữ nguyên chính sách mục 3–5. Không tạo revision/occurrence qua GET.

### Ngày giao dịch thực tế

- Ngày đến hạn chỉ hiển thị tham khảo cạnh số tiền dự kiến; trường nhập ghi “Ngày giao dịch thực tế”, mặc định hôm nay theo Việt Nam, không theo ngày đến hạn hoặc timezone của runtime.
- Form ghi nhận định kỳ có `clean_date()` chặn ngày tương lai phía server; thuộc tính HTML `max` hỗ trợ nhập liệu nhưng không phải lớp bảo vệ duy nhất. Cho phép ngày quá khứ hợp lệ, kể cả khác tháng định danh kỳ. Có lời nhắc chỉ xác nhận khoản đã thực sự phát sinh.
- POST lỗi vẫn là bound form, giữ ngày/tiền/danh mục/mô tả đã gửi. Không tự thay ngày lỗi bằng hôm nay hoặc tự sửa giao dịch.
- Không đổi TransactionForm chung, model giao dịch, CRUD/CSV hay chính sách sửa giao dịch liên kết; quy tắc chặn ngày tương lai mới chỉ ở form ghi nhận định kỳ. Atomic/unique, quyền sở hữu/CSRF, signals, coverage/forecast và ngân sách giữ nguyên.

### Kiểm chứng và giới hạn

- Thêm 10 ca kiểm thử: trạng thái/start/end bao gồm, end ưu tiên pause, pending resume, sửa chờ hiệu lực, trạng thái độc lập bộ lọc/đã ghi nhận, ngày mặc định, giữ dữ liệu khi lỗi, từ chối tương lai không ghi dữ liệu, ngày khác tháng, ranh giới 17:00 UTC (00:00 Việt Nam) và đổi năm; có ca xác nhận TransactionForm thường vẫn giữ chính sách ngày cũ.
- Nhóm định kỳ/migration: **37/37 đạt** ở lần chạy cuối (1,731 giây). Hồi quy giao dịch, coverage, forecast, budget và CSV import: **118/118 đạt** (26,197 giây). Chạy trong SQLite RAM với guard cấm mở SQLite thật; không chạy thí nghiệm ML.
- Django system check không lỗi; `makemigrations --check --dry-run`: No changes detected. **Không cần migration mới**; migration 0011 không sửa, không migrate lại SQLite thật.
- Browser thực tế tại `127.0.0.1:8017`, SQLite QA mới `D:\SAO LUU KHOA LUAN\task15b1-qa-20261022-224355\qa.sqlite3`, runner chỉ cho mở QA. Đã đăng nhập tài khoản QA; xem đủ bốn trạng thái; biểu mẫu hiện đến hạn 31/10 và mặc định ngày thực tế 22/10; ghi nhận kỳ tháng 10 với ngày 30/09 và 900.000 VND thành công; trang chi tiết và danh sách thể hiện đúng ngày thực tế, kỳ tháng 10 và quy tắc vẫn đang hoạt động. Kích hoạt lại quy tắc paused vẫn hiện “Đã tạm dừng”, kèm lịch 11/2026.
- Ảnh QA ngoài Git, cùng thư mục trên: `actual-date-desktop.png`, `actual-date-saved.png`, `rule-statuses-desktop.png`. Lượt triển khai đầu đã thử desktop; lượt hoàn tất dưới đây đã bổ sung khung 390×844. Chưa thử thiết bị vật lý. Ca lỗi form, timezone, CSRF, phân quyền và concurrent được kiểm tự động, không gộp thành tuyên bố đã thử mọi ca qua browser.
- Không truy cập PostgreSQL/production; chưa xác minh behavior runtime online sau sửa. Không đổi model ML, dependency, dữ liệu/thí nghiệm hoặc dữ liệu tài khoản thật. Lượt triển khai đầu chưa commit/push; lượt hoàn tất được người dùng cho phép commit/push 7 tệp liên quan.

### Hoàn tất kiểm tra mobile và bàn giao TASK 15B.1

- Dùng lại SQLite QA ngoài Git tại thư mục TASK15B.1 ở trên, server `127.0.0.1:8017`. Khởi động lại riêng server QA để tải đúng template cuối; không khởi động hoặc truy cập production.
- Đặt viewport và đo trực tiếp DOM: `innerWidth=390`, `innerHeight=844`, `clientWidth=scrollWidth=367` (phần còn lại là thanh cuộn). Công cụ có DPI/zoom nên cấu hình override 261×565 mới cho đúng **390×844 CSS**; không dùng kích thước bitmap ảnh để suy ra kích thước CSS. Đã reset override sau kiểm tra.
- Trang định kỳ: bộ lọc/nút hiển thị vừa khung, bảng chuyển thành thẻ có nhãn; đọc được các trạng thái và lịch kích hoạt lại khi cuộn, không tràn ngang toàn trang. Form Ghi nhận: ngày đến hạn tách riêng, ngày thực tế mặc định 22/10/2026, HTML max cùng ngày; tiền/ngày/danh mục/mô tả và các nút xác nhận/hủy thao tác được ở khung hẹp.
- Tạo thêm một quy tắc mô phỏng bằng UI, chỉ trong QA; ghi nhận kỳ tháng 10, ngày thực tế 30/09/2026, số tiền thực tế 495.000 VND (dự kiến 500.000). Nút xác nhận hoạt động; trang chi tiết hiện đúng ngày/tháng định danh và số tiền. Không ghi dữ liệu mô phỏng vào SQLite thật.
- Ảnh ngoài Git: `recurring-mobile-390x844.png`, `rule-statuses-mobile-390x844.png`, `actual-date-mobile-390x844.png`, `actual-date-mobile-actions.png`, `actual-date-mobile-saved.png`, cùng thư mục QA đã nêu. Đây là kiểm bằng trình duyệt trong khung CSS, chưa phải thiết bị điện thoại vật lý.
- Không phát hiện lỗi cần sửa thêm mã trong lượt hoàn tất; chỉ cập nhật tài liệu. Tận dụng kết quả **37/37** định kỳ/migration và **118/118** hồi quy đã chạy trên mã thực thi hiện tại, không chạy lại suite khi mã không đổi. Django system check trên QA vẫn đạt. Không cần migration mới, không đổi migration 0011.
- Rà đúng 7 tệp mã/template/kiểm thử/tài liệu của TASK15B.1, kiểm bí mật và `git diff --check` trước commit. Push `main` bình thường, không force-push/đổi remote. Commit và xác nhận SHA local/remote được báo ở bàn giao; push không phải bằng chứng ứng dụng production đã chạy thành công.
