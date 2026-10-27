# TASK 18B — Hướng dẫn bắt đầu và bộ danh mục mẫu

Thực hiện và chốt bàn giao 26/10/2026 trên dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`. Mã được bàn giao lên main theo yêu cầu; SHA local/remote và kết quả push báo trong tin nhắn cuối. Không sửa SQLite local thật, kết nối Render, đổi dependency, model/hash hoặc thí nghiệm ML. Không cần migration mới. Push không được coi là bằng chứng UI hoặc database production đã được xác minh.

## Cách dùng

1. Mở **Danh mục → Thêm danh mục mẫu**. GET chỉ xem trước, mặc định chưa chọn mục nào.
2. Đọc loại thu/chi, phạm vi và nhãn đề xuất/chưa ánh xạ; đánh dấu từng mục rồi **Xác nhận thêm mục đã chọn**.
3. Kết quả ghi rõ số mục thêm/bỏ qua và tên tương ứng. Nếu đã có tất cả 11 mục, hiện trạng thái rõ và không còn nút xác nhận thêm.
4. Tự ghi giao dịch bằng form hiện có. Danh mục mẫu chỉ là cấu hình, **không tạo giao dịch, ngân sách hoặc tiền demo**. Đăng ký/mở trang cũng không tự thêm danh mục.

Người dùng vẫn có thể tự tạo danh mục thủ công hoặc sửa ánh xạ sau khi xác định rõ ý nghĩa. Thêm bộ mẫu không hứa phân loại đúng; kết quả ML vẫn là gợi ý thử nghiệm, không tự lưu và luôn cần người dùng kiểm tra/Áp dụng.

## 11 mẫu và quyết định ánh xạ

Đã đọc đủ 17 mã trong `finance/classification_labels.py`, quy tắc TASK 10A ở `vietnamese-classification-data.md`, kiểm định tiếng Anh và luồng suy luận/phản hồi hiện có. Không suy nhãn chỉ từ chiều tiền hoặc tên chung.

| Danh mục | Loại | Mã khi tạo mới | Phạm vi/quyết định |
|---|---|---|---|
| Ăn uống | Chi | Chưa ánh xạ | Nhóm rộng có thể chứa Restaurants hoặc Groceries, không ép vào ăn ngoài |
| Đi chợ & siêu thị | Chi | Groceries | Nguyên liệu/thực phẩm/hàng tiêu hao vệ sinh nhà; không dùng nơi bán để gán mọi mặt hàng |
| Di chuyển | Chi | Transportation | Đi lại thường ngày/vận hành phương tiện; không mặc định chuyến nghỉ là di chuyển thường ngày |
| Nhà ở | Chi | Chưa ánh xạ | Có thể Rent, Mortgage, Utilities hoặc mua đồ dùng; không chọn một nhãn hẹp thay người dùng |
| Hóa đơn | Chi | Chưa ánh xạ | Có thể tiện ích, thuê bao, bảo hiểm…; không gom tất cả vào Utilities/Fees |
| Sức khỏe | Chi | Healthcare | Khám/điều trị/phòng bệnh/thiết bị y tế; làm đẹp thường ngày là phạm vi khác |
| Giáo dục | Chi | Education | Học/đào tạo/thi và mục đích học rõ |
| Mua sắm | Chi | Shopping | Quần áo, phụ kiện, đồ dùng chung; mục đích chuyên biệt ưu tiên danh mục riêng |
| Giải trí | Chi | Entertainment | Hoạt động/vé/nội dung mua lẻ, không gom thuê bao gia hạn |
| Lương | Thu | Income | Nguồn xác định từ công việc; không suy thu nhập từ tiền vào |
| Thu nhập khác | Thu | Chưa ánh xạ | Cần xác minh nguồn/bản chất, không tự coi hoàn tiền/chuyển khoản là Income |

**7 mẫu có ánh xạ, 4 mẫu chưa ánh xạ.** Phạm vi này được hiển thị trong xem trước, không phải ánh xạ ngầm theo tên ở lúc suy luận. Người dùng có thể bỏ chọn nếu phạm vi không hợp nhu cầu.

Các nhãn đã rà nhưng không có mẫu riêng: **Fees, Insurance, Mortgage, Personal Care, Rent, Restaurants, Subscription, Travel, Utilities**. Chúng không bị gán thay cho các nhóm rộng. **Transfer** là mã thứ 17: không tạo danh mục thu/chi mẫu và vẫn yêu cầu xem lại. Bộ mẫu không bao phủ mọi nhãn; mô hình dự đoán nhãn chưa ánh xạ vẫn báo chưa có danh mục phù hợp theo cơ chế cũ.

## Chuẩn hóa, trùng và giao dịch đồng thời

Khóa so khớp bộ mẫu: **(kind, normalized_name(name))**. Chuẩn hóa NFC, casefold, gộp mọi khoảng trắng liên tiếp thành một khoảng trắng, bỏ khoảng trắng ngoài, NFC lại. Giữ dấu tiếng Việt và ký hiệu: không coi `Di cho` là `Đi chợ`, không đổi `&` thành `và`, không dịch hoặc đoán tên gần nghĩa. Khác loại thu/chi là hai khóa khác nhau.

Chỉ đọc danh mục của request.user. Nếu khóa đã có, **bỏ qua toàn bộ mục**: không sửa tên, ID, canonical_label, không gộp hai danh mục cũ và không “bổ sung” ánh xạ ngay cả khi đang trống. Các danh mục cũ tự chọn ánh xạ khác cũng được giữ nguyên. POST cũ vẫn được kiểm lại; checkbox disabled trên xem trước không phải lớp bảo vệ duy nhất.

Server chỉ nhận danh sách ID ổn định trong bộ 11 mẫu cho phép. Tên/loại/nhãn/chủ tài khoản được lấy từ cấu hình server + request.user, không nhận giá trị tùy ý từ trình duyệt. ID lạ hoặc không chọn mục nào báo lỗi; không tạo một phần trước khi phát hiện ID lạ. ID lặp trong cùng lựa chọn không nhân đôi vòng tạo.

`add_defaults` chạy trong **transaction.atomic**. Trước khi đọc danh mục, `lock_catalog` UPDATE `auth_user.last_login = last_login` cho đúng user để lấy khóa hàng PostgreSQL/khóa ghi SQLite; giá trị thời điểm đăng nhập được giữ nguyên. Sau khóa mới tạo tập khóa chuẩn hóa và ghi các mục còn thiếu. `Category.save` dùng cùng khóa trước full_clean/save, phối hợp với các form lưu danh mục thủ công hiện có. Lỗi trong lô rollback toàn bộ; không dùng ignore_conflicts để che lỗi.

POST lặp nhận ra các khóa đã tồn tại và bỏ qua, không cần bảng receipt mới. Nếu người dùng chủ động xóa/đổi tên danh mục sau đó, lần POST mới có thể thêm lại mẫu thiếu; đây không phải mã thao tác bất biến cho mọi lần thiết lập. SQLite báo khóa thì form thông báo thử lại, không tự retry vô hạn.

Phạm vi bảo đảm: các đường lưu Category.save và endpoint bộ mẫu của dự án. **Không có unique constraint chuẩn hóa mới**; database giữ unique (user,kind,name) chính xác như trước. Quy tắc tên thủ công cũ không bị viết lại; bộ mẫu không sửa/gộp các danh mục chuẩn hóa trùng đã có. QuerySet.update/bulk_create hoặc SQL ghi trực tiếp không qua khóa không nằm trong bảo đảm này. Không gọi đây là phát hiện mọi tên/giao dịch trùng.

## Hướng dẫn bắt đầu

Khối **Bắt đầu với Sổ Thu Chi** trên Tổng quan dùng HTML details/summary, mặc định **thu gọn** ở mọi tài khoản để số liệu dễ thấy, mở/đóng được khi JavaScript tắt. Không overlay, chặn trang hoặc bắt buộc hoàn thành. Lựa chọn mở/đóng chỉ thuộc trang hiện tại, chưa lưu xuyên phiên.

- Thiết lập danh mục: hoàn thành khi tài khoản có ít nhất một Category, không bắt buộc dùng mẫu.
- Ghi giao dịch đầu tiên: hoàn thành khi tài khoản có ít nhất một Transaction.
- Ngân sách: hiển thị đã có khi có Budget của tài khoản, là bước **tùy chọn**; không góp vào bộ đếm 2 bước chính.
- Kiểm dữ liệu trên toàn lịch sử của chính tài khoản, độc lập tháng Tổng quan đang chọn. Xóa dữ liệu liên quan sẽ làm trạng thái cập nhật theo exists ở lần mở trang sau.
- Không lấy coverage làm điều kiện, không tự xác nhận đầy đủ, không gọi ML hoặc tính dự báo khi mở hướng dẫn.

## Kiểm thử tự động

| Phạm vi | Kết quả | Cách đếm |
|---|---|---|
| `finance.test_getting_started` | **16/16 đạt** | Tài khoản mới/cũ, signup không seed, GET không ghi, subset, chuẩn hóa, khác loại, replay, quyền/CSRF, rollback, trạng thái và ánh xạ ML |
| Hồi quy toàn finance | **366/366 đạt**, 183,413 giây | 350 trước + 16 mới; không cộng lại 16 vào tổng 366 |
| Nhóm 16 sau tinh chỉnh giao diện cuối | **16/16 đạt**, 3,304 giây | Kiểm lại phần liên quan, không phải 16 bài bổ sung |
| JavaScript dùng chung | **30/30 đạt** | Không sửa/thêm JS trong task; kiểm nhập nhanh/tiền/form feedback/ML Apply |
| System check SQLite QA và PostgreSQL QA | Không lỗi | Cấu hình riêng, không production |
| `makemigrations --check --dry-run` | No changes detected | Không có migration mới; SQLite QA mới khởi tạo đến 0013 hiện có |

Các test có đối chiếu dữ liệu Category cũ, mọi bảng finance khác (gồm phản hồi ML đã có dữ liệu) và User trước/sau thêm mẫu: không đổi, ngoài các Category mới được chọn. Test cạnh tranh SQLite dùng hai thread/connection trên file QA; có chấp nhận lỗi khóa rồi retry tuần tự cùng lựa chọn để kiểm tính không nhân đôi. Bằng chứng PostgreSQL thật dưới đây bổ sung kiểm hai HTTP POST cùng thực thi.

Runtime sẵn có: `D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe` (Python 3.13/Django 5.2); không cài dependency. Ví dụ chạy lại chỉ trong QA riêng:

```powershell
& 'D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe' -X utf8 'D:\SAO LUU KHOA LUAN\qa-18b-20261026\manage_qa.py' test finance --noinput --settings=qa18b_test_settings
node --test scripts/test_money.js scripts/test_quick_entry.js scripts/test_transaction_suggestion.js scripts/test_form_feedback.js
```

## PostgreSQL QA thật

Dùng lại cluster TASK16 **`D:\POSTGRESQL QA\rehearsal-20261023\data-attempt2`**, PostgreSQL **18.6**, database **qa_restore_20261023**, chỉ **127.0.0.1:55432**. Xác minh data_directory/system identifier `7699798773140758112`/version/listener trước thao tác. Profile QA kế thừa config.base, host/port/database cố định, loại PG*/DATABASE_URL kế thừa, guard identity/READ COMMITTED trước request. Không kết nối Render. Không có pending migration, không chạy migration mới.

Tạo role **qa_web_18b** không superuser/CREATEDB/CREATEROLE và một tài khoản Django thử mới. Admin QA đã được cấp mật khẩu ngẫu nhiên bằng single-user khi cluster dừng vì credential trước đã hủy; không đổi mật khẩu Django của người dùng cũ. Một Category QA được chuẩn bị trước: tên Groceries dạng NFD/hoa/khoảng trắng, **canonical_label trống**, để chứng minh không ánh xạ lại.

Hai session đăng nhập cùng tài khoản thử qua **Waitress 4 threads localhost:8004**, GET form rồi POST **có CSRF thật** cùng chọn 11 mục. Connection điều phối QA giữ FOR UPDATE trên **user thử**, chờ pg_stat_activity xác nhận **hai backend PID riêng cùng chờ Lock**, rồi nhả. Không thay/mocking logic ứng dụng.

| Kiểm tra | Kết quả |
|---|---|
| Hai POST đồng thời | Cả hai HTTP 200 thành công; một thêm **10**, bỏ qua **1**; một thêm **0**, bỏ qua **11** |
| Số danh mục/khóa chuẩn hóa | **11 / 11**, không trùng |
| Mục đã có | Tên/ID và ánh xạ trống giữ nguyên; last_login không đổi bởi thiết lập |
| Gửi lại POST | Thêm **0**, bỏ qua **11** |
| ID chọn có Transfer không được phép | Lỗi rõ, không thêm hoặc sửa mục nào |
| Dữ liệu khác của user thử | Transaction, Budget, Coverage, Suggestion và Feedback đều **0** |
| Dữ liệu QA cũ có sẵn | Đối chiếu digest **196 bản ghi**, **0 hàng thay đổi/mất** |

Bằng chứng ở **`D:\POSTGRESQL QA\getting-started-18b-20261026`**, ngoài Git: `http-defaults-report.json`, `final-verification.json`, `system-check.log`, identity/shutdown report và manifest. Baseline digest/native log giữ trong vùng ACL riêng, không sao chép nội dung riêng tư vào tài liệu.

Đã dừng đúng website QA và PostgreSQL QA, pg_ctl stop exit **0**, cổng **8004/55432 đóng**; xóa credential/passfile tạm. Không tạo service, restore lại archive hoặc sửa dữ liệu cũ. Đây là một cặp cạnh tranh có điều phối, **chưa kiểm tải lớn, mọi lịch tranh chấp hoặc isolation khác**; không coi HTTP/DB là bằng chứng UI PostgreSQL đầy đủ.

## QA trình duyệt và ảnh

SQLite QA mới, settings/cookie/credential riêng ở **`D:\SAO LUU KHOA LUAN\qa-18b-20261026`**, URL **http://127.0.0.1:8022/**. Không sao chép dữ liệu thật. Dùng tài khoản QA mới và tài khoản QA có sẵn hai cấu hình danh mục; thêm một tài khoản rỗng chỉ để chụp trạng thái ban đầu sau tinh chỉnh. Banner ghi rõ **QA 18B · Dữ liệu mô phỏng, không phải tài khoản thật**.

Đã thử Edge/Chromium headless **1280×900** và **390×844**:

- Hướng dẫn 0/2 thu gọn, mở/đóng native; xem trước 11 checkbox ban đầu chưa chọn; không tràn ngang toàn trang.
- Desktop chọn 3 mục → thêm đúng 3. Mobile dùng xem trước cũ vẫn chọn 11 → server thêm 8/bỏ qua 3, hiện tất cả mẫu đã có và bỏ nút xác nhận thêm.
- Tài khoản cũ: hai mục chuẩn hóa đã có bị disabled. Thêm 2 mục bằng **trình duyệt mobile tắt JavaScript**; danh sách của tài khoản này chỉ có 4, không thấy 11 mục của tài khoản kia. Kiểm trực tiếp DB giữ nguyên ID/tên/ánh xạ hai mục cũ.
- Mô hình VI thật với “Đóng học phí học kỳ đại học”: trước thiết lập dự đoán Education nhưng chưa có category; sau thêm Giáo dục tìm đúng một category của tài khoản. EN thật với “Tuition fee for university” cũng tìm đúng Education. Đã chọn và **Áp dụng** vào form, không bấm Lưu ở các lượt ML đó; không phát sinh feedback.
- Sau các bước thiết lập và ML Apply, xác minh **0 Transaction/Budget/Coverage/Feedback**. Sau đó người kiểm **chủ động dùng form thường** lưu một khoản thu QA 50.000 VND để thử bước “giao dịch đầu tiên”; hướng dẫn thành 2/2 dù chưa có Budget/Coverage. Đây không phải giao dịch do chức năng mẫu tạo. Mọi khoản này chỉ nằm trong QA.

Hai mô tả suy luận là ví dụ AI biên soạn, chưa rà trùng train, không phải tập kiểm tra độc lập hoặc bằng chứng chất lượng phân loại. Không tính tỷ lệ đúng, không đổi score thành phần trăm, không huấn luyện/refit artifact.

| Ảnh/bằng chứng trong thư mục SQLite QA | Nội dung |
|---|---|
| `{desktop,mobile}-getting-started-new.png` | Bản cuối, tài khoản rỗng 0/2, mặc định thu gọn |
| `{desktop,mobile}-getting-started-viewport.png` | Khung 1280×900 / 390×844, số liệu vẫn đọc được |
| `{desktop,mobile}-getting-started-expanded.png` | Mở hướng dẫn theo lựa chọn |
| `{desktop,mobile}-defaults-preview.png` | 11 mục, loại và phạm vi/ánh xạ trước chọn |
| `desktop-defaults-partial.png`, `mobile-defaults-all-existing.png` | Thêm một phần / kiểm lại xem trước cũ / tất cả đã có |
| `{desktop,mobile}-existing-account-preview.png`, `mobile-existing-account-after.png` | Trùng chuẩn hóa và thêm khi tắt JS |
| `desktop-ML-vi-after-samples.png`, `desktop-ML-en-after-samples.png` | Apply đúng ánh xạ, chưa lưu |
| `{desktop,mobile}-getting-started-complete.png` | 2/2 sau thao tác lưu QA chủ động, ngân sách vẫn tùy chọn |
| `browser-checks.json`, `model-ui-checks.json`, `before-manual-transaction.json` | Các assert UI và mốc chưa có giao dịch |
| `regression.log`, `getting-started-final-tests.log`, `javascript.log`, `verification-report.json`, `evidence-manifest.json` | Kiểm thử/hash/integrity và bảo toàn cấu hình cũ |

Chưa kiểm Safari/Firefox, điện thoại/bàn phím vật lý, screen reader hoặc UI online. Mobile là viewport mô phỏng. Không có ảnh dữ liệu thật hoặc ảnh QA trong repository.

## Tệp và triển khai

Tệp mới: `finance/category_defaults.py`, `category_defaults_views.py`, `category_locks.py`, `test_getting_started.py`, `templates/finance/category_defaults.html`, `templates/finance/includes/getting_started.html`, tài liệu này.

Tệp sửa: `finance/models.py` (khóa Category.save, **không đổi trường/schema**), `views.py` (trạng thái hướng dẫn), `urls.py`, `templates/base.html`, `templates/finance/category_list.html`, `dashboard.html`, CSS và README. Không sửa luồng signup/login/logout, receipt/ML Apply, CSV, tiền, coverage, dự báo hoặc ngân sách.

Không cần migrate local/production cho TASK 18B; QA khởi tạo theo schema 0013 có sẵn. Đã rà diff/static trong đợt chốt dưới đây; giữ quy trình backup/deploy hiện có, không tự seed danh mục trong migrate/startup. SQL/mã ghi trực tiếp bỏ qua Category.save phải tự phối hợp khóa hoặc không dùng đồng thời với luồng thiết lập.

Đã đối chiếu SHA-256 SQLite thật và hai model EN/VI: giữ nguyên; PostgreSQL QA còn đối chiếu archive gốc. Đã rà **15 tệp** mới/sửa cùng các đường dẫn đang theo dõi và quét mẫu credential: không phát hiện bí mật hoặc artifact riêng tư; `git diff --check` đạt. Quét mẫu bổ sung cho rà thủ công, không bảo đảm phát hiện mọi dạng bí mật. `diff-review.json` ngoài Git ghi danh sách tệp và kết quả. Không đưa database, dataset, credential/settings QA, log riêng tư hoặc ảnh lên Git. Bàn giao chỉ commit mã/kiểm thử/tài liệu đã rà; PostgreSQL QA đã dừng.

## Chốt bàn giao — migration, static và Git

Đã rà lại đủ **11 danh mục**: giữ **7 ánh xạ** phù hợp với phạm vi đã mô tả; **Ăn uống, Nhà ở, Hóa đơn, Thu nhập khác** vẫn có canonical_label rỗng. Không bổ sung Transfer, không chỉnh model hoặc đổi phạm vi để ép một nhóm rộng vào nhãn hẹp. Danh mục đã có luôn bỏ qua toàn bộ; không ghi tên/ánh xạ mới lên hàng cũ.

Đã chạy lại **`makemigrations --check --dry-run`** bằng settings SQLite QA riêng: **No changes detected**. Thay đổi `Category.save` chỉ thêm transaction/khóa và giữ kiểm tra cũ, không đổi field/schema; không có migration bị bỏ sót. System check QA không lỗi. Mã ứng dụng không sửa thêm trong đợt chốt, tận dụng **366 Django / 30 JavaScript** đã đạt, không chạy/cộng trùng nhóm 16 vào tổng 366.

### Collectstatic production QA

Đã import **config.render thực tế**, DEBUG=False, WhiteNoise **CompressedManifestStaticFilesStorage**, settings/đầu ra nằm ngoài repository tại **`D:\SAO LUU KHOA LUAN\qa-18b-20261026\handoff`**. Host `.invalid`, secret ngẫu nhiên trong bộ nhớ, URL PostgreSQL dummy localhost:1; chặn `BaseDatabaseWrapper.ensure_connection` trước Django setup nên **mọi kết nối database đều bị từ chối**. Không dùng URL/credential production, không kết nối Render hoặc SQLite thật và không tải mô hình trong kiểm đóng gói.

Kết quả: **7 static files copied, 14 post-processed**, system check không lỗi. Đã kiểm đủ manifest, URL static có tên hash, tệp tồn tại và bản gzip giải ra khớp byte cho cả bảy tài nguyên. CSS đã collect có phần mẫu/hướng dẫn mới; output không có database, dataset, model, Python hay credential.

| Nguồn | Tên đóng gói |
|---|---|
| `css/app.css` | `css/app.513f231b616d.css` |
| `js/money.js` | `js/money.f8ad2307326e.js` |
| `js/quick-entry.js` | `js/quick-entry.7b921d3d69b2.js` |
| `js/transaction-form.js` | `js/transaction-form.93fd08bdff76.js` |
| `js/transaction-filters.js` | `js/transaction-filters.08166be8015f.js` |
| `js/form-feedback.js` | `js/form-feedback.23a41e39df0d.js` |
| `img/brand.svg` | `img/brand.749d6337c5ed.svg` |

CSS SHA-256: `2c05d6cd3a380be066b15968a8611e66d746f1d7255a428047974f46a93d2302`. Bằng chứng ngoài Git: `handoff-collectstatic.log`, `handoff-static-report.json`, script/settings QA và các tệp audit trong thư mục handoff. Đây là kiểm production static trên **Windows**, chưa phải build Linux hoặc kiểm UI online sau push.

Đã xác minh GitHub đúng tài khoản **thiennamm**, repository **thiennamm/khoa_luan_tai_chinh_ca_nhan** vẫn **Private**, giữ main/remote/quyền truy cập và không force-push. Commit chỉ gồm 15 tệp TASK 18B, không chứa cấu hình/dữ liệu QA. Kết quả commit, SHA local/remote và working tree được kiểm sau push, báo trong tin nhắn cuối; không nhúng SHA của chính commit vào nội dung tệp. Push main có thể kích hoạt auto-deploy theo cấu hình hosting, nhưng task không kết nối hoặc kiểm chứng production.

## Liên kết nhãn sau khi thêm mẫu — TASK 19A

Bộ 11 mẫu và 4 mục chưa ánh xạ giữ nguyên. Trang Thêm/Sửa danh mục nay dùng nhãn **Liên kết với nhãn mô hình — tùy chọn**, lựa chọn **Chưa ánh xạ** rõ ràng, hướng dẫn phạm vi đủ 17 mã và thông báo trung tính nếu có danh mục cùng loại/cùng nhãn. Không ánh xạ lại danh mục cũ. Hướng dẫn và bằng chứng mới tại [category-mapping-help.md](category-mapping-help.md).
