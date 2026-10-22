# TASK 15A — Ghi nhận phản hồi phân loại

Thực hiện ngày 22/10/2026 trên dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`. Không thay model, hash, bộ nhãn, dữ liệu/thí nghiệm hay dependency. Không huấn luyện, tự học hoặc xuất phản hồi. Không truy cập database production. Kết quả triển khai ban đầu ở mục 7; bàn giao/migrate local theo yêu cầu tiếp theo ở mục 8.

**Phản hồi phản ánh lựa chọn của người dùng, không phải nhãn đúng đã được kiểm định.** Đây là quan sát hành vi khi lưu, chịu ảnh hưởng gợi ý đang hiển thị, ánh xạ do người dùng đặt và cách ghi chép. Không dùng các số đếm để tuyên bố chất lượng thực tế của mô hình.

## 1. Kiến trúc và điểm ghi

Đã đọc `finance/views.py`, forms/models, hai loader VI/EN, bộ nhãn, JavaScript Áp dụng và kiểm thử hiện có. Không có AGENTS.md trong repository. Dịch vụ suy luận giữ nguyên: `category_suggestion` gọi `classification_modes.suggest_label`, loader kiểm artifact/metadata/hash như TASK 08A/10C. Không có nhánh suy luận thứ hai và không fit trong request.

Sau suy luận thành công, server tạo `ClassificationSuggestion` và chỉ trả UUID cho trình duyệt. Gợi ý Transfer/khác loại vẫn là trạng thái **cần xem lại**, không có danh mục để áp dụng. Chưa có ánh xạ vẫn có thể hiện nhãn dự đoán; không tự tạo danh mục.

Nút Áp dụng gọi POST `giao-dich/goi-y-danh-muc/thao-tac/`, action `apply`, có đăng nhập và CSRF. Server kiểm receipt, đầu vào, tài khoản, loại và ánh xạ của category; chỉ sau phản hồi thành công JavaScript đổi trường danh mục. Request này chỉ ghi sự kiện áp dụng của gợi ý, **không lưu giao dịch/phản hồi**. Không tin một cờ `applied` trong POST lưu. Đây là sự kiện endpoint áp dụng được server chấp nhận, không chứng minh ý định tâm lý hoặc thao tác vật lý của một con người; client tự viết có thể gọi endpoint hợp lệ của chính tài khoản.

Khi tự bấm Lưu, view dùng `save_with_feedback` trong `transaction.atomic()`: nhận diện/kiểm receipt → claim bằng UPDATE có điều kiện → đọc lại category mới nhất và khóa dòng → lưu giao dịch bằng ModelForm/Model validation hiện có → ghi feedback nếu so sánh được → gắn giao dịch đã lưu vào receipt. Khóa gợi ý trước danh mục ở cả Apply/Save để tránh đảo thứ tự khóa PostgreSQL. Không dùng chỉ dữ liệu category từ lần suy luận trước.

Nếu không có UUID gợi ý, lưu giao dịch theo luồng thủ công, không cần tải model hoặc truy vấn bảng phản hồi. Nếu có UUID không hợp lệ, chưa lưu và hiện lỗi rõ; render lại bỏ UUID. Người dùng có thể yêu cầu gợi ý mới hoặc kiểm tra danh mục rồi tự bấm Lưu lần nữa để lưu thủ công. Lỗi validation không tạo phản hồi, không tiêu thụ receipt. Lỗi trong transaction rollback cả giao dịch, feedback và trạng thái consumed, kể cả thay đổi coverage/forecast version do lưu giao dịch.

Mọi đường ghi khác như CSV/ORM không tự có phản hồi: chỉ luồng biểu mẫu có receipt đã xác minh mới gọi dịch vụ này. Sửa giao dịch về sau không viết lại phản hồi cũ; nếu người dùng yêu cầu gợi ý mới khi sửa và lưu thành công, tạo một sự kiện mới. Vì thế **số phản hồi không phải số giao dịch khác nhau**.

## 2. Trường dữ liệu và lịch sử

| Bảng | Nội dung |
|---|---|
| `ClassificationSuggestion` | UUID, FK user, digest HMAC đầu vào, kind/mode, nhãn đề xuất, định danh thí nghiệm/candidate, SHA-256 model, seal HMAC, source transaction khi sửa, thời điểm tạo/hết hạn/thu hồi/áp dụng/tiêu thụ, category áp dụng, transaction đã lưu |
| `ClassificationFeedback` | FK user/transaction, OneToOne suggestion (unique ở database), thời điểm lưu, mode, model name/SHA, nhãn đề xuất, FK category cuối có thể null, **snapshot tên category và nhãn cuối**, `applied`, `same_label` |

Không thêm bản sao mô tả vào hai bảng. Digest không phải description mã hóa để giải lại: dùng HMAC với SECRET_KEY phía server, tránh hash văn bản ngắn có thể dò từ điển công khai. Không ghi mô tả, UUID hoặc payload vào log ứng dụng mới; không xuất score/xác suất.

Snapshot lấy từ ánh xạ **tại thời điểm lưu**. Đổi tên/nhãn danh mục về sau không đổi snapshot hoặc các cờ đã ghi. `applied=True` nghĩa đã có action Apply hợp lệ cho receipt, kể cả sau đó người dùng đổi sang danh mục khác. Không suy `applied` chỉ vì nhãn cuối giống nhãn dự đoán.

Chỉ ghi feedback nếu nhãn category cuối nằm trong bộ nhãn chuẩn và tương thích kind. Không ánh xạ hoặc ánh xạ hỏng/sai loại thì không tạo feedback; transaction thành công vẫn tiêu thụ receipt để ngăn gửi lại tạo lô phản hồi/giao dịch mới. Transfer không có ánh xạ thu/chi: không Apply; nếu người dùng tự chọn danh mục có ánh xạ rồi lưu, có thể ghi một so sánh khác nhãn, luôn hiện **Cần xem lại**. Không diễn giải là mô hình sai.

## 3. Hiệu lực, chống sửa và dùng lại

- Thời hạn **15 phút** từ lúc server tạo. Quyền sở hữu được kiểm ở mọi action và khi lưu.
- Ràng buộc với mô tả sau `.strip()` giống ModelForm, kind, mode và đúng ngữ cảnh tạo/sửa (source transaction). Đổi chữ, dấu, hoa/thường hoặc khoảng trắng bên trong cũng làm digest khác; không dùng khóa chuẩn hóa rộng của ML để cho phép gợi ý cũ. Chuẩn hóa đầu vào **suy luận** vẫn giữ nguyên quy tắc thí nghiệm (bỏ một tiền tố đầu, NFC/casefold/gộp khoảng trắng, giữ dấu).
- Server khóa model name/SHA theo hằng đã kiểm ở loader. Receipt có seal HMAC bao gồm UUID, user, digest, kind/mode, nhãn, model identity, source transaction và expires_at. Sửa nhãn/version từ trình duyệt không có tác dụng; sửa các trường receipt bất biến mà không có seal hợp lệ bị từ chối. Đổi SECRET_KEY sẽ vô hiệu receipt cũ, không thay snapshot feedback đã lưu.
- JavaScript xóa UUID/kết quả khi đổi mô tả, loại, mode hoặc yêu cầu gợi ý mới; gửi POST `revoke` cho UUID cũ. Gợi ý đã thu hồi không sống lại khi đổi đầu vào về giá trị cũ. Khi mất mạng, revoke là best effort; backend vẫn kiểm trực tiếp đầu vào đang lưu và hạn dùng, nhưng không thể biết một thay đổi trung gian chưa từng gửi tới server. Không tin client là bằng chứng lịch sử mọi lần gõ.
- Chặn submit trong lúc Apply đang chờ; phản hồi Apply/fetch đến muộn không ghi đè đầu vào đã đổi. Mọi request thay đổi đều có CSRF; không ghi qua GET.
- UPDATE claim chỉ thành công khi chưa consumed, chưa revoked và chưa hết hạn; chạy trong cùng transaction ghi. Feedback có OneToOne suggestion; database không cho hai feedback cùng receipt. Gửi lại cùng receipt đã lưu với đúng tài khoản/đầu vào/ngữ cảnh chuyển tới **giao dịch đã lưu**, không ghi lại dù amount/date/category được sửa trong POST lặp. Muốn sửa giao dịch phải dùng luồng sửa thông thường hoặc gợi ý mới. Receipt consumed được phép phục vụ nhận diện POST lặp sau hạn; không cho Apply lại.
- Receipt lỗi không gây suy luận mới trong request lưu. Không có model vẫn lưu thủ công được. Không nhận file/path model, label/version hoặc user đích từ request.

## 4. Chỉ số và giao diện

Trang `/phan-hoi-phan-loai/` yêu cầu đăng nhập, `never_cache`, truy vấn user trước khi aggregate/list; phân trang 20 dòng, sắp xếp `-created_at, -pk`. Tên category render bằng autoescape; bảng có nhãn ô cho bố cục điện thoại và vùng cuộn riêng, nội dung chính không cần JavaScript.

| Chỉ số | Ý nghĩa |
|---|---|
| So sánh được | Tổng feedback có snapshot nhãn cuối hợp lệ |
| Cùng nhãn | `predicted_label == final_label` khi lưu |
| Khác nhãn | Hai nhãn khác nhau; không phải nhãn lỗi đã kiểm định |
| Có bấm Áp dụng | Server đã chấp nhận action Apply trước lưu |

Cùng + khác bằng tổng; có bấm Áp dụng có thể giao với cả hai nhóm. Tổng hợp dùng cùng queryset giới hạn tài khoản và một aggregate có filter. Không hiện tỷ lệ, decision score hoặc phần trăm chắc chắn. Không dùng chỉ số từ thí nghiệm cũ trên màn hình này.

## 5. Xóa dữ liệu, thời hạn lưu và vận hành

- Xóa transaction: CASCADE xóa feedback và các receipt gắn với transaction (source/saved). Không giữ phản hồi của giao dịch đã xóa.
- Xóa category: giữ nguyên PROTECT của giao dịch/ngân sách hiện có. Khi category thực sự có thể xóa (ví dụ transaction đã chuyển sang category khác), FK final/applied category SET_NULL; snapshot vẫn thuộc user/transaction và không thay đổi. Không nới quy tắc xóa/đổi loại category.
- Xóa user: FK CASCADE cho hai bảng mới, không giữ feedback/receipt vô chủ. **Hiện hệ thống vẫn chặn xóa user còn transaction qua Category PROTECT**; task này không thêm luồng xóa tài khoản hoặc bỏ bảo vệ đó. Quy trình quản trị phải xử lý transaction/ngân sách liên quan trước; khi xóa user được phép, receipt pending cũng bị xóa.
- `cleanup_classification_suggestions` dọn receipt hết hạn **chưa dùng**, gồm receipt đã thu hồi. Không xóa receipt consumed/feedback còn gắn với transaction; giữ để phân tích lịch sử và chống POST lặp. Không có retention tự xóa feedback theo ngày trong task này.
- Hai bảng nằm trong database bền vững của website; không giữ payload trong cookie/cache/filesystem tạm. Không có job nền mới tự chạy. Cần vận hành lệnh dọn định kỳ bằng môi trường đúng database, không in dữ liệu; chưa thay startup Render hoặc tạo cron trả phí. Đến khi chạy cleanup, receipt hết hạn vẫn bị từ chối dù còn trong bảng.

```powershell
# Chỉ chạy sau khi đã sao lưu/migrate và chọn đúng môi trường local:
& '.\.venv\Scripts\python.exe' -X utf8 manage.py cleanup_classification_suggestions --settings=config.local
```

Không đưa database/feedback vào Git, dataset train/test, gói inference hoặc bản export CSV giao dịch. Backup chứa hai bảng mới phải được bảo vệ như dữ liệu tài chính, không công khai.

## 6. Migration và hướng dẫn áp dụng sau review

Migration mới: `0010_classificationsuggestion_classificationfeedback`, phụ thuộc `0009_postgresql_budget_guards` và AUTH_USER_MODEL. Chỉ tạo hai bảng/FK/index, không sửa giá trị tài khoản, giao dịch, category hay coverage cũ. OneToOne tạo unique constraint cho suggestion. UUID/FK/Boolean/DateTime/Char và Count filter đều dùng ORM Django hỗ trợ SQLite/PostgreSQL; không có SQLite-only SQL mới. Có index `(user, -created_at)` và expires_at.

**Giai đoạn đầu chỉ migrate QA; bước bàn giao đã migrate local sau backup, xem mục 8. Không kết nối production.** Khi áp dụng ở máy khác, trước tiên tạm dừng thao tác ghi local, thực hiện SQLite backup API ra thư mục timestamp ngoài dự án như TASK 09B/11A/12B. Ví dụ mở Django shell đúng môi trường local rồi chạy đoạn dưới:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 manage.py shell --settings=config.local
```

```python
from datetime import datetime
from pathlib import Path
import sqlite3
from django.db import connection
from django.db.backends.sqlite3._functions import register
backup_dir = Path('D:/SAO LUU KHOA LUAN') / ('before-task15a-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
backup_dir.mkdir(parents=True, exist_ok=False)
connection.ensure_connection()
with sqlite3.connect(backup_dir / 'db.sqlite3') as destination:
    connection.connection.backup(destination)
    register(destination)  # CHECK của schema hiện có dùng hàm ngày của Django.
    assert destination.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
connection.close()
```

Ghi thêm SHA-256/manifest bản sao theo quy trình hiện có, kiểm hash trước phục hồi; không copy đè database đang chạy. Sau khi xác nhận backup tốt mới chạy:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate --settings=config.local
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check --settings=config.local
& '.\.venv\Scripts\python.exe' -X utf8 manage.py showmigrations finance --settings=config.local
```

Render: trước lần phát hành đã duyệt, backup PostgreSQL bằng quy trình pg_dump riêng tư trong `docs/render-deployment.md`, kiểm backup và phục hồi ở môi trường riêng. Giữ cấu hình `DATABASE_URL` production; không fallback SQLite. `deploy/render-start.sh` → `scripts/render_start.py` hiện đã migrate dưới advisory lock khi start; migration mới sẽ được chạy qua quy trình đó sau khi mã được phát hành. Không cần shell/pre-deploy trả phí mới. Không chạy lệnh trên database Render hoặc thay cấu hình dịch vụ trong bước bàn giao; push main có thể kích hoạt quy trình auto-deploy đã cấu hình của Render. Rollback schema làm mất feedback/receipt, vì vậy không tự reverse migration nếu chưa có backup và phê duyệt.

## 7. Kiểm chứng ban đầu trước bàn giao local

Settings kiểm thử riêng dùng `config.base`, SQLite trong bộ nhớ; guard từ chối kết nối mọi tệp SQLite. QA trình duyệt dùng `D:\SAO LUU KHOA LUAN\task15a-qa-20261022-145334\qa.sqlite3`, server `127.0.0.1:8015`, runner chỉ cho mở đúng tệp QA này. Tài khoản/danh mục/giao dịch mô phỏng chỉ tạo ở QA, không chứa dữ liệu người dùng thật.

- `finance/test_classification_feedback.py`: **23 kiểm thử đạt**, gồm cùng/khác nhãn, có/không Apply, Apply rồi đổi lựa chọn/ánh xạ, danh mục chưa ánh xạ, Transfer/khác loại, model identity thay đổi, receipt malformed/expired/revoked/tampered/khác user/khác target, đổi đầu vào, lỗi lưu, rollback cả coverage, POST lặp, snapshot, xóa, cleanup, danh sách/tổng/phân trang/CSRF.
- Hồi quy toàn bộ `finance`: **252/252 đạt** (120,620 giây), gồm 23 ca feedback mới; Django system check không có vấn đề, `makemigrations --check --dry-run`: No changes detected. Chạy bằng runtime QA có sẵn dependency deploy để không bỏ qua nhóm kiểm tra Render; không cài thêm vào môi trường dự án. Hai mô hình thật được loader kiểm trong kiểm thử có sẵn; không chạy lại thí nghiệm nghiên cứu hoặc đổi artifact.
- JavaScript Node chuẩn: **17/17 đạt**, gồm 13 ca suggestion và 4 ca phản hồi submit dùng chung. Kiểm request Apply/revoke/CSRF, không tự lưu, không ghi đè khi phản hồi đến muộn, không submit trong khi Apply pending, lỗi endpoint và các thay đổi mode/description/kind.
- SQLite QA trên đĩa migrate từ rỗng đến 0010 thành công. Kiểm thêm migration **0009 → 0010 trong RAM có sẵn user/category/transaction QA**: toàn bộ giá trị trước/sau khớp, `integrity_check=ok`, `foreign_key_check` rỗng. Chưa áp dụng migration vào SQLite thật.
- PostgreSQL: compile offline **19 câu DDL và 3 dạng query**, cấm mở connection/cursor; schema/query không lỗi compile. **Chưa chạy migration, kiểm thử cạnh tranh hoặc kiểm thử tích hợp trên PostgreSQL thật**. Không coi compile offline là kiểm chứng vận hành trên Render.
- Trình duyệt: đăng nhập QA, trang phản hồi trống, gợi ý **VI thật → Apply → lưu → cùng nhãn/có Apply**; gợi ý **EN thật → chọn category khác thủ công → lưu → khác nhãn/không Apply**; tổng hiển thị **2 / 1 / 1 / 1**. Đã thao tác menu điện thoại và đọc bảng dạng ô có nhãn; không chỉ dựa trên HTTP 200.
- Đã yêu cầu khung 390×844, nhưng công cụ/zoom trả kích thước CSS khác. Sau hiệu chỉnh, đo DOM được **390×845**, `clientWidth=scrollWidth=367` (có thanh cuộn); không tràn ngang toàn trang. **Chưa xác minh đúng tuyệt đối 390×844** hoặc thiết bị điện thoại thật. Screenshot công cụ ở khung hẹp bị lỗi; không coi ảnh khung khác là bằng chứng pixel cho 390×844. Desktop CSS 981×997 đã đọc/chụp, không tràn ngang. Đã reset viewport sau kiểm tra.
- Ảnh desktop QA: `D:\SAO LUU KHOA LUAN\task15a-qa-20261022-145334\feedback-desktop.png`. Bằng chứng QA, database, SQL compile và runner đều ngoài Git. Không công bố mật khẩu QA/secret trong tài liệu. Các trường hợp lỗi/rollback và tài khoản khác được kiểm tự động; chưa thao tác mọi ca đó trong trình duyệt.
- Rà diff/đường dẫn: **16 tệp mới hoặc sửa**, **186 đường dẫn đang được Git theo dõi**; không thấy token, private key, URL chứa credential hoặc bí mật local đã đối chiếu trong bộ nhớ. Không đưa SQLite/dataset/model/config riêng vào diff. `git diff --check` đạt; không stage, commit hoặc push.

Các lệnh kiểm thử thông thường để chạy lại trên máy phát triển (Django tạo database test riêng; không chạy với settings production):

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 manage.py test finance.test_classification_feedback finance.test_classification finance.test_vietnamese_classification --settings=config.local
node --test scripts/test_transaction_suggestion.js scripts/test_form_feedback.js
```

Lần kiểm chứng này dùng runner guard ngoài Git nêu trên để chặn cả việc vô tình mở tệp SQLite thật. Khi chạy hồi quy các kiểm thử deploy, dùng runtime QA deployment đã có; không cài dependency mới vào `.venv` dự án.

Không có nhãn chuẩn độc lập hoặc thẩm định người dùng trong task. Không có suy luận về độ đầy đủ lịch sử từ phản hồi. Không tự đưa phản hồi vào nghiên cứu; muốn sử dụng về sau cần một thiết kế dữ liệu, quyền riêng tư và đánh giá riêng.

## 8. Bàn giao local và Git — 22/10/2026

Theo yêu cầu bàn giao tiếp theo, đã kiểm settings **`config.local`**, engine SQLite và đường dẫn đúng `D:\KHÓA LUẬN TỐT NGHIỆP\db.sqlite3`. Runner ngoài Git chặn kết nối SQLite tới mọi tệp khác ngoài local và bản backup; không dùng settings production hoặc DATABASE_URL.

### Backup và đối chiếu dữ liệu

- Thư mục mới: `D:\SAO LUU KHOA LUAN\task15a-local-handover-20261022-152039`.
- `db.sqlite3` được tạo bằng `sqlite3.Connection.backup`, không copy tệp live; không ghi đè bản sao cũ. Trước migrate đã kiểm `integrity_check=ok`, `foreign_key_check` rỗng và dấu vân tay nội dung các bảng khớp source.
- SHA-256 bản backup: `46e628b5ea4efa165bfbafaa318638e056c6fa11db1969b986d1267715129bc3`. Đã kiểm lại sau migration.
- `manifest.json` lưu phương thức, thời điểm UTC, kích thước/hash backup và dấu vân tay theo bảng trước/sau. Runner và manifest nằm ngoài Git; không công bố nội dung hàng, mật khẩu, session hoặc secret.
- So sánh nội dung dùng biểu diễn `quote()` của SQLite để không nhầm khác biệt kiểu Python ngày/Decimal giữa connection Django và sqlite3 thuần. Lần so sánh đầu bị dừng vì khác biểu diễn kiểu; đã kiểm lại cùng biểu diễn lưu trữ trước khi cho phép migrate, không ghi đè backup.

### Local migration và xác minh chức năng

`migrate --settings=config.local` áp dụng **0009** đang chờ (nhánh SQLite không chạy SQL guard PostgreSQL) rồi **0010** thành công. Django system check không có vấn đề; `migrate --check` không còn migration chờ; local `integrity_check=ok`, không có vi phạm khóa ngoại.

Mọi bảng nghiệp vụ cũ giữ nguyên giá trị. `post_migrate` của Django thêm đúng **2 content type và 8 permission** cho hai model mới; tất cả các hàng metadata cũ và quan hệ quyền cũ giữ nguyên. Không coi phần metadata mới này là thay đổi giao dịch/tài khoản người dùng.

Đã xác minh trên **database local thật trong một transaction rollback toàn bộ**: tạo tài khoản/danh mục QA tạm, đăng nhập test client, tải form, suy luận VI/EN bằng đúng artifact thật, Apply có CSRF, lưu transaction/feedback, gửi lại POST, xem danh sách riêng và chặn khách. Cuối kiểm tra rollback toàn bộ, đối chiếu dấu vân tay **tất cả các bảng local** trước/sau khớp. Hai bảng mới vẫn rỗng; không giữ lại tài khoản, session, giao dịch hoặc feedback QA trong local. Đây là kiểm HTTP/service trên local, không gọi là kiểm trình duyệt local; bằng chứng trình duyệt QA riêng ở mục 7 được giữ lại.

Mã thực thi không thay đổi sau 252/252 kiểm thử backend và 17/17 JavaScript đạt ở mục 7; tận dụng kết quả đó, không chạy lại toàn bộ suite hoặc thí nghiệm ML chỉ để bàn giao. Chỉ bổ sung kiểm local/migration và tài liệu.

### Rà PostgreSQL

Đã đọc lại migration 0010 và SQL compile offline:

- Chỉ tạo hai bảng trống mới; không thêm cột NOT NULL vào bảng đã có dữ liệu, không backfill, RunPython/RunSQL hoặc sửa hàng cũ. Phụ thuộc đúng migration 0009 và AUTH_USER_MODEL.
- UUID primary key cho suggestion; feedback có bigint identity. FK user dùng **integer** theo `auth_user.id` hiện có; FK transaction/category dùng **bigint**, FK suggestion dùng **uuid**, khớp kiểu bảng tham chiếu.
- `suggestion_id` có NOT NULL + UNIQUE (OneToOne), ngăn hai feedback cho cùng receipt ở database. Các FK được PostgreSQL backend Django sinh `DEFERRABLE INITIALLY DEFERRED`; receipt và feedback có thể được ghi trong cùng transaction rồi kiểm ràng buộc lúc commit.
- CASCADE/SET_NULL là chính sách **Django deletion collector** đã kiểm bằng ORM, không khẳng định SQL FK có `ON DELETE CASCADE/SET NULL`. Xóa bằng SQL trực tiếp không tương đương luồng ORM và có thể bị FK chặn.
- Không có CHECK liên bảng để chứng minh user/category/transaction cùng chủ hoặc `same_label` đúng. Quyền sở hữu, ánh xạ, snapshot và trạng thái receipt được kiểm trong dịch vụ server; FK chỉ bảo đảm bản ghi tham chiếu tồn tại. Choices nhãn/mode cũng không phải enum/CHECK do migration tạo.
- Index user, FK, expires_at và `(user, created_at DESC)` dùng cú pháp PostgreSQL hợp lệ theo compile. UPDATE claim, select_for_update và thứ tự khóa receipt → category được rà; chưa đo cạnh tranh nhiều worker trên PostgreSQL.
- Tạo FK có thể cần khóa bảng tham chiếu; không cam kết migration không chờ khóa khi production đang ghi. Cần backup và quy trình migrate/advisory lock hiện có.

**Giới hạn giữ nguyên:** chưa kết nối PostgreSQL thật, chưa thử migrate trên bản sao dữ liệu PostgreSQL hiện có, chưa kiểm quyền role/lock timeout hoặc auto-deploy Render thực tế trong bước này. Compile offline và SQLite local thành công không thay thế các kiểm tra đó. Không đổi model ML, hash, dependency hay cấu hình production.

### Git và phục hồi

Mã, migration, kiểm thử và tài liệu TASK 15A được rà để bàn giao lên main theo yêu cầu; backup/manifest/runner local, SQLite, dữ liệu và mô hình không nằm trong commit. SHA commit và việc local khớp remote được báo trong kết quả bàn giao, tránh tự chèn SHA của chính commit vào nội dung commit.

Nếu cần phục hồi local: dừng các tiến trình ghi đúng dự án, kiểm SHA-256 backup ở trên và integrity bằng connection có đăng ký hàm SQLite Django, giữ lại database hiện tại thành một bản sao riêng rồi mới phục hồi ở thư mục mới để kiểm trước. Backup này ở schema trước 0009/0010; dùng mã tương ứng hoặc migrate lại sau khi phục hồi. Không copy đè database đang mở, không dùng backup này để ghi đè PostgreSQL/production.
