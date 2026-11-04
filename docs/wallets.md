# TASK 23A — Ví VND và chuyển nội bộ

**Mốc bàn giao mới nhất — 03/11/2026:** đã sao lưu SQLite local thật bằng backup API, kiểm bản sao và áp dụng 0015 vào đúng dự án chính; dữ liệu/liên kết cũ và tổng thu–chi giữ nguyên. Phần QA dưới đây giữ kết quả lịch sử; xem [biên bản local và kế hoạch online](#bàn-giao-migration-0015-trên-local--03112026) cuối tài liệu. Chưa push/deploy hoặc truy cập production. Các giới hạn UI chưa xác minh vẫn giữ nguyên.

**Bổ sung 04/11/2026:** đã được phép kết nối production **chỉ đọc để backup**, kiểm archive mới và restore/diễn tập 0015 trên PostgreSQL QA riêng đạt; xem mục cuối. Không push/deploy hoặc migrate production. Các câu chưa truy cập production ở các mốc trước là lịch sử của lần đó.

## Thiết kế chốt trước khi sửa mã — 03/11/2026

Nhánh main, nền `1da8898d7292c73a5f390d17304f4d8771c0dfb4`. Giữ nguyên thay đổi tài liệu TASK 22C trong `docs/thesis-demo-script.md`. Không đọc database thật/production. Các migration chỉ chạy trên QA. Chưa triển khai chia tiền nhóm, tài khoản ngân hàng, phí, ngoại tệ hoặc điều chỉnh số dư.

- **Wallet** thuộc user: tên chuẩn hóa NFC/casefold/khoảng trắng để chống trùng theo tài khoản; loại tiền mặt/ngân hàng/ví điện tử/khác; số dư ban đầu VND nguyên (có thể 0/âm), ngày theo dõi, lưu trữ. Tên/loại có thể sửa; số dư/ngày mốc bị khóa khi đã có giao dịch hoặc chuyển tiền. Không có nút xóa ví; lưu trữ giữ lịch sử, có POST mở lại. Không hỏi số tài khoản ngân hàng.
- **Dữ liệu cũ:** FK wallet nullable trên Transaction, CsvImportBatch và RecurringRule. NULL được trình bày rõ **Chưa xác định ví**, không tự tạo ví ngân hàng/tiền mặt, không tự gán lịch sử. Thêm trường nullable là toàn bộ chuyển đổi dữ liệu; không RunPython tự sửa bản ghi cũ. Cần kiểm migration từ 0014 trên dữ liệu QA cũ: ID, tiền/ngày/category/receipt/liên kết và coverage giữ nguyên; các FK mới NULL. Giao dịch mới có thể chủ động để Chưa xác định; đây là tổng dòng tiền đã ghi, không có số dư được đối soát và không đưa vào tổng số dư ví.
- **Giao dịch:** chọn ví hoạt động thuộc chính tài khoản, ngày không trước mốc. Được giữ ví lưu trữ khi sửa giao dịch vốn thuộc ví đó để sửa lịch sử; không chuyển giao dịch mới vào ví lưu trữ. Xóa/sửa lịch sử làm số dư dẫn xuất cập nhật. Tạo tương tự chỉ điền ví còn hoạt động; ví lưu trữ phải chọn lại hoặc để Chưa xác định rõ ràng. Nhập nhanh không tự đoán/đổi ví; receipt tương tự gắn cả ví trong payload. Receipt ML vẫn kiểm mô tả/loại/mode/model, không kế thừa từ nguồn.
- **CSV:** vẫn `date,kind,amount,category,description`. Một ví tùy chọn cho cả lô (mặc định ghi rõ Chưa xác định), hiện ở preview, lưu FK trên lô; kiểm lại quyền, hoạt động và mọi ngày khi confirm. Batch cũ NULL dùng trạng thái chưa xác định. Receipt chống lặp vẫn `(user, SHA-256 tệp)`, không thêm wallet vào khóa. Import atomic và hook coverage hiện có giữ nguyên.
- **Định kỳ:** thêm ví mặc định tùy chọn, đưa wallet ID vào snapshot revision mới; snapshot cũ thiếu key coi là chưa xác định. Kỳ cũ không bị viết lại. Ghi nhận cho chọn ví khác, kiểm lại ví và ngày thực tế qua form/model lưu giao dịch. Chọn ví không tạo kỳ/giao dịch trên GET.
- **Chuyển nội bộ:** WalletTransfer bất biến, nguồn/đích khác nhau, cùng user, hoạt động, ngày <= hôm nay Việt Nam và >= mốc cả hai ví. Số tiền nguyên dương, ghi chú ngắn. Một bản ghi nguồn thật cho hai tác động, không tạo cặp Transaction. Không sửa/xóa/hủy chuyển trong v1. POST có CSRF, token ký gắn user/thao tác/TTL; UUID unique và digest payload chống dùng lại với dữ liệu khác. Trong atomic: khóa tài khoản, kiểm thao tác đã ghi, khóa ví theo ID, validate rồi INSERT WalletTransfer (bản ghi này đồng thời mang UUID/digest receipt); rollback không để chuyển nửa chừng. Hai token riêng vẫn là hai chuyển hợp lệ. Số dư âm được phép, không có kiểm thiếu tiền. Không dùng nhãn ML Transfer để tạo chuyển.
- **Số dư:** đến ngày D = mốc ban đầu + income − expense + chuyển đến − chuyển đi từ ngày theo dõi đến D. Trước ngày bắt đầu, số dư là chưa bắt đầu theo dõi, không tự tính mốc vào hiện tại. Tách tổng income/expense ngày tương lai; báo cáo thu–chi hiện có vẫn tính theo chính sách cũ. Tổng ví hoạt động chỉ cộng các ví đã bắt đầu, loại ví lưu trữ và Chưa xác định; hiện rõ phần bị loại. Đây là số dư theo ghi chép/mốc người dùng khai báo, chưa đồng bộ/đối soát ngân hàng. Tiết kiệm chỉ phân bổ, không trừ ví.
- **Lịch sử/quyền:** trang ví theo user, lịch sử Transaction + chuyển đến/đi phân trang và lọc khoảng ngày ở database; số dư ban đầu riêng có nhãn, không giả Transaction. Tổng hợp theo ví bằng Decimal ở database, không truy vấn từng ví hoặc tải mọi mô tả. Mọi URL/POST kiểm chủ; không cache riêng tư dùng chung. Wallet/Transfer cascade khi xóa tài khoản được phép; FK ví RESTRICT chặn xóa độc lập ví có liên kết. Cơ chế Category PROTECT cũ vẫn có thể chặn xóa tài khoản còn giao dịch; task không bỏ bảo vệ đó hoặc thêm chức năng xóa tài khoản. Không giữ dữ liệu mồ côi nếu tài khoản thực sự bị xóa.
- **Phạm vi tương lai:** dòng tiền ví không mặc nhiên là chi tiêu cá nhân khi có ứng hộ. Chia tiền nhóm cần thiết kế riêng, không thêm bảng/field dự phòng không dùng trong task này.

## Thiết kế đã triển khai

- `finance/models.py`: Wallet, WalletTransfer; FK nullable trên Transaction, CsvImportBatch, RecurringRule. `opening_locked` là cờ một chiều khóa mốc sau lần đầu có nghiệp vụ thành công, **không phải số dư lưu sẵn**. Xóa/chuyển giao dịch cuối cùng sang ví khác vẫn không mở lại mốc. Không có thao tác xóa ví trong giao diện; ORM cũng chặn xóa ví đã dùng. FK RESTRICT bảo vệ liên kết còn tồn tại.
- `finance/wallets.py`: công thức số dư, truy vấn lịch sử hợp nhất, phát và kiểm token chuyển. Token ký có hạn 2 giờ, gắn user/action/UUID; cùng UUID và cùng payload trả bản đã ghi, khác payload bị từ chối. Unique UUID ở database là lớp chống trùng cuối; khóa ghi tài khoản trước rồi khóa các ví theo ID ổn định. Không khóa nút để thay kiểm tra server. Một dòng WalletTransfer đại diện cả hai phía, nên không tồn tại chuyển chỉ ghi một phía.
- Hai tác động của chuyển được đọc từ **cùng một truy vấn nhóm nguồn/đích**, tránh đọc nguồn và đích tại hai thời điểm commit khác nhau. Số dư không được cache hoặc lưu dư thừa. Các nhóm giao dịch và metadata vẫn là nhiều SELECT: đây không phải snapshot đối soát bất biến của toàn sổ khi mọi loại CRUD cùng chạy đồng thời.
- `finance/wallet_forms.py`, `finance/wallet_views.py`: tạo/sửa, lưu trữ/mở lại bằng POST xác nhận, lọc ngày và phân trang 20 mục. `/vi/`, `/vi/them/`, `/vi/<id>/`, `/vi/<id>/sua/`, `/vi/<id>/trang-thai/`, `/vi/chua-xac-dinh/`, `/vi/chuyen/`, `/vi/chuyen/<id>/`. GET không phát sinh dữ liệu nghiệp vụ.
- `finance/transaction_queries.py`, Transaction.save: kiểm lại ví, ngày và quyền cả ở save, bulk_create, queryset update; đồng bộ cờ khóa mốc trong transaction. CRUD/CSV vẫn dùng hook coverage và vô hiệu hóa dự báo hiện có. Chuyển nội bộ không đi qua các hook đó.
- `finance/forms.py`, CSV, định kỳ và tạo tương tự tái sử dụng luồng lưu giao dịch. Lưu ví trên batch phía server; confirm kiểm lại ví và ngày trong cùng transaction. CSV vẫn đúng 5 cột; đổi ví không né được receipt theo user/hash tệp. Snapshot định kỳ cũ thiếu wallet_id vẫn là chưa xác định; không viết lại kỳ đã xử lý. Ví mặc định không còn hoạt động phải chọn ví khác hoặc xác nhận rõ lựa chọn chưa xác định.
- Nhập nhanh giữ nguyên ví đã chọn và cơ chế hỏi thay thế dữ liệu. Mở form tương tự từ ví đã lưu trữ không tự thay bằng ví khác; phải chọn ví hoạt động hoặc xác nhận rõ Chưa xác định. Digest receipt tương tự có ID ví cuối cùng. Ví không được suy ra từ nhãn ML Transfer.
- Tiền dùng Decimal nguyên, giới hạn từng mốc/khoản `999.999.999.999.999 VND`; mốc cho phép âm. Tính tổng không ép về giới hạn từng khoản. Giao dịch tương lai vẫn nằm trong báo cáo thu–chi theo quy tắc cũ, nhưng không vào số dư đến hôm nay.

### Quyền, riêng tư và giới hạn schema

Mọi URL, queryset danh sách/chi tiết, lựa chọn form và dịch vụ chuyển kiểm chủ tài khoản; không nhận user_id đích. POST dùng CSRF, không log mô tả/ghi chú hoặc đưa dữ liệu vào cache dùng chung. Chuyển bất biến: không sửa/xóa/hủy trong v1. Xóa tài khoản theo cascade xóa dữ liệu ví/chuyển cùng tài khoản khi chính sách cũ cho phép; Category PROTECT có thể chặn xóa tài khoản còn giao dịch. Task này không thêm chức năng xóa tài khoản hoặc bỏ bảo vệ đó.

Database có FK, unique tên chuẩn hóa theo user, unique operation_id, check loại ví, mốc nguyên trong giới hạn, số chuyển nguyên dương và nguồn khác đích. Quyền cùng chủ, trạng thái ví, ngày theo mốc và cờ khóa mốc được kiểm trong nghiệp vụ có khóa; **không có PostgreSQL RLS/trigger kiểm chéo chủ sở hữu**. Ghi SQL trực tiếp ngoài ứng dụng không phải đường ghi được hỗ trợ.

## Migration QA và bảo toàn dữ liệu cũ

Migration duy nhất: `finance/migrations/0015_wallet_csvimportbatch_wallet_recurringrule_wallet_and_more.py`, phụ thuộc 0014. Thêm hai bảng, ba FK nullable, cờ khóa mốc và index `(wallet,date)`/`(user,date)` cho lịch sử. Không có RunPython gán ví hoặc đổi dữ liệu tài khoản.

Đã chạy **bản cuối của 0015** từ trạng thái 0014 trên SQLite QA riêng và PostgreSQL **18.6 QA thật trên localhost:55432**, cluster mới riêng của task. Fixture chỉ lấy từ database demo mô phỏng TASK 22C, không từ SQLite thật hoặc bản phục hồi có dữ liệu cá nhân. Đối chiếu toàn bộ trường cũ của 19 model finance, gồm 9 giao dịch và liên kết CSV/định kỳ/ML, coverage, ngân sách, dự báo, tiết kiệm. Hash trước/sau trong từng backend bằng nhau; ba FK cũ đều NULL, không tự sinh Wallet/Transfer. Chạy migrate lại không thay đổi. SQLite integrity_check = ok, foreign_key_check không lỗi; PostgreSQL các ràng buộc đã kiểm ở database.

| Backend | SHA-256 nội dung lịch sử cũ trước = sau |
|---|---|
| SQLite QA | `8d76edaac3be3534cac95995c968f59fa8186edba665d98cf44cc235ea299177` |
| PostgreSQL QA | `6f5c8e49464c028da750c9a5612b98f8fd58c94b3346717a511b16e706721f0c` |

Hai hash khác nhau giữa backend vì thời điểm fixture, không dùng chúng để khẳng định dump hai backend giống byte. Bằng chứng: `migration-sqlite-final.json`, `migration-pg-final.json` tại thư mục QA local nêu dưới. SQLite giao diện từng dùng bản nháp migration được cập nhật cột trên **QA riêng**; bằng chứng migration tái lập bản cuối là database `migration-final.sqlite3` độc lập và lượt PostgreSQL nêu trên.

**Tại mốc QA/rà cuối ban đầu:** chưa áp dụng 0015 hoặc mở SQLite thật. Sau đó, bước bàn giao được người dùng cho phép đã backup và áp dụng vào local như biên bản cuối tài liệu. Production chưa được truy cập/áp dụng trong TASK 23A.

## Kiểm thử — 03/11/2026

Runtime QA sẵn có: Windows, Python 3.13.16, Django 5.2.18; không cài dependency. Wrapper quản lý nằm ngoài repository, xóa DATABASE_URL/PG* kế thừa, chặn mọi đích ngoài database QA đã định danh. PostgreSQL kiểm host/port, data_directory và tên database trước sử dụng. Không kết nối Render.

Lệnh dưới cần cấu hình QA riêng tương đương; **không chạy manage.py mặc định vào SQLite thật khi chưa được cho phép**:

```powershell
# $qaRoot và $qaPython trỏ tới môi trường QA ngoài repository đã tạo cho task.
& $qaPython "$qaRoot\manage_qa.py" test finance --settings qa_pg_settings --noinput
& $qaPython "$qaRoot\manage_qa.py" test finance --noinput
& $qaPython "$qaRoot\manage_qa.py" test finance.test_wallets finance.test_csv_import --settings qa_pg_settings --noinput
& $qaPython "$qaRoot\manage_qa.py" check
& $qaPython "$qaRoot\manage_qa.py" makemigrations --check --dry-run
node --test scripts/test_*.js
```

| Lượt kiểm | Kết quả và cách đếm |
|---|---|
| Hồi quy PostgreSQL | **484/484 đạt**, không skip, 307,576 giây; gồm 26 bài ví (24 thông thường + 2 đồng thời). |
| Hồi quy SQLite lượt đầu | 484 bài: **480 đạt, 2 lỗi, 2 skip** (hai bài đồng thời yêu cầu PostgreSQL). Hai lỗi được sửa và chạy lại đúng 2 bài đều đạt; không gọi toàn bộ đạt trong một lượt. |
| Nhóm cuối sau sửa bảo vệ mốc/xóa ví | PostgreSQL **50/50 đạt**; SQLite **48 đạt + 2 skip**, gồm ví + CSV. Đây là tập con của 484, không cộng thành số bài duy nhất mới. Full suite PostgreSQL ở dòng đầu chạy trước các tinh chỉnh cuối; nhóm chịu ảnh hưởng được chạy lại. |
| Rà cuối theo yêu cầu bổ sung | PostgreSQL **204/204 đạt**, 81,267 giây; SQLite **202 đạt + đúng 2 skip**, 60,925 giây. Gồm 50 bài trên và 154 bài các luồng liên quan, **204 là tập con của 484**, không cộng lượt chạy/backend/retry thành số bài duy nhất mới. Chi tiết dưới đây. |
| JavaScript | **44/44 đạt**, gồm bài mới giữ ví/hỏi thay thế của Nhập nhanh. |
| System check / migration | Không vấn đề; `makemigrations --check --dry-run`: No changes detected. |
| Production static QA | config.render với override QA, DEBUG=False, WhiteNoise manifest; chặn mọi kết nối database. 12 file copy, 24 hậu xử lý, kiểm manifest/hash và gzip CSS/JS/icon, check đạt. Không kiểm Linux/Render trong task. |

Hai lỗi hồi quy SQLite: (1) thông báo form tương tự làm mất câu hướng dẫn chọn lại danh mục mà kiểm thử hiện có yêu cầu — khôi phục câu và giữ hướng dẫn ví; (2) bài thống kê hardcode tháng 10 nhưng phụ thuộc ngày chạy tháng 11 — cố định clock trong **test**, không sửa nghiệp vụ thống kê. Khi QA giao diện, sửa thêm nhãn token ẩn không nên hiện và padding thẻ ví; cờ khóa mốc được bổ sung để không thể sửa lại mốc sau khi xóa giao dịch cuối.

Hai bài đồng thời trên PostgreSQL dùng hai connection/thread thực, barrier trước thao tác: **cùng token tạo đúng một chuyển**, **hai token độc lập cùng commit tạo hai chuyển**, số dư hai ví không mất tiền và tổng không đổi. Đây không phải thử tải lớn hoặc kiểm mọi tổ hợp deadlock. SQLite không thay thế bằng chứng row-lock PostgreSQL.

Các bài ví còn kiểm owner/CSRF/GET, số dư âm/0/chưa bắt đầu, future, sửa/xóa/đổi ví, archived, token sai payload, rollback, cascade, ngày/hạn mức, HTML escape, phân trang, CSV rollback/dedupe, định kỳ snapshot, tương tự, ML Apply → Lưu và không có tác động tài chính từ chuyển. Các suite hiện có kiểm thêm coverage/ngân sách/dự báo/tiết kiệm/ML.

### Hiệu năng

`balances()` dùng **4 SELECT tổng hợp**, không phải 4 truy vấn cho mọi trang. Đo cả trang SQLite với 1 ví/0 giao dịch và 13 ví/41 giao dịch: danh sách **6 → 6**, chi tiết **8 → 9** (trang rỗng bỏ SELECT lấy page, không phải N+1). Lịch sử UNION lọc ngày và LIMIT/OFFSET ở database, không tải toàn bộ mô tả quá khứ. Số metadata ví dùng để tính tổng tài khoản vẫn tăng theo số ví; chưa kiểm tải lớn. PostgreSQL suite cũng kiểm số truy vấn không tăng theo từng ví; phép đo cả trang chi tiết ở đây là SQLite QA.

## Bằng chứng trình duyệt và giới hạn

Thư mục bằng chứng local ngoài Git: `D:\POSTGRESQL QA\task23a-20261103-141645`. Các đường dẫn ở mục này là **tham chiếu trên máy**, không phải liên kết artifact người đọc GitHub truy cập được. Không đưa database, log riêng, cấu hình QA hoặc credential vào Git.

| Thao tác | Bằng chứng thực tế |
|---|---|
| Tạo hai ví | Qua trình duyệt: tiền mặt mốc 500.000 VND và ngân hàng 1.000.000 VND, ngày 01/11/2026. |
| Chuyển nội bộ | Qua form: 200.000 VND tiền mặt → ngân hàng; chỉ một WalletTransfer. Trước chuyển tổng 1.550.000 VND, sau chuyển không đổi. |
| Nhập nhanh + ML thật | Giữ ví tiền mặt; yêu cầu xác nhận thay thế; câu học phí 45k → gợi ý VI Education → chọn danh mục QA tương ứng → Áp dụng → Lưu. Xác minh feedback.applied và ví giao dịch ở database QA. Không huấn luyện hoặc đổi artifact. |
| Số dư cuối đối chiếu Decimal | Tiền mặt **355.000 VND**, ngân hàng **1.150.000 VND**, tổng **1.505.000 VND**. Chi tương lai 30.000 VND và chi chưa xác định 25.000 VND không bị cộng/trừ vào tổng này. |
| Lịch sử/bàn phím | Gửi bộ lọc ngày bằng Enter; Tab/Shift+Tab giữa hai lựa chọn ví có focus outline nhìn thấy. Không gọi đây là audit bàn phím toàn diện. |
| Tách tài khoản | Đăng nhập B không thấy tên ví A; mở trực tiếp `/vi/1/` của A trả 404; đăng xuất và đóng tab QA. |
| Ảnh | `wallet-list-ready.jpg`, `wallet-detail-ready.jpg` sau sửa padding; ảnh trước sửa `wallet-list-ui.jpg`. Chỉ chứa dữ liệu/tài khoản mô phỏng. |

Viewport thực đo được trong công cụ là **981×997**, không phải 1280×900 hoặc 390×844. Ở ảnh cuối danh sách, document clientWidth/scrollWidth đều 958; chưa phát hiện tràn ngang ở viewport đã đo. Kích thước canvas ảnh công cụ không được coi là viewport.

**Chưa xác minh**: đúng viewport desktop 1280×900; mobile 390×844; trọn luồng khi tắt JavaScript trước tải trang; thiết bị vật lý/trình duyệt khác; bộ lịch sử/phân trang bằng bàn phím đầy đủ. Công cụ không cung cấp thao tác viewport/disable-JS hữu dụng trong phiên này, nên không lặp cách từng thất bại ở TASK 22A hoặc vượt chặn Edge. Đây là giới hạn công cụ, không phải lỗi ứng dụng đã tái hiện. Form/lịch sử chính là HTML server có POST/CSRF và được kiểm backend; điều đó **không thay bằng chứng trình duyệt tắt JavaScript**. Không ghi QA hoàn tất toàn bộ.

Log kết quả ở cùng thư mục: `postgres-regression.log`, `sqlite-regression.log`, `postgres-handoff-50.log`, `sqlite-handoff-50.log`, `javascript-final.log`, `page-query-results.json`, `static-report.json`. Không cần gửi log chứa fixture dù là mô phỏng lên repository.

## Bàn giao và phục hồi sau này

1. Task này chỉ bàn giao mã/migration/tài liệu, chưa stage/commit/push/deploy. Giữ thay đổi TASK 22C sẵn có trong `docs/thesis-demo-script.md` nguyên byte.
2. Trước khi được phép áp dụng local: dừng thao tác ghi, dùng SQLite backup API theo [biên bản phục hồi](restore-rehearsal.md), kiểm integrity_check/foreign_key_check/SHA-256 và lưu ngoài repository. Với PostgreSQL dùng [quy trình PostgreSQL](production-verification.md), không dùng SQLite backup thay thế; kiểm archive đọc được không đồng nghĩa đã restore đạt.
3. Sau backup đã kiểm và được cho phép: dùng đúng runtime/cấu hình đích, `migrate`, `check`; kiểm lịch sử cũ vẫn Chưa xác định ví, tổng thu–chi/coverage/liên kết không đổi. Không tạo tài khoản/mật khẩu mặc định. Trên Render làm theo [quy trình triển khai](render-deployment.md), không đưa dữ liệu QA vào môi trường.
4. Nếu cần khôi phục: kiểm backup trên database/thư mục QA mới trước; chỉ phục hồi đích thật theo kế hoạch riêng có xác nhận. Không chạy reverse 0015 sau khi đã có dữ liệu ví/chuyển vì sẽ xóa bảng/cột mới. Rollback mã và schema phải tương thích, giữ bản sao trước triển khai; không xóa riêng một phía chuyển để chữa lỗi.
5. Chia tiền nhóm cần định nghĩa dòng tiền ứng hộ/chi tiêu cá nhân riêng; chưa có bảng nhóm/công nợ hoặc schema dự phòng trong 0015.

### Phạm vi tệp và rà cuối

37 tệp thuộc TASK 23A; không tính thay đổi TASK 22C đã có:

| Nhóm | Tệp |
|---|---|
| Model/migration/query | `finance/models.py`, `finance/migrations/0015_wallet_csvimportbatch_wallet_recurringrule_wallet_and_more.py`, `finance/transaction_queries.py` |
| Ví/chuyển mới | `finance/wallets.py`, `finance/wallet_forms.py`, `finance/wallet_views.py`, `finance/test_wallets.py` |
| Tích hợp cũ | `finance/forms.py`, `finance/views.py`, `finance/urls.py`, `finance/transaction_filters.py`, `finance/csv_import.py`, `finance/csv_views.py`, `finance/recurring.py`, `finance/recurring_forms.py`, `finance/recurring_views.py`, `finance/similar_transactions.py` |
| Kiểm thử/cửa sổ Nhập nhanh | `finance/test_statistics.py` (clock cố định), `scripts/test_quick_entry.js`, `static/js/quick-entry.js` |
| Giao diện ví mới | `static/css/wallets.css`; `templates/finance/` gồm `wallet_base.html`, `wallet_list.html`, `wallet_detail.html`, `wallet_form.html`, `wallet_status.html`, `wallet_transfer_form.html`, `wallet_transfer_detail.html`; `templates/finance/includes/wallet_fields.html`, `wallet_pagination.html` |
| Template tích hợp | `templates/finance/csv_preview.html`, `transaction_detail.html`, `transaction_form.html`, `transaction_list.html`; `templates/includes/navigation.html` |
| Tài liệu | `README.md`, `docs/wallets.md` |

Rà diff/secret: không có giá trị credential QA đã tạo, token GitHub/private key hoặc URL PostgreSQL chứa mật khẩu trong các tệp task. Không có database, artifact/dataset hay cấu hình QA trong danh sách thay đổi. Hash 8 tệp bảo vệ khớp đầu task: hai joblib EN/VI, hai module phân loại, ba requirements và tài liệu TASK 22C. `git diff --check` không lỗi; index trống, chưa stage/commit/push. Không thay model ML, dependency hoặc thí nghiệm.

Kết thúc: đã đăng xuất/đóng tab QA; hủy session SQLite QA, vô hiệu mật khẩu hai tài khoản ứng dụng tạm, xóa tệp credential UI/PostgreSQL tạm. Đã dừng đúng web server TASK 23A và cluster riêng; cổng **8023/55432 đóng**. SQLite QA sau dọn integrity_check = ok, foreign_key_check không lỗi. Bằng chứng `handoff-audit.json`, `shutdown-report.json` nằm ngoài Git cùng thư mục QA. Dữ liệu mô phỏng và cluster đã dừng được giữ làm bằng chứng local, không dùng để phục hồi đè dữ liệu thật.

## Rà cuối số dư, chuyển và migration — 03/11/2026

### Kết luận rà bất biến

Đã đối chiếu cả 37 tệp với các đường ghi hiện có; không sửa mã nghiệp vụ trong lượt rà này. Chỉ tăng nội dung **hai phương thức kiểm thử hiện có** tại `finance/test_wallets.py` và bổ sung tài liệu này. Không thêm test ID, migration, dependency hay đổi chính sách tài chính. Tài liệu TASK 22C giữ nguyên.

| Bất biến | Nơi bảo vệ và kết luận |
|---|---|
| Mốc không phải thu nhập | Wallet.opening_balance chỉ cộng vào `balances()`, không tạo Transaction; test kiểm số giao dịch vẫn 0. |
| Chuyển hai phía nhất quán | Dịch vụ `transfer()` atomic, khóa user trước rồi Wallet theo `order_by('pk')`; WalletTransfer.save tải lại/khóa nguồn và đích cùng thứ tự. Một dòng cho hai phía, cập nhật cờ mốc cùng transaction, không dùng cặp Transaction. |
| Chống lặp | Token kiểm user/action/thời hạn; UUID unique và digest. Cùng thao tác/cùng payload trả bản cũ; payload khác bị từ chối. Hai thao tác riêng hợp lệ. Form có thể báo ví hiện không hợp lệ khi gửi lại sau khi ví đã lưu trữ; vẫn không tạo chuyển mới. |
| Quyền/trạng thái tại lúc lưu | Không chỉ dựa vào ModelChoice đã validate: tải lại ví dưới khóa, kiểm chủ/archived/mốc/ngày. Đã tăng test với form hợp lệ nhưng ví đích bị lưu trữ trước khi lưu: server từ chối, không tạo chuyển. |
| Rollback thật sau ghi | Test cũ chỉ ném lỗi trước save, chưa đủ chứng minh rollback sau INSERT. Đã sửa test: xác nhận thấy 1 WalletTransfer bên trong transaction, gây lỗi khi khóa mốc, sau rollback không còn dòng chuyển/cờ mốc/số dư thay đổi; gửi lại đúng token sau rollback ghi được một lần. Không phát hiện lỗi ứng dụng từ kiểm này. |
| Không tác động thu–chi | WalletTransfer không gọi Transaction.save/signals/reset_months. Kiểm snapshot giao dịch, coverage, version dự báo, feedback và ngân sách không đổi. Không suy từ nhãn ML Transfer thành chuyển ví. |
| CRUD/đổi ví/CSV | Số dư dẫn xuất từ ledger; save/bulk_create/queryset update kiểm lại ví; xóa đi qua signals coverage cũ. Chuyển ví tự bỏ tác động ví cũ và thêm ví mới. CSV khóa coverage trước ví, kiểm mọi ngày và rollback cả lô. Receipt user/hash không đổi theo ví. |
| Định kỳ và tiết kiệm | Chỉ giao dịch đã ghi nhận mới vào ledger; snapshot cũ thiếu ví vẫn NULL; mặc định archived cần xem lại. Phân bổ tiết kiệm không tự tạo Transaction hoặc chuyển ví. |
| Tương lai/lưu trữ/chưa xác định | Thu/chi ngày > hôm nay tách riêng. Ví archived vẫn có lịch sử/số dư riêng nhưng bị loại khỏi tổng ví hoạt động. NULL chỉ hiện dòng tiền, không có mốc để gọi là số dư đã đối soát. |

Khóa các ví cần kiểm ở bulk_create/update cũng theo PK qua `validate_wallet_rows()`. Đây là bảo vệ ở các đường ghi ứng dụng, không phải bảo đảm mọi SQL do quản trị viên tự viết. Chưa thử mọi cuộc đua giữa xóa/sửa/chuyển, mọi kế hoạch khóa PostgreSQL hoặc tải lớn; lỗi khóa được rollback/báo chưa xác nhận, không tự retry POST tài chính.

### Phạm vi tinh chỉnh sau lượt PostgreSQL 484/484

Biên bản và log được giữ, nhưng **không có snapshot/hash từng tệp tại đúng thời điểm bắt đầu lượt 484**. Vì vậy bảng này mô tả phạm vi tinh chỉnh cuối được rà, không giả lập một Git diff bất biến so với lượt đó:

| Tệp | Hành vi tinh chỉnh và bằng chứng tương ứng |
|---|---|
| `finance/wallets.py` | Gộp tác động chuyển vào cùng SELECT nhóm nguồn/đích; nhóm ví kiểm bảo toàn tổng, âm, future và số truy vấn. |
| `finance/models.py`, `finance/transaction_queries.py`, `finance/wallet_forms.py`, migration 0015 | Thêm/ghi cờ opening_locked một chiều, khóa trường mốc, chặn xóa ví đã dùng kể cả sau khi xóa giao dịch cuối; chặn bulk_create chuyển bỏ qua dịch vụ. Nhóm ví kiểm save/queryset/bulk/archive/xóa/rollback; CSV kiểm đường bulk_create. Migration bản cuối được replay trên dữ liệu cũ. |
| `finance/csv_import.py` | Thứ tự khóa coverage trước wallet khi confirm nhất quán với lưu giao dịch; 24 bài CSV và các bài ví/CSV kiểm lỗi, rollback, quyền và receipt. |
| `templates/finance/includes/wallet_fields.html`, `wallet_form.html`, `wallet_status.html`, `wallet_transfer_form.html`; `static/css/wallets.css` | Hidden token không thành nhãn tiếng Anh; form render lại dữ liệu/lỗi, padding thẻ 20/16px. Nhóm ví có GET/render/POST/CSRF; ảnh QA đã nêu. Kiểm server render không chứng minh mọi viewport hoặc tắt JS đạt. |
| `finance/test_wallets.py` | Bổ sung kiểm cờ mốc/xóa và hai assert nghiệp vụ mạnh hơn ở lượt rà này; vẫn 26 test ID. |

Nhóm **50 = 26 ví + 24 CSV** bao phủ trực tiếp các thay đổi tính số dư/chuyển/cờ mốc/luồng batch và hai cuộc đua chuyển. Tuy nhiên nó **không đại diện toàn bộ các giao diện gọi Transaction.save**. Để khép phạm vi chia sẻ, đã chạy bổ sung chính các module liên quan trên cả PostgreSQL và SQLite, trong một selection không lặp ID:

| Module | Số bài |
|---|---:|
| finance.test_wallets | 26 |
| finance.test_csv_import | 24 |
| finance.test_recurring | 36 |
| finance.test_similar_transactions | 21 |
| finance.test_monthly_coverage | 24 |
| finance.test_forecast | 26 |
| finance.test_forecast_history | 14 |
| finance.test_budgets | 10 |
| finance.test_classification_feedback | 23 |
| **Tổng selection duy nhất** | **204** |

Kết quả: PostgreSQL **204/204 đạt**, SQLite **202 đạt và 2 skip**. Hai bài skip chính xác là `WalletConcurrencyTests.test_two_requests_same_receipt_create_one_transfer` và `WalletConcurrencyTests.test_two_distinct_intents_both_commit_without_lost_money`; cả hai chạy **đạt** trên PostgreSQL trong cùng selection. 50 nằm trong 204, 204 nằm trong 484; không cộng chúng hoặc cộng hai backend thành số bài duy nhất mới. Không chạy lại full suite. JavaScript không đổi trong lượt rà, dùng lại 44/44 đã chạy; collectstatic dùng lại bằng chứng đã có vì static không đổi. Check PostgreSQL QA đạt, makemigrations dry-run không thay đổi.

### Kiểm lại migration, khóa và reverse trên QA

Thư mục local ngoài Git riêng cho lượt rà: `D:\POSTGRESQL QA\task23a-final-review-20261103`. Dùng cluster PostgreSQL 18.6 **mới**, chỉ localhost:55432, guard kiểm cả data_directory/tên database; không dùng cluster có bản phục hồi dữ liệu cá nhân. Replay SQLite ở `migration-final.sqlite3` riêng, có guard đích. Không mở SQLite thật/Render. Fixture cũ vẫn là 19 model/9 giao dịch mô phỏng.

- **Forward:** replay SQLite trước/sau giữ hash `8d76edaac3be3534cac95995c968f59fa8186edba665d98cf44cc235ea299177`; PostgreSQL lượt rà giữ hash `c2b17516a70cb13762546c1153ed3d973b44294eb812fd8b359394d1c12e8e6e` (thời điểm load fixture mới). Kiểm tất cả trường cũ, không chỉ tổng tiền: FK mới NULL, không backfill Wallet/Transfer, không sinh income/feedback, coverage/liên kết không đổi; constraint PostgreSQL validated, SQLite integrity/FK đạt.
- **Khóa:** SQL forward có ALTER TABLE ba bảng cũ và CREATE INDEX thường, không CONCURRENTLY. Đo `pg_locks` trong transaction thấy **AccessExclusiveLock** trên Transaction, CsvImportBatch, RecurringRule. Một connection QA thứ hai SELECT Transaction bị `lock_timeout=200ms` trong kiểm có chủ đích. Đây là bằng chứng có thể chặn đọc/ghi khi triển khai, không phải sự cố production. FK nullable/no default không có câu UPDATE backfill trong SQL, nhưng vẫn cần khóa và tạo index quét dữ liệu; không gọi đây là migration zero-downtime.
- **Rollback DDL khi chưa commit:** thực hiện 0015 trong outer transaction QA, gây exception có chủ đích sau DDL rồi rollback. Hai bảng mới và bản ghi django_migrations 0015 đều không còn; 19 model cũ vẫn cùng hash. Điều này xác minh rollback trong transaction PostgreSQL ở kịch bản đã thử, **không** chứng minh phục hồi sau mất điện/kết nối hoặc crash mọi thời điểm.
- **Reverse sau commit khác rollback lỗi:** đã tạo 2 ví và 1 chuyển mô phỏng, reverse về 0014, rồi apply 0015 lại. Dữ liệu cũ vẫn nguyên; 2 ví/1 chuyển **mất**, apply lại không phục hồi được. Ba cột ví và liên kết mới cũng bị bỏ. Reverse được Django cho phép không có nghĩa an toàn dữ liệu. Chỉ thử trên QA, không dùng như cách rollback thường lệ.
- **SQLite:** nullable FK AddField không có default theo schema editor Django đang cài đi theo ADD COLUMN; thêm check trên bảng mới có thể remake bảng mới. RemoveField FK khi reverse có thể remake/copy bảng cũ. DDL/index vẫn cần khóa ghi/dung lượng; chưa đo thời gian chờ, journal/WAL và dung lượng trên database lớn. Không dùng kích thước fixture nhỏ để ước lượng thời gian production.

Bằng chứng: `migration-review.json`, `migration-forward.sql`, `migration-sqlite-final.json`, `postgres-test-selection.json`, `sqlite-test-selection.json`, `postgres-review.log`, `sqlite-review.log`. Chỉ báo cáo hash/schema/số lượng; không đưa fixture, log hoặc credential vào Git.

### Kế hoạch local và online — chưa thực hiện trên dữ liệu thật

| Giai đoạn | SQLite local | PostgreSQL/Render |
|---|---|---|
| Chuẩn bị | Xác minh đúng project/runtime/database, xin phép bước migration thật riêng. Dừng server và mọi luồng ghi, ghi mốc mã/schema. | Xác minh đích theo thông tin chủ dự án kiểm trên Dashboard; lập cửa sổ bảo trì/ngừng ghi. Chưa thay auto-deploy/quyền dịch vụ. Rolling deploy không được mặc định đồng nghĩa ngừng ghi. |
| Backup trước thay đổi | SQLite backup API vào thư mục timestamp mới ngoài repo; integrity_check, foreign_key_check, SHA-256 và manifest; giữ bản trước migration. | Script backup PostgreSQL hiện có, client chính thức tương thích, External URL nhập ẩn/TLS, không vào lệnh/log/Git. pg_dump custom, exit code, pg_restore --list, SHA/manifest. Archive đọc được chưa đủ; restore sang QA riêng và kiểm schema/migration/count/FK/sequence theo tài liệu TASK 16. |
| Migrate có kiểm soát | Sau backup đã kiểm và được cho phép: runtime local đúng cấu hình, xem plan rồi migrate/check; không chạy đồng thời nhiều tiến trình. | Build hiện chỉ collectstatic/check/model preflight; `scripts/render_start.py` mới chạy migrate dưới advisory lock, sau đó kiểm còn migration và dọn CSV hết hạn. Advisory lock chỉ ngăn nhiều startup migrate, **không thay maintenance hoặc ngăn request cũ**. Cần backup trước khi cho phép khởi động bản mới. Có kế hoạch timeout/hủy triển khai nếu không lấy được khóa; task chưa đổi cấu hình timeout production. |
| Xác minh sau migrate | Kiểm 0015 applied, lịch sử cũ NULL, ID/tiền/ngày/liên kết/coverage/tổng giữ nguyên. Không để dữ liệu QA. | Kiểm tương tự và smoke test bằng tài khoản thử riêng khi được cho phép. Không dùng health check/Live để suy mọi chức năng đạt. Giữ model/hash/config đúng môi trường. |
| Nếu DDL lỗi trước commit | Dừng, kiểm schema + django_migrations + integrity, không giả định mọi lỗi tự an toàn. Giữ backup và log đã che bí mật. | Kiểm transaction/schema/migration record; không retry vô hạn khi khóa bận. Rollback DDL đã thử QA không thay kiểm đích thực. Không fallback SQLite. |
| Nếu lỗi sau commit/đã có dữ liệu mới | Không reverse 0015. Có thể giữ schema mở rộng khi quay mã cũ **chỉ sau khi xác minh tương thích trên QA**; đóng ghi để tránh thêm dữ liệu không được UI cũ trình bày. | Cùng nguyên tắc. Nếu cần phục hồi đầy đủ: restore backup sang database mới, kiểm trên QA, thống kê phần ghi sau backup có nguy cơ mất; chỉ đổi đích thật theo kế hoạch được chấp thuận. Không restore đè production hoặc xóa từng phía chuyển. |

Kế hoạch trên được ghi ở mốc QA. Bước bàn giao tiếp theo đã thực hiện riêng phần backup/migrate SQLite local như dưới đây; phần online vẫn chỉ là kế hoạch. Chưa có SLA thời gian khóa, thử tải lớn hoặc bằng chứng UI mới; giữ nguyên toàn bộ trạng thái UI “Chưa xác minh” ở trên.

Rà cuối: `final-audit.json` xác nhận vẫn đúng 37 tệp TASK 23A; so với lần bàn giao trước chỉ `finance/test_wallets.py` và tài liệu này đổi. 204 ID được đối chiếu là tập con của 484; tám tệp bảo vệ và TASK 22C không đổi, không có bí mật theo mẫu/credential QA trong diff, index trống. Không phát hiện lỗi ứng dụng mới; điểm yếu kiểm thử rollback đã được khắc phục. Đã hủy session QA, dừng cluster lượt rà và xóa credential tạm; cổng 55432/8023 đóng, ghi trong `shutdown-report.json` tại thư mục lượt rà. Chưa stage/commit/push/deploy.

## Bàn giao migration 0015 trên local — 03/11/2026

Người dùng cho phép backup và migrate **SQLite local thật**, chỉ commit local; chưa push để tránh Render auto-deploy. Không sửa mã ứng dụng, kiểm thử, schema migration đã được rà hoặc tài liệu TASK 22C trong bước bàn giao này. Không chạy lại suite: dùng kết quả 484/204/50 và JavaScript đã ghi, không cộng trùng hoặc mô tả là lượt chạy mới.

### Backup nhất quán và đối chiếu

Thư mục riêng ngoài Git:
`D:\SAO LUU KHOA LUAN\task23a-local-handover-20261103-084229-528866`

| Mục | Kết quả thực tế |
|---|---|
| Nguồn | `D:\KHÓA LUẬN TỐT NGHIỆP\db.sqlite3`; `config.local`, không DATABASE_URL/Render |
| Runtime | `.venv\Scripts\python.exe`, Python 3.13.16 / Django 5.2.18, chế độ UTF-8 |
| Tệp backup | `before-migration-0015.sqlite3`, **430.080 byte** |
| Phương pháp | SQLite Connection.backup từ connection nguồn `mode=ro`; không copy tệp đang ghi hoặc sửa nguồn để tạo backup |
| SHA-256 backup | `1546fa278ffcb250b61ccfbe3bedfa1dc30691e14e56b68decee450ab682a89f` |
| Kiểm bản sao | integrity_check = ok; foreign_key_check không lỗi; hash kiểm lại sau migration vẫn khớp |
| Manifest/bằng chứng | `manifest.json`, `local-migration-verification.json`, `local-migration-check.log`; chỉ lưu ngoài Git, không chép bản ghi cá nhân vào tài liệu |

Không có server local lắng nghe ở các cổng đã kiểm trước bước này. Sau backup đạt, helper xác minh đúng engine/đường dẫn local, chỉ cho phép plan đúng 0015. Trong transaction ngoài cùng, lấy khóa ghi SQLite bằng UPDATE không đổi dữ liệu, đối chiếu lại snapshot trước DDL, rồi migrate. Nếu dữ liệu đã khác backup hoặc đối chiếu nghiệp vụ không khớp thì rollback, không tiếp tục ngầm.

Đối chiếu **27 bảng cũ**, gồm mọi dòng/trường và liên kết trước khi thêm ví; không chỉ đếm số lượng. Tổng income/expense tính bằng Decimal theo từng tài khoản/tháng được so sánh bằng fingerprint riêng. Tất cả dòng cũ giữ nguyên. Các FK ví mới đều NULL; Wallet = 0, WalletTransfer = 0. Không tạo tài khoản/giao dịch/coverage/feedback hoặc dữ liệu QA. Không đưa số tiền, tên hoặc mô tả cá nhân vào báo cáo Git.

**Metadata Django được phân biệt với dữ liệu nghiệp vụ:** post_migrate thêm đúng 2 django_content_type và 8 auth_permission cho Wallet/WalletTransfer; các dòng metadata cũ giữ nguyên. Đây không phải tự cấp quyền cho tài khoản hoặc tự thêm giao dịch.

Helper đối chiếu đã dừng hai lần: lần đầu do khác kiểu ngày/bool giữa connection Django và sqlite3; lần sau do so toàn bộ bảng metadata như bảng bất biến. Lần đầu chưa chạy DDL; lần sau transaction rollback. Đã kiểm nguồn trở lại trạng thái 0014, toàn bộ bảng cũ khớp backup và integrity/FK sạch trước khi tiếp tục. Đã tái hiện trên **bản sao QA riêng từ backup**, xác định chỉ có metadata đúng như trên, rồi chỉnh **helper ngoài repository** để so chính xác mọi dòng cũ và chỉ cho phép 2/8 metadata mới. Không thay mã ứng dụng/migration để bỏ kiểm dữ liệu, không ghi dữ liệu mô phỏng vào nguồn.

### Kết quả local sau commit transaction migration

- 0015 applied, **0 migration còn chờ**; system check không vấn đề; `makemigrations --check --dry-run`: No changes detected.
- integrity_check = ok, foreign_key_check không lỗi; toàn bộ dòng/liên kết nghiệp vụ cũ và tổng thu–chi theo tài khoản/tháng giữ nguyên, không có dữ liệu QA.
- SHA-256 SQLite local sau migration: `e78167559eac47f3636c98d4961396a2e9d1b6b411821d3c32566b778931b974`. File đổi do schema/metadata là dự kiến, không phải bằng chứng dữ liệu nghiệp vụ đổi.
- Model EN/VI, các module phân loại, requirements và tài liệu TASK 22C vẫn khớp hash trước task. Không cần suite mới vì mã đã kiểm giữ nguyên. Không có bằng chứng UI mới: **1280×900, 390×844 và trọn luồng tắt JavaScript vẫn Chưa xác minh** như mục trước.

### Runbook online cho lần được phép sau — chưa thực hiện

1. **Chốt backup mới trước push/deploy.** Chủ dự án kiểm đúng service/database/version trên Dashboard, kiểm lịch hết hạn gói Free theo trạng thái hiện tại, chọn cửa sổ bảo trì và cách ngừng ghi. Không dùng archive 23/10 như backup mới cho lần này. Xem [quy trình backup](production-verification.md). Lệnh dưới là hướng dẫn, **chưa chạy**; kiểm lại đường dẫn PowerShell/client khi đến lúc thực hiện:

   ```powershell
   & 'C:\Users\namt2\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe' -NoProfile -File 'D:\KHÓA LUẬN TỐT NGHIỆP\scripts\backup_postgresql.ps1' `
     -PgBin 'C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-client\bin' `
     -Backup -ServerMajor 18 `
     -BackupRoot 'D:\SAO LUU KHOA LUAN\postgresql'
   if ($LASTEXITCODE -ne 0) { throw 'Backup chưa hoàn tất; chưa triển khai.' }
   ```

   Chỉ nhập External Database URL ở prompt ẩn; không gửi chat hoặc đặt URL vào command/history/file Git. Server major phải được kiểm lại trước khi dùng 18. TLS theo script hiện có; không hạ bảo vệ. Cần exit 0, manifest/hash mới, pg_restore --list và decode đạt, không còn partial/passfile tạm. Kết quả này chỉ chứng minh archive đọc được.

2. **Kiểm khả năng khôi phục.** Theo [chuẩn bị restore](postgresql-restore-preparation.md) và [diễn tập đã thực hiện](postgresql-restore-rehearsal.md), restore archive **mới** vào database/cluster QA mới cùng major, localhost riêng; kiểm danh tính đích trước restore, single transaction/exit-on-error, schema/migration/FK/count/sequence và smoke test ứng dụng bằng tài khoản QA. Không restore đè cluster cũ hoặc production; giữ log riêng tư ngoài Git, dừng QA/dọn credential. Diễn tập cũ không chứng minh mọi archive mới đã restore được.

3. **Bảo trì/migrate.** DDL 0015 từng giữ AccessExclusiveLock và chặn SELECT trong QA; chưa có ước lượng thời gian trên kích thước online. Dừng/giới hạn ghi theo kế hoạch vận hành được chủ dự án duyệt, thông báo khả năng gián đoạn đọc; không hứa zero-downtime. Build không migrate; `render_start.py` dùng advisory lock rồi migrate/check/cleanup CSV trước khi serve. Lock này không ngừng request bản cũ. Giữ backup, mốc code và cấu hình trước khi cho phép push/auto-deploy. Không tạo worker migration song song hoặc retry vô hạn.

4. **Xác minh sau deploy.** Kiểm log 0015 OK, không còn unapplied và system check/preflight đạt; khi có phương tiện quản trị được cho phép, kiểm django_migrations/schema thực và các dòng cũ/tổng trước–sau. Sau đó dùng tài khoản thử riêng: mở lịch sử chưa xác định, tạo hai ví mốc rõ → thu/chi → chuyển nội bộ → gửi lại cùng thao tác → kiểm hai số dư/tổng và thu–chi không bị cộng chuyển; kiểm ví lưu trữ, giao dịch tương lai, CSV/định kỳ chọn ví và coverage/dự báo theo checklist hiện có. Không dùng dữ liệu QA để xác nhận số dư tài khoản thật; không mặc định Deploy Live là mọi chức năng đạt. Không tự tạo dữ liệu online trong bước hiện tại.

5. **Rollback mã khác rollback dữ liệu.** Nếu migration chưa commit và gặp lỗi, kiểm transaction/schema/record, không suy mọi tình huống crash đều tự khôi phục. Sau khi 0015 commit, ưu tiên giữ schema và dừng ghi khi điều tra. Chỉ quay mã cũ khi đã kiểm tương thích QA; UI cũ không trình bày được ví/chuyển mới, không có nghĩa dữ liệu biến mất. **Không reverse 0015 như cách rollback an toàn**: đã chứng minh mất ví/chuyển và liên kết mới. Nếu cần quay dữ liệu, restore backup sang đích mới, kiểm và lập kế hoạch phần ghi sau backup có thể mất trước khi xin phép chuyển đích; không âm thầm phục hồi đè production.

Bước bàn giao này chỉ commit local đúng 37 tệp TASK 23A; không đưa backup, helper/cấu hình QA, credential hoặc tài liệu TASK 22C vào commit. SHA commit và đối chiếu remote được ghi ở biên nhận ngoài repository/tin nhắn bàn giao; remote chưa có commit mới là dự kiến vì **không push**.

## Bổ sung kiểm thủ công demo ví — 03/11/2026

**Nguồn bằng chứng:** người dùng xác nhận kết quả kiểm thủ công qua ảnh trên server QA `127.0.0.1:8023`, database mới hoàn toàn mô phỏng. Đây không phải kiểm thử tự động hoặc xác minh online. Các thao tác thực tế dưới đây thay cho kịch bản dự kiến đã hướng dẫn trước đó; không ghi kịch bản chưa thực hiện là đạt.

| Bước thực tế | Ngân hàng | Tiền mặt | Tổng hai ví |
|---|---:|---:|---:|
| Mốc ban đầu | 2.000.000 VND | 1.000.000 VND | 3.000.000 VND |
| Chuyển Ngân hàng → Tiền mặt 100.000 VND | 1.900.000 VND | 1.100.000 VND | 3.000.000 VND |
| Chuyển Ngân hàng → Tiền mặt 10.000 VND | 1.890.000 VND | 1.110.000 VND | 3.000.000 VND |
| Chuyển Ngân hàng → Tiền mặt 20.000 VND | 1.870.000 VND | 1.130.000 VND | 3.000.000 VND |
| Chi từ Tiền mặt 30.000 VND | **1.870.000 VND** | **1.100.000 VND** | **2.970.000 VND** |

Người dùng xác nhận qua ảnh số dư ban đầu/cuối và **Tổng quan tháng 11/2026: thu 0 VND, chi 30.000 VND**. Các dòng số dư trung gian trong bảng là đối chiếu số học từ chuỗi thao tác được cung cấp, không khẳng định có ảnh riêng của từng mốc. Tổng chuyển nội bộ 130.000 VND không làm tăng thu/chi; mốc ban đầu không tính thành thu nhập. Tổng tài sản theo ghi chép giảm đúng khoản chi 30.000 VND. Không coi đây là số dư ngân hàng được đối soát.

Giữ nguyên các giới hạn UI đã công bố: **chưa xác minh đúng viewport 1280×900/390×844, trọn luồng tắt JavaScript, toàn bộ focus/Tab/phân trang, thiết bị vật lý hoặc trình duyệt khác**. Xác nhận qua ảnh/thao tác này chỉ bổ sung bằng chứng cho luồng ví/chuyển/chi và số liệu nêu trên; không nâng thành “toàn bộ UI đạt”. Không thêm ảnh, dữ liệu hoặc credential vào Git.

Đã dừng đúng server demo 8023, kiểm socket xác nhận cổng đóng; hủy toàn bộ session trong database demo (còn 0), vô hiệu mật khẩu tài khoản QA và xóa tệp credential mã hóa/khóa server tạm. Database mô phỏng được giữ ngoài Git tại `D:\POSTGRESQL QA\wallet-manual-20261103-090726-806960\demo.sqlite3`; biên nhận dọn QA là `manual-check-shutdown.json` cùng thư mục, chỉ là tham chiếu local. Không mở SQLite thật hoặc truy cập production trong lần cập nhật này.

Chỉ sửa tài liệu này; giữ nguyên mã và TASK 22C. Không chạy lại suite vì mã không đổi; chưa stage/commit/push/deploy bản bổ sung kiểm thủ công này.

## Backup PostgreSQL và diễn tập 0015 từ snapshot thật — 04/11/2026

### Xác minh đích và phạm vi quyền

Người dùng xác nhận trực tiếp Dashboard: repository `thiennamm/khoa_luan_tai_chinh_ca_nhan`, branch main, **Auto-Deploy On Commit**, Build `bash deploy/render-build.sh`, Start `bash deploy/render-start.sh`, commit Live `1da8898` tại lúc kiểm. Database hiển thị `so-thu-chi-db`, PostgreSQL major 18, Available, Singapore, External Access `0.0.0.0/0`; không thay cấu hình/allowlist.

Đối chiếu **riêng trên máy** bằng 3 lời nhắc ẩn: DATABASE_URL Web Service, Internal URL và External URL do người dùng sao chép từ cùng database trên Dashboard. Host/cổng/tên database của Web Service khớp URL **Internal**. Không in/lưu URL, username hoặc mật khẩu trong biên nhận; bản so sánh không kết nối database và không dùng việc giống tên hiển thị làm bằng chứng cùng đích. Sau đó người dùng nhập External URL lại tại prompt ẩn của script backup.

Production chỉ được `SHOW server_version_num` và pg_dump qua process con với `PGOPTIONS=-c default_transaction_read_only=on`, TLS require, theo `scripts/backup_postgresql.ps1` hiện có. Không migrate/restore/SQL sửa schema hoặc dữ liệu production; không đọc `.env`, không dùng SQLite local làm nguồn hoặc đích. Không push/deploy. Không ghi lại bằng chứng có URL hoặc bản ghi tài chính vào Git.

### Backup mới đã kiểm

| Mục | Kết quả |
|---|---|
| Thư mục ngoài Git | `D:\SAO LUU KHOA LUAN\postgresql\postgres-20261104T030444734Z-2a5a0dd4` |
| Archive | `postgres-20261104T030444734Z-2a5a0dd4.dump` — **109.126 byte**, PostgreSQL custom |
| SHA-256 | `5f666910a5f94702927491851571d95aef4fafebd6832f25ebdb77a03f64d4a4` |
| Runtime nguồn | server_version_num **180006** (18.6); client pg_dump/pg_restore/psql 18.6 |
| Thời gian chạy pg_dump/kiểm archive theo manifest, giờ VN | **10:04:45,988 – 10:04:50,994 ngày 04/11/2026** |
| Kiểm archive | exit 0, pg_restore --list và giải mã vào NUL đạt, kích thước/hash khớp manifest; không còn .partial/.pgpass.tmp |
| Sau diễn tập | Archive/hash và manifest gốc được giữ nguyên; không sửa manifest backup để tự ghi restore đạt |

### Restore và đối chiếu với nguồn tại mốc backup

Cluster **mới**, không ghi đè bản TASK16: `D:\POSTGRESQL QA\wallet0015-restore-20261104-abc6454e\data`. PostgreSQL 18.6 portable, không Windows service, chỉ `127.0.0.1:55432`, database mới **qa_wallet0015_restore**. Trước restore đã kiểm data_directory, database, host/port, role, version, listen_addresses và không có bảng người dùng. Không nhận URL làm đích restore. Role restore là owner QA, không superuser/CREATEDB/CREATEROLE; có **pg_read_all_settings chỉ trong QA** để guard kiểm data_directory. Mật khẩu QA ngẫu nhiên, tách khỏi production.

Restore dùng `--no-owner --no-privileges --exit-on-error --single-transaction`, **exit 0**. Không --clean, --create, bỏ constraint/trigger hoặc chọn lọc bỏ dữ liệu lỗi.

Mốc nguồn đối chiếu là **snapshot pg_dump trong archive**, không phải phép đếm production ở thời điểm muộn hơn. Đọc COPY của archive trong bộ nhớ, đối chiếu **28/28 bảng public** với bản restore: số hàng và fingerprint mọi cột/giá trị khớp, gồm các ID/FK liên kết. Chuẩn hóa biểu diễn datetime về UTC, numeric bằng Decimal và JSON theo cấu trúc để tránh khác định dạng hiển thị. Tổng income/expense theo từng tài khoản/tháng có fingerprint khớp; không in số tiền/tên/mô tả cá nhân trong báo cáo Git. Không khẳng định website hiện tại vẫn bằng snapshot nếu có thao tác mới sau backup.

### Migration trên QA vừa restore

Plan QA chỉ còn đúng 0015; đã migrate, system check không vấn đề, `migrate --check` đạt và `makemigrations --check --dry-run` báo No changes detected. Sau migration:

- Fingerprint mọi trường cũ ở **27 bảng ngoài django_migrations** giữ nguyên; với content type/permission chỉ so các dòng cũ và kiểm riêng phần thêm đúng **2 content type + 8 permission** cho hai model ví. Danh sách app/name trong django_migrations giữ bản cũ và thêm đúng 0015; không dùng hash toàn bảng để bỏ qua metadata thêm hợp lệ.
- Tổng thu–chi Decimal theo tài khoản/tháng và các liên kết nghiệp vụ giữ nguyên. Transaction, CsvImportBatch, RecurringRule cũ đều có wallet_id NULL — **Chưa xác định ví**. Wallet = 0, WalletTransfer = 0; không tạo income, feedback, coverage, tài khoản hoặc giao dịch QA giả.
- **0 migration còn chờ.** Không sửa application code, model ML, dependency hoặc migration để ép kết quả đạt.

| Kiểm database | Trước 0015 | Sau 0015 |
|---|---:|---:|
| FK được quét | 40 | 47 |
| Hàng mồ côi | 0 | 0 |
| CHECK được đánh giá | 29 | 33 |
| Index invalid / constraint chưa validated / trigger bị disable | 0 / 0 / 0 | 0 / 0 / 0 |
| Sequence có ứng viên ID kế tiếp an toàn | 22 | 24 |
| Sai chủ/loại ở các liên kết giao dịch–danh mục, ngân sách, định kỳ; tiền giao dịch lẻ VND | 0 | 0 |

Sequence được kiểm bằng last_value/is_called/increment/MAX ID, **không gọi nextval hoặc sửa sequence**. Có kiểm dữ liệu thực đã restore; không suy thành kiểm toàn bộ hành vi ứng dụng, UI, concurrency hoặc tải lớn.

### Lỗi helper, bằng chứng và dọn môi trường

Lượt helper đầu dừng ở archive-parse, **trước initdb/restore**: pg_restore.exe xuất CRLF, bộ đọc COPY ngoài repository ban đầu chỉ xử lý LF. Đã giữ biên nhận thất bại, sửa helper để bỏ CR ở cuối dòng vật lý (không tách nhầm Unicode U+2028 hay sửa nội dung ô), chạy **11 assertion tổng hợp của helper** đạt, rồi restore/migrate QA đạt. Đây không phải lỗi dữ liệu/model/ứng dụng hoặc sự cố production. Không chạy lại suite 484/204/50 hay JavaScript; 11 assertion này không cộng vào số bài ứng dụng đã công bố.

Thư mục bằng chứng riêng ngoài Git: `D:\SAO LUU KHOA LUAN\wallet0015-rehearsal-20261104-abc6454e`, gồm `database-target-comparison.json`, `dashboard-confirmation.json` (chỉ dữ kiện không bí mật/fingerprint đích), `backup-result.json`, `attempt1-rehearsal-result.json`, `rehearsal-result.json`, `migration-QA-check.log` và helper. Native log có thể chứa SQL/dữ liệu riêng chỉ ở vùng QA ACL riêng, **không đưa vào Git/chat**. Đây là tham chiếu local, không phải link artifact công khai trên GitHub.

Đã đóng kết nối/process nguồn sau backup và cửa sổ nhập URL. Đã đóng mọi connection QA, dừng đúng cluster, xác nhận cổng 55432 đóng, xóa passfile/init-password QA; không lưu mật khẩu QA dài hạn. Clipboard hiện tại đã xóa; nếu người dùng bật Win+V/Cloud Clipboard, cần tự xóa các mục URL còn trong lịch sử đó. Cluster đã dừng và backup gốc được giữ nguyên, không phục hồi đè SQLite local/production. Model, requirements và tài liệu TASK 22C vẫn khớp hash bảo vệ.

### Phương án khôi phục và giới hạn trước deploy

Archive này khôi phục dữ liệu theo snapshot nội bộ của pg_dump trong khoảng chạy ở trên, **không phải trạng thái tại lúc kết thúc hoặc hiện tại**. Các giao dịch/sửa/xóa và thay đổi tài khoản sau snapshot có thể mất nếu quay về backup. Trước triển khai thực tế cần backup mới nếu đã có ghi thêm, chốt khoảng ngừng ghi và cách bảo toàn/đối chiếu các thay đổi sau mốc backup; không hứa khôi phục không mất dữ liệu.

Nếu cần phục hồi, restore archive đã kiểm vào **database mới riêng**, xác minh hash/schema/count/FK/sequence và đối chiếu ứng dụng rồi mới lập bước chuyển đích được phép. Rollback mã không tự rollback database. **Không reverse 0015 để phục hồi dữ liệu ví/chuyển**: reverse sẽ bỏ bảng/cột mới và không khôi phục các khoản đã phát sinh. Không phục hồi đè production trong diễn tập.

Đã đạt: backup thật chỉ đọc, archive/hash, restore QA và đối chiếu snapshot, migration 0015/checks QA, dừng/dọn credential. **Chưa thực hiện**: push/deploy/migrate production, smoke test online hoặc UI mới, thử tải lớn và diễn tập hỏng ổ/mất điện/PITR. Quyền DDL cụ thể của role DATABASE_URL production và thời gian khóa trên workload online chưa được kiểm bằng migration thật. QA Windows/locale C khác Linux/Render; kết quả không thay toàn bộ kiểm online. Các giới hạn viewport/tắt JavaScript đã công bố vẫn giữ “Chưa xác minh”. Lượt này chỉ cập nhật tài liệu, chưa stage/commit/push; giữ TASK 22C ngoài phạm vi.
