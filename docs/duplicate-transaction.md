# TASK 20A — Tạo giao dịch tương tự

Thực hiện trên dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`, ngày **27/10/2026**, giờ Việt Nam. Không có AGENTS.md trong repository. Đã đọc luồng ModelForm/Transaction.save, ML/Apply/feedback, CSV, định kỳ, coverage và forecast version trước khi sửa. Không đổi dependency, model ML, hash artifact, chính sách CSV/ngày của CRUD hoặc thuật toán dự báo. Giai đoạn QA chưa commit/push/deploy; kết quả bàn giao local và chốt mã theo yêu cầu tiếp theo ở **mục 9**.

## 1. Cách dùng

1. Mở chi tiết một giao dịch của mình, bấm nút phụ **Tạo giao dịch tương tự**, phân biệt với **Sửa giao dịch**.
2. Form có tiêu đề riêng và thông báo: **Đã điền từ giao dịch trước. Chưa tạo giao dịch mới.** Điền trước mô tả, loại, số tiền Decimal và danh mục còn thuộc tài khoản/đúng loại.
3. Ngày mặc định là **hôm nay theo Asia/Ho_Chi_Minh**, không lấy ngày nguồn, không phụ thuộc múi giờ được activate khác. Người dùng sửa mọi trường theo validation giao dịch hiện có; không thêm quy tắc chặn ngày tương lai cho CRUD/CSV.
4. Danh mục nguồn không hợp lệ: để trống và yêu cầu chọn lại, không chọn thay. Nếu danh mục bị đổi/xóa sau khi mở, server kiểm lại khi lưu.
5. Tự bấm **Lưu giao dịch** mới tạo giao dịch mới. Form lỗi giữ dữ liệu vừa nhập và mã thao tác; hiển thị tóm tắt lỗi như form thường.

Nhập nhanh vẫn phải xác nhận thay thế dữ liệu có sẵn; hủy thay thế giữ form. Thay thế thật dùng các sự kiện hiện có để vô hiệu receipt ML cũ, không thay mã thao tác tạo giao dịch tương tự. Gợi ý ML vẫn là tùy chọn thử nghiệm; phải yêu cầu gợi ý mới, chủ động Apply và tự Save. Khi tắt JavaScript, form điền trước/lưu thủ công vẫn dùng được, nhập nhanh/ML cần JavaScript như trước.

## 2. Kiến trúc và giới hạn nguồn

| Đường dẫn | Hành vi |
|---|---|
| GET `/giao-dich/<id>/tao-tuong-tu/` | Đăng nhập và kiểm chủ nguồn bằng server; dựng `initial` từ danh sách 5 trường cho phép, ký nonce mới; không ghi bản ghi chờ, giao dịch, ML hoặc trạng thái tài chính |
| POST `/giao-dich/tao-tuong-tu/luu/` | Đăng nhập + CSRF; bắt buộc có mã hợp lệ, dùng lại `transaction_edit`, `TransactionForm` qua subclass có một trường ẩn và `classification_feedback.save_with_feedback` hiện có |

Không POST tới URL nguồn, không nhận source ID làm đích lưu. POST không truy vấn lại nguồn: nguồn bị sửa/xóa không tự thay dữ liệu đã chỉnh trên form. Giao dịch mới không có ID của nguồn, không copy thời điểm, liên kết định kỳ, CSV receipt, gợi ý/Apply/feedback hoặc operation cũ. Schema Transaction hiện không có FK lô CSV; chức năng này không tạo hay sửa batch/receipt CSV.

`source_transaction_id` của khung ML để rỗng trong form tương tự, đúng **ngữ cảnh tạo mới**, không phải ngữ cảnh sửa nguồn. Receipt ML cũ gắn nguồn bị backend từ chối. Receipt mới qua endpoint hiện có, giữ kiểm đầu vào/mode/thời hạn/quyền/Transfer. Nếu receipt đã được dùng bởi một form khác, không gắn giao dịch đã có vào operation mới. Không sao chép mô tả vào bảng receipt mới, không thêm log payload và không tự suy luận/huấn luyện.

## 3. Chống gửi lặp và transaction

Không thể chỉ khóa nút hoặc dùng session để bảo đảm hai request đồng thời. Luồng nhập tay trước đây chỉ có idempotency khi dùng receipt ML; tái sử dụng bảng ML hoặc receipt tiết kiệm cho một giao dịch nhập tay sẽ sai ý nghĩa. Vì vậy thêm bảng tối thiểu **SimilarTransactionOperation**, không thay schema Transaction:

| Trường | Nội dung |
|---|---|
| `id` | UUID primary key, lấy từ claim đã ký phía server |
| `user` | FK tài khoản, CASCADE khi tài khoản được xóa theo chính sách hiện có |
| `digest` | HMAC-SHA256 của dữ liệu đã validation: kind, Decimal amount, date, category ID, description và receipt/mode ML mới nếu có; không lưu bản sao mô tả |
| `created_at` | Thời điểm ghi nhận operation thành công |
| `saved_transaction` | OneToOne nullable tới giao dịch mới; SET_NULL khi giao dịch bị xóa |

GET chỉ ký nonce ngẫu nhiên gồm UUID/user/purpose bằng Django signing; thời hạn **7.200 giây (2 giờ)**, không có ID nguồn, không tái dùng mã của nguồn. Hai lần mở tạo hai nonce khác nhau. Thiếu/sửa mã, hết hạn, sai purpose hoặc thuộc tài khoản khác đều bị từ chối. Mã chỉ chống trùng cho luồng tương tự, không thay chính sách idempotency của form thêm thông thường/CSV/định kỳ.

Trong `transaction.atomic`: INSERT operation là câu SQL đầu tiên; PK unique chặn cùng nonce, dùng savepoint để xử lý xung đột. PostgreSQL chờ transaction cùng nonce kết thúc rồi đọc receipt đã commit. Cùng nonce và cùng digest trả giao dịch đã lưu, không ghi thêm và không chạy lại hook coverage. Cùng nonce khác payload bị từ chối; không ngầm sửa giao dịch trước. Khác nonce cho phép cùng ngày/tiền/mô tả, vì có thể là hai khoản thật.

Sau claim mới, đường thủ công đọc lại/khóa category của chính tài khoản và đúng loại; đường có ML giữ thứ tự claim receipt → khóa category của dịch vụ hiện có. Sau đó lưu bằng dịch vụ/form/model cũ, gắn operation với giao dịch mới. Lỗi bất kỳ rollback operation, giao dịch và các hook/feedback trong cùng transaction. Không tự retry POST sau lỗi mạng.

Nếu giao dịch kết quả bị xóa, giữ operation với FK null để mã cũ không tự tạo lại khoản đã xóa; yêu cầu mở form mới nếu người dùng thật sự muốn tạo khoản khác. Receipt hết hạn cũng không tái dùng để tạo mới. Không có tác vụ tự xóa receipt trong phiên bản này. Chính sách account có Transaction bị PROTECT giữ nguyên: dọn giao dịch qua luồng được phép trước khi xóa tài khoản; khi tài khoản được xóa, operation CASCADE, không giữ dữ liệu cá nhân mồ côi.

## 4. Ảnh hưởng tài chính

GET/nhập nhanh không cập nhật coverage, ngân sách, forecast version hoặc lịch sử dự báo. Lưu thành công gọi đúng `Transaction.save`/hook cũ, hủy xác nhận **tháng của ngày giao dịch mới**, cập nhật version và tổng chi/ngân sách từ Transaction thực tế. Không dùng tháng/ngày nguồn để xác định tháng ghi nhận. Operation/ML feedback rollback cùng Transaction khi lỗi. Không thay nguồn hoặc snapshot dự kiến của kỳ định kỳ.

Không đổi cơ chế fingerprint dự báo. Cơ chế hiện tại có hash mã `models.py` trong cấu hình: triển khai thay đổi mã này có thể làm kết quả hiện hành cũ bị coi lỗi thời như các lần đổi phiên bản trước; không có thao tác tự tính lại hoặc ghi đè lịch sử. Đây khác với việc mở form gây thay đổi dữ liệu, vốn được kiểm là không xảy ra.

## 5. Migration và triển khai

**`finance/migrations/0014_similar_transaction_operation.py`** chỉ CreateModel: UUID PK, user FK, FK kết quả nullable/unique và trường digest/thời điểm. Phụ thuộc 0013 và User swappable. Không có RunPython, không đọc/backfill/sửa giao dịch hay bảng cũ; bảng mới ban đầu trống. Không cần cài extension.

Đã áp dụng lên SQLite QA riêng và **PostgreSQL 18.6 QA thật** trên localhost:55432. Kiểm schema thực tế: UUID, PK, UNIQUE và **hai FK đều validated**; database ứng dụng PostgreSQL QA vẫn trống, suite dùng database test riêng đã xóa sau chạy. Không chỉ compile SQL offline. `makemigrations --check --dry-run`: **No changes detected**; `migrate --check` trên SQLite QA không còn migration chờ, system check **0 issues**.

**Tại thời điểm kết thúc QA, chưa migrate SQLite thật hoặc Render; bàn giao local sau đó ở mục 9.** Để triển khai trên database khác sau khi được duyệt:

1. Sao lưu đúng loại DB theo quy trình đã có (SQLite backup API ở local; pg_dump cho PostgreSQL), kiểm bản sao; không copy nóng SQLite.
2. Dùng đúng Python/cấu hình của môi trường đích, kiểm DB đích trước khi `migrate --noinput`; trên Render dùng bước migrate/start đã thiết kế trong [render-deployment.md](render-deployment.md).
3. Kiểm migration 0014, system check; thử bằng tài khoản QA mới, không dùng tài khoản thật. Không seed tài khoản hoặc giao dịch.
4. Không mở chức năng mới trên SQLite thật chưa có bảng 0014. Không xóa bảng receipt như cách xử lý lỗi gửi lặp; có thể làm mất dấu chống trùng.

## 6. Kiểm thử tự động

| Lượt cuối | Kết quả | Bằng chứng ngoài Git |
|---|---|---|
| Nhóm TASK 20A trên SQLite bộ nhớ test | **21/21 đạt** | `sqlite-related.log` |
| Toàn bộ suite trên PostgreSQL QA | **416/416 đạt**, 160,889 giây, **không skip** | `postgresql-full-final.log` |
| JavaScript hồi quy | **43/43 đạt**, không sửa JS | `javascript.log` |
| Production QA collectstatic | **10 copied, 20 postprocessed**, manifest/URL hash/gzip CSS/JS/icon đúng, system check đạt | `handoff-static-report.json`, `collectstatic-run.log` |

21 bài mới đã nằm trong 416 PostgreSQL; 21 SQLite là lượt bổ sung cùng nhóm, không cộng trùng. Kiểm các nhóm: prefill/Decimal/ranh giới UTC→Việt Nam; GET không ghi toàn bộ bảng finance; nguồn khác tài khoản/CSRF/method; nguồn đổi/xóa; category sai hoặc đổi giữa validation/save; giữ input lỗi; token thiếu/giả/hết hạn/khác tài khoản; POST lặp/đổi payload/xóa kết quả; hai nonce riêng; không sao chép định kỳ/CSV/ML; receipt ML mới Apply/Save; receipt cũ sai ngữ cảnh/đầu vào; thiếu model vẫn nhập tay; coverage/budget/forecast chỉ đổi sau lưu; rollback và chính sách xóa.

**Ba ca đồng thời đã chạy thật trên PostgreSQL:**

1. Cùng nonce/cùng dữ liệu: cả hai request được xử lý, cùng transaction ID, một lần tạo và một lần replay; đúng 1 operation/1 Transaction.
2. Hai nonce/cùng dữ liệu: cả hai thành công, đúng 2 operation/2 Transaction.
3. Cùng nonce/khác dữ liệu: một thành công, một conflict; chỉ 1 operation/1 Transaction.

SQLite không có row lock `select_for_update`; có thể báo database locked khi chạy thread trên memory/shared cache. Test harness cho phép kiểm lại một request bị khóa ở SQLite, **ứng dụng không tự retry**. PostgreSQL assertions nghiêm ngặt không chấp nhận kết quả locked hoặc lỗi DB. Chưa kiểm tải lớn/nhiều worker, xung đột với mọi loại cập nhật khác hoặc lỗi mạng thực.

Lượt toàn suite đầu có lỗi subprocess giải mã thông báo tiếng Việt bằng cp1258 của Windows (**30 error subcase, 1 failure**). Chạy lại với `PYTHONUTF8=1`/`-X utf8` đạt toàn bộ; không đổi mã ứng dụng/validator hoặc bỏ qua bài. Các fixture mới ban đầu xác nhận nhầm tháng hiện tại và kỳ vọng xóa account vượt PROTECT đã được sửa cho đúng chính sách hiện có; không đổi nghiệp vụ để làm test đạt.

## 7. QA giao diện và bằng chứng

Thư mục riêng **`D:\POSTGRESQL QA\task20a-20261027`**. SQLite mới `qa.sqlite3`, cổng **8021**; hai tài khoản ngẫu nhiên, có banner **QA 20A — SQLite riêng — Dữ liệu mô phỏng**. Không copy SQLite thật. Edge Chromium headless, desktop **1280×900**, mobile **390×844**, reduced motion; không gọi HTTP 200 là thử UI.

Đã điều khiển UI: nút trên chi tiết → form có prefill/ngày hôm nay/receipt rỗng; danh mục đúng; tài khoản B mở nguồn A nhận 404; không tràn ngang mobile; Nhập nhanh yêu cầu xác nhận thay thế và Cancel giữ dữ liệu. Kiểm DB sau GET/parser preview: vẫn 2 giao dịch fixture, 0 operation/0 feedback/0 suggestion và coverage không đổi.

Sau đó thử lỗi tiền thật `50,00`: dữ liệu/mã được giữ, tóm tắt lỗi nhận focus. Nhập nhanh thay thế chủ động làm mất gợi ý ML cũ nhưng giữ operation. VI suy luận thật → Apply → Save tạo giao dịch mới/phản hồi mới. Hai DOM `button.click()` liên tiếp qua submit thật tạo **1 POST**; gửi lại cùng body qua HTTP nhận đúng URL đã lưu. Hai lần chủ động mở form riêng cùng dữ liệu đều được chấp nhận. Đây không phải thử ngón tay trên điện thoại vật lý.

Mobile **tắt JavaScript**, mở form trước rồi xóa nguồn bằng một thao tác xóa QA riêng ở phiên khác: vẫn lưu được ngày/tiền/mô tả đã chỉnh, không nối kỳ/không phát sinh feedback. Xóa nguồn là hành động cố ý của ca kiểm thử, **không phải tác dụng phụ của Tạo giao dịch tương tự**. Một harness ban đầu chờ sai query string sau redirect xóa; đã sửa kỳ vọng đường dẫn và hoàn thành ca sau bằng fixture riêng, không gửi lại giao dịch ML đã commit.

DB cuối: A có 3 giao dịch, B có 1; 4 operation (1 có FK null vì kết quả bị xóa có chủ đích); 1 feedback VI Apply/cùng nhãn từ gợi ý mới, không feedback cho lưu thủ công; không thêm batch/receipt CSV; kỳ nguồn chuyển deleted đúng thao tác xóa riêng, không liên kết giao dịch mới. SQLite integrity_check=ok, foreign_key_check không lỗi. Ví dụ ML QA không dùng để đánh giá chất lượng mô hình.

Ảnh đã xem trực quan, nằm **ngoài Git**:

- `desktop-similar-form.png`, `mobile-similar-form.png`: prefill trước lưu.
- `desktop-validation-error.png`: lỗi backend giữ input/focus.
- `mobile-applied-before-save.png`: đã Apply nhưng chưa lưu; lỗi server cũ có thể vẫn hiển thị đến lần submit tiếp theo như form hiện có.
- `mobile-no-javascript.png`: form không JS, ngày/tiền đã chỉnh.
- `mobile-feedback.png`: phản hồi mới của tài khoản QA.

Bằng chứng: `ui-get-checks.json`, `ui-get-db-verification.json`, `ui-save-checks.json`, `ui-created.json`, `final-verification.json`, `database-identity.json`, `postgresql-schema-check.json`, các log kiểm thử/static, manifest/hash trong thư mục QA. PostgreSQL dùng cluster TASK 16 `D:\POSTGRESQL QA\rehearsal-20261023\data-attempt2`, system identifier `7699798773140758112`, chỉ nghe **127.0.0.1:55432**; database ứng dụng mới `qa_task20a_20261027`, test `qa_task20a_suite`. Kiểm identity trước kết nối; không dùng database đã phục hồi hoặc URL production.

Đã dừng website QA **8021** và PostgreSQL **55432**, xác minh hai cổng đóng và `postmaster.pid` không còn. Đã xóa file credential, hai session trình duyệt và secret SQLite QA tạm; quét tệp text còn lại không thấy các bí mật tạm đó. Giữ database/bằng chứng mô phỏng riêng ngoài Git. `shutdown-report.json` ghi kết quả dọn, `evidence-manifest.json` ghi kích thước/SHA-256 của bằng chứng được chọn, không gồm credential.

Chưa kiểm trình duyệt khác, thiết bị vật lý, screen reader/WCAG toàn diện, Linux/Render hoặc UI online. Các kết quả UI ở trên chỉ dùng database QA; khi kết thúc giai đoạn đó chưa migrate local thật hoặc commit/push. Bàn giao local sau đó không thử ghi giao dịch thật (mục 9).

## 8. Tệp thay đổi

- `finance/models.py`, migration 0014: receipt chống trùng tối thiểu.
- `finance/similar_transactions.py`: initial, ký/kiểm nonce, digest, claim/replay và gọi dịch vụ lưu cũ.
- `finance/forms.py`, `views.py`, `urls.py`: subclass hidden field, tái sử dụng luồng thêm và hai endpoint có phương thức rõ ràng.
- `templates/finance/transaction_detail.html`, `transaction_form.html`: nút phụ, tiêu đề/notice, action POST mới và hidden fields; không sửa JavaScript.
- `finance/test_similar_transactions.py`, README và tài liệu này.

Rà diff chỉ gồm mã, migration, kiểm thử và tài liệu; không thêm credential/config/ảnh/database QA. Đối chiếu SHA-256 SQLite thật, hai artifact EN/VI và hai requirements giữ nguyên; không đưa dữ liệu thử lên Git.

## 9. Bàn giao local và chốt mã — 27/10/2026

Theo yêu cầu tiếp theo của người dùng, rà lại migration 0014 và receipt, không cần sửa mã thực thi. Nonce được ký bằng salt riêng, bắt buộc đúng user và action `similar_create`, có thời hạn; claim UUID unique trong transaction, đọc replay giới hạn tài khoản và digest, kiểm chủ giao dịch kết quả. GET mint nonce mới, không lấy receipt nguồn. Receipt ML phải thuộc ngữ cảnh tạo mới và còn hợp lệ; receipt đã tạo giao dịch ở form khác không được gắn vào operation mới. PK/UNIQUE/FK đã kiểm thực tế trên PostgreSQL QA; ba ca đồng thời và giới hạn SQLite giữ như mục 6.

### Backup và migration local

- Bản sao mới, không ghi đè bản cũ: **`D:\SAO LUU KHOA LUAN\task20a-local-handover-20261027-141936-501742\before-migration-0014.sqlite3`**.
- Dùng **`sqlite3.Connection.backup`**, nguồn mở read-only; bản sao ở ngoài repository, ACL giới hạn tài khoản Windows hiện tại và SYSTEM. Không copy nóng tệp DB, không chứa credential trong báo cáo.
- Kiểm bản sao **trước migrate**: integrity_check **ok**, foreign_key_check **0 vi phạm**, kích thước **417.792 byte**.
- SHA-256 backup: **`dfccc641ec7b81c535f6d21fe4eb459be172b34ba7ef4ae6c6e0febd93fb03cf`**; kiểm lại hash sau migrate vẫn khớp. `manifest.json` giữ thống kê/hash các bảng để đối chiếu riêng, không xuất nội dung bản ghi vào tài liệu.
- Xác minh đích **`D:\KHÓA LUẬN TỐT NGHIỆP\db.sqlite3`**, backend SQLite, `settings=config.local`, Python **`.venv\Scripts\python.exe` 3.13.16**, Django **5.2.18**; không đọc cấu hình production, không dùng DATABASE_URL/PG để kết nối.
- Đối chiếu DB với bản sao ngay trước ghi; plan chỉ có migration **0014** đi tới. Áp dụng **0014 OK**, system check **0 issues**, makemigrations --check --dry-run **No changes detected**, migrate --check **không còn migration chờ**.
- Sau migrate: integrity_check **ok**, foreign_key_check **0 vi phạm**; **24 bảng nghiệp vụ/auth/session hiện có giữ nguyên số dòng và hash toàn bộ nội dung**, không thêm/sửa/xóa tài khoản hoặc giao dịch. Bảng mới có **0 operation**; không đưa dữ liệu hoặc thời gian QA vào local. Chỉ có schema, dòng migration và metadata content type/permissions mới theo cơ chế Django.
- SHA-256 tệp SQLite sau migration (tại lúc kiểm): **`d7d8abea9049eaea144aee9393e04682cf4559670e3a7225375bb901dc5fe40d`**. Hash tệp đổi do migration là bình thường; phép đối chiếu bản ghi cũ xác nhận dữ liệu nghiệp vụ không đổi.

Lệnh tương đương để áp dụng trên local sau khi sao lưu/kiểm đích đúng (không cần chạy lại trên máy đã bàn giao):

```powershell
Set-Location 'D:\KHÓA LUẬN TỐT NGHIỆP'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate finance 0014_similar_transaction_operation --settings=config.local
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check --settings=config.local
```

Không thử thêm giao dịch bằng tài khoản thật để chứng minh tính năng. Bằng chứng chức năng vẫn là UI/test QA ở mục 6–7; bàn giao này xác minh schema local và bảo toàn dữ liệu. Không chạy lại toàn bộ suite khi mã không đổi; giữ **416 PostgreSQL / 21 SQLite bổ sung / 43 JavaScript**, không cộng trùng. Hai model EN/VI và hai requirements giữ nguyên hash.

### Git, bằng chứng và giới hạn

Rà đủ **11 tệp** TASK 20A, không bỏ sót migration/service/test/tài liệu, không stage database, dữ liệu QA, credential, cấu hình QA hoặc ảnh riêng. `git diff --check` đạt. Commit/push **main** thông thường theo yêu cầu, giữ remote và quyền Private; SHA xác nhận sau push và báo trong tin nhắn bàn giao, không nhúng SHA của chính commit vào tài liệu.

`manifest.json`, `local-migration-check.log`, `local-handover-verification.json` nằm trong thư mục backup trên; các script/evidence bàn giao riêng nằm ngoài Git ở thư mục QA. Không tự phục hồi đè DB đang dùng. Khi cần phục hồi, dừng ứng dụng, kiểm hash/integrity bản sao rồi diễn tập vào DB riêng theo quy trình backup/restore đã có trước khi quyết định đổi đích.

**Không kết nối hoặc migrate production**, không trực tiếp deploy. Push có thể kích hoạt auto-deploy đã cấu hình ở hosting; chưa kiểm kết quả online. Giữ các giới hạn PostgreSQL/SQLite đồng thời, tải lớn, thiết bị/trình duyệt và UI online ở mục 6–7; không suy local migrate đạt thành production đạt.
