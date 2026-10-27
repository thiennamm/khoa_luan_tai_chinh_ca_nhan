# TASK 19D — Kiểm thử tích hợp đợt 19A–19C

Ngày kiểm chứng: **27/10/2026**, giờ Việt Nam. Dự án chính: `D:\KHÓA LUẬN TỐT NGHIỆP`. Đọc và giữ nguyên nội dung đã làm của [19A](category-mapping-help.md), [19B](monthly-report.md), [19C](interaction-accessibility.md).

**Kết luận QA:** chưa phát hiện lỗi chặn còn lại trong phạm vi dưới đây. Đây không phải xác nhận website production đã đạt. **Tại thời điểm kết thúc TASK 19D, chưa stage/commit/push/deploy.** Việc chốt mã theo yêu cầu tiếp theo được ghi ở mục cuối; các ghi chú chưa commit trong tài liệu 19A–19C là trạng thái tại thời điểm bàn giao từng task.

## Môi trường và cách ly dữ liệu

| Thành phần | Đã xác minh |
|---|---|
| PostgreSQL | Portable **18.6**, `server_version_num=180006`, chỉ nghe `127.0.0.1:55432` |
| Cluster | `D:\POSTGRESQL QA\rehearsal-20261023\data-attempt2`; system identifier `7699798773140758112` |
| Database ứng dụng | **`qa_release19_20261027`**, mới tạo, UTF8, collation/ctype **C/C**; không dùng database đã phục hồi chứa dữ liệu cũ |
| Database kiểm thử | **`qa_release19_suite`**, tạo/xóa bằng Django; đã xác minh bị xóa sau suite |
| Website | Waitress, DEBUG=False, `http://127.0.0.1:8004`; settings, cookie và secret riêng |
| Runtime | Python **3.13.16**, Django **5.2.18**; môi trường QA có sẵn `D:\POSTGRESQL QA\application-16e-20261024\.venv`, không cài dependency |
| Trình duyệt | Edge Chromium headless qua Playwright, **1280×900** và **390×844**, múi giờ Việt Nam |
| Bằng chứng riêng | `D:\POSTGRESQL QA\release19-20261027` — ngoài repository, không đưa vào static/public/Git |

Đối chiếu cluster bằng `pg_controldata` trước khi khởi động, sau đó bằng SQL kiểm host/port/database/system identifier/data directory/listen address. Mỗi kết nối và mỗi request QA đều có chốt kiểm tra đích; xóa các biến môi trường PG/DATABASE_URL thừa trước khi cấu hình. Role ứng dụng không có quyền superuser/tạo database. Test runner dùng role quản trị **QA** để tạo database test riêng.

Credential QA cũ đã bị dọn từ đợt trước: đặt lại mật khẩu ngẫu nhiên của role quản trị **cluster QA** khi server đang dừng; không dùng hoặc đọc URL/credential Render. Không kết nối production, không mở SQLite thật bằng Django. Hai tài khoản mới đăng ký bằng UI và toàn bộ danh mục/giao dịch trong database mới đều là dữ liệu mô phỏng. Không đổi tài khoản đã phục hồi. Bản dump/cluster cũ không vào Git.

## Lỗi phát hiện và phần sửa trong 19D

### 1. Tìm kiếm Unicode trên PostgreSQL

Lượt đầu chạy toàn bộ **394 bài** trên PostgreSQL ghi nhận **6 failure subcase và 1 error** (giữ log ban đầu). Các ca bộ lọc/xuất CSV cho thấy tìm hoa/thường tiếng Việt không khớp khi database có collation C. Không đổi locale QA để che lỗi.

Sửa `finance/transaction_filters.py`: trên PostgreSQL 18+, dùng `CASEFOLD(... COLLATE pg_unicode_fast)` cho mô tả và chuỗi tìm; vẫn dùng queryset đã giới hạn tài khoản, `contains` và thứ tự ngày/ID cũ. Nhánh SQLite dùng Python casefold giữ nguyên. Thêm một bài kiểm Unicode đầy đủ, giữ dấu và tách tài khoản trong `finance/test_transaction_filters.py`. Qua UI mobile, chuỗi hoa `ĐÓNG HỌC PHÍ` tìm đúng một giao dịch của tài khoản A.

Không thay schema, extension, dữ liệu hoặc chính sách bộ lọc. Nhánh này đã kiểm trên PostgreSQL 18.6 UTF8; backend cũ hơn 18 còn giữ `icontains`, chưa được xác minh Unicode tương đương. Căn cứ: [collation PostgreSQL 18](https://www.postgresql.org/docs/18/collation.html), [casefold](https://www.postgresql.org/docs/18/functions-string.html).

### 2. Kỳ vọng kiểm thử ngân sách khác backend

`finance/test_budgets.py` trước đó đòi mọi đầu vào sai qua `bulk_create` đều gây `IntegrityError`. PostgreSQL `NUMERIC(15,0)` có thể làm tròn `1.5` thành `2` trước CHECK; tràn precision gây `DataError`. Đây là kỳ vọng sai của bài kiểm thử, không phải bằng chứng form đang cho lưu tiền lẻ.

Bài kiểm thử nay xác minh đường lưu model chuẩn từ chối số lẻ bằng `ValidationError`; kiểm riêng hành vi ép kiểu của raw `bulk_create` trong transaction luôn rollback; chấp nhận đúng hai loại lỗi từ chối dữ liệu tại DB. **Không sửa model, form tiền, giá trị tiền hoặc quy tắc làm tròn.** Không tuyên bố CHECK có thể phát hiện số lẻ gốc sau khi NUMERIC đã ép kiểu; đường ghi được hỗ trợ vẫn cần validation. Căn cứ: [PostgreSQL NUMERIC](https://www.postgresql.org/docs/18/datatype-numeric.html).

Các lần lỗi harness QA (sai tên nút đăng ký, kỳ vọng định dạng/chuỗi lỗi HTML 500, đếm nhầm receipt tạo mục tiêu cùng receipt đóng góp) được sửa ở công cụ ngoài repository, không coi là lỗi sản phẩm. Lần EN bổ sung đã lưu thành công trước khi harness chờ nhầm thông báo; xác minh DB rồi chỉ chạy lại phần mô phỏng 500, không gửi lại giao dịch EN.

## Luồng tích hợp đã thử

| Luồng | Bằng chứng và kết quả thực tế |
|---|---|
| Đăng ký → đăng nhập → bộ mẫu | Hai tài khoản A/B đăng ký qua UI; không tự đăng nhập, trang bảo vệ chuyển tới đăng nhập; đăng nhập bằng Enter; tự chọn/xác nhận đủ 11 danh mục. Chưa có giao dịch sau thêm bộ mẫu |
| Chưa ánh xạ | Dùng danh mục Ăn uống chưa ánh xạ, nhập/lưu giao dịch **30.000 VND** thành công |
| Ánh xạ trùng | Thêm danh mục Education thứ hai của A vẫn được lưu; thông báo chỉ hiện danh mục A, không có tên riêng của B. Enter trên nút kiểm tra giữ đúng `action=preview_mapping`, chưa lưu |
| Đổi tên | Cảnh báo đổi tên hiện trước khi lưu. Education ID **7** giữ nguyên; giao dịch ID **2** vẫn liên kết ID 7. Snapshot phản hồi VI trước/sau giữ nguyên từng trường |
| Nhập nhanh → VI/EN | Parser thật điền form; suy luận thật qua hai artifact hiện có. Sửa mô tả, loại hoặc chế độ xóa receipt cũ. Chủ động Apply → Save tạo phản hồi VI; lượt EN riêng cũng Apply → Save tạo phản hồi EN. Không gọi kết quả ví dụ là đánh giá chất lượng ML |
| Gửi lại có receipt | POST lại lựa chọn 11 mẫu trước khi đổi tên: tạo 0, bỏ qua 11. POST lại receipt ML đã dùng: trả đúng giao dịch, không thêm phản hồi. Các kiểm tra gửi lại này là HTTP riêng, không giả là bấm UI |
| CSV | Upload → xem trước → xác nhận thật, một giao dịch mới; POST xác nhận lại nhận 409. Báo cáo tháng 9 tăng từ 35 lên **36** dòng đúng một lần |
| Báo cáo ↔ Tổng quan | Cùng tháng, tổng thu/chi/chênh lệch và cơ cấu danh mục khớp DOM Tổng quan, dịch vụ và SQL. Toàn bộ 36 chi tiết hiện trong báo cáo, không bị cắt ở 20 dòng |
| Tiết kiệm/định kỳ dự kiến | Tạo mục tiêu, đóng góp và quy tắc chưa ghi nhận qua UI; tổng thu–chi giữ nguyên trước/sau. Cuối QA có 3 đóng góp tổng **130.000 VND**, không tạo Transaction; quy tắc chưa có occurrence |
| Phân quyền | B mở báo cáo kèm `user_id` giả vẫn chỉ có khoản của B. HTTP kiểm URL giao dịch/danh mục/mục tiêu của A trả 404 cho B. HTML/PDF báo cáo A không có marker riêng của B |
| Lỗi validation thật | Tiền `50,00` bị backend từ chối, giữ input; nút không kẹt pending, tóm tắt nhận focus và Enter trên link đưa tới ô tiền |
| Bàn phím/mobile | Tab → bỏ qua điều hướng → main; Enter mở/đóng menu/details, thao tác nút/form và link lỗi. Mobile báo cáo cuộn bảng trong vùng riêng, không tràn ngang toàn trang |
| JavaScript tắt | Nhập và lưu giao dịch thủ công trên mobile thành công; không coi nhập nhanh/ML là hoạt động khi tắt JS. Luồng category preview không JS còn được kiểm bằng suite và bằng chứng 19A/19C |
| Back/Forward | Sau lỗi mạng giả lập, quay lại/tiến tới không còn nút bị kẹt busy. Không cam kết giữ bản nháp nếu browser tải lại document; test JS kiểm riêng `pageshow.persisted` |

Đối chiếu DB cuối: A **40** giao dịch (tháng 8: 1; tháng 9: 36; tháng 10: 3); B **1** giao dịch. Hai phản hồi VI/EN đều có Apply/cùng nhãn trong **ví dụ QA này**, không dùng làm tỷ lệ chất lượng. Có 1 receipt CSV/1 dòng nhập, 4 operation tiết kiệm (1 tạo mục tiêu + 3 đóng góp), 0 occurrence định kỳ, 0 kết quả/lịch sử dự báo và không tự xác nhận coverage. Số liệu này chỉ mô tả fixture QA, không thuộc dữ liệu người dùng thật.

## Lỗi mạng, server và bấm lặp: phân biệt cách kiểm

- Hai lần kích hoạt nút bằng `button.click()` trong DOM, qua validation/submit thật: **1 POST**, có `aria-busy`, `aria-disabled`; không vô hiệu nút native làm mất name/value. Không gọi đây là thử hai ngón tay trên thiết bị thật.
- POST lại **cùng operation token** tiết kiệm: cùng kết quả, không thêm khoản. Hai operation khác mã hợp lệ vẫn được chấp nhận. Các ca tranh chấp backend có trong suite PostgreSQL, không thay bằng chặn nút.
- **Route abort giả lập** trước Django cho nhập nhanh: thông báo chưa có kết quả, giữ trường, khôi phục nút.
- **HTML HTTP 500 giả lập**: UI không hiển thị nội dung diagnostic giả, giữ form, khôi phục nút; không phải lỗi server production. JS suite kiểm thêm response JSON lỗi và redirect.
- **Timeout giả lập mạng**: giữ request không tới Django, chờ timer client thật 20 giây; một request, không retry.
- **Mất response giả lập sau commit thật**: proxy kiểm thử nhận 302 từ server/DB QA rồi abort response tới browser. Không tự retry; kiểm danh sách thấy đúng khoản đóng góp **20.000 VND** đã lưu, tổng phân bổ 130.000 VND. Không thông báo chắc chắn “lưu thất bại”.
- CSRF thiếu token nhận **403** qua HTTP riêng. Không có sự cố production nào được quan sát hay suy ra từ các ca giả lập này.

## PDF thực tế và đối chiếu số liệu

PDF được tạo bằng **Chromium `page.pdf`**, A4 theo CSS, không nền, header/footer của browser tắt. Đây là file PDF thật từ browser engine, **khác kiểm hộp thoại Save as PDF thủ công**. Công cụ đọc/render PDF dùng runtime QA bên ngoài, không thêm dependency website.

| PDF QA ngoài Git | Số trang | Nội dung đối chiếu |
|---|---:|---|
| `qa-postgresql-short.pdf` | **1** | Tháng 08/2026, không chi tiết; 1 giao dịch, thu 0, chi **30.000 VND**, chênh lệch **-30.000 VND** |
| `qa-postgresql-long.pdf` | **4** | Tháng 09/2026, đủ **36** chi tiết; thu **45.000.000 VND**, chi **1.000.000.001.992.999 VND**, chênh lệch **-999.999.956.992.999 VND** |

Khoản cực lớn là dữ liệu mô phỏng có chủ đích để kiểm Decimal và dàn trang. Đếm đủ 33 marker chi, 2 marker thu và 1 dòng CSV, không lặp/mất; tách cột tiền/loại từ PDF để cộng lại bằng Decimal: thu 45.000.000, chi 1.000.000.001.992.999, khớp SQL, dịch vụ, Tổng quan và HTML. Kiểm cả số dòng/tổng, không chỉ nhìn ảnh.

Đã render và **xem trực quan cả 5 trang** ở `pdf-short-page-01.png` và `pdf-long-page-01.png` đến `04.png`: đủ cột, chữ dài xuống dòng, không có trang trắng bất thường, không cắt số lớn, tiêu đề bảng chi tiết lặp ở trang 2–4. Cảnh báo coverage, nguồn và VND còn; không có sidebar/nút/thông tin đăng nhập. Kiểm tọa độ chữ trong lề và nội dung không rỗng. Chưa thử máy in vật lý hoặc hộp thoại Save as PDF thủ công.

## Kiểm tra kỹ thuật sau sửa

| Kiểm tra | Kết quả cuối | Bằng chứng ngoài Git |
|---|---|---|
| Toàn bộ suite Django trên PostgreSQL QA | **395/395 đạt**, 163,079 giây; **không bỏ qua bài nào** | `django-postgresql-final.log` |
| Bộ lọc + export + ngân sách PostgreSQL | **34/34 đạt** | `postgresql-related-fix.log` |
| Cùng nhóm trên SQLite bộ nhớ riêng | **34/34 đạt** | `sqlite-related.log` |
| Suite JavaScript | **43/43 đạt**, không skip | `javascript.log` |
| Django system check | **0 lỗi, 0 silenced** | log suite và `handoff-static-report.json` |
| `migrate --check` | Không có migration chờ trên QA | Thực hiện bằng `manage_qa.py`, exit 0 |
| `makemigrations --check --dry-run` | **No changes detected** | Thực hiện bằng `manage_qa.py`, exit 0 |
| Production QA `collectstatic` | **10 tệp copied, 20 postprocessed**; manifest, URL hash và gzip của CSS/JS/icon kiểm đúng | `static-run.log`, `handoff-static-report.json` |

Nhóm 34 PostgreSQL là **tập con** của 395; 34 SQLite là lượt bổ sung cùng nhóm, không cộng thành số bài khác nhau. Không cộng lại số kiểm thử từ tài liệu 19A/B/C. Sau sửa mới có thêm 1 bài nên suite từ 394 thành 395; các lỗi ban đầu đã được chạy lại và đạt. Các bài đồng thời trong suite chạy trên PostgreSQL QA thật; không có bài bị gắn skip vì Windows.

Static dùng `config.render`, DEBUG=False, storage WhiteNoise manifest, override QA ngoài repository. Đích DB giả localhost:1 và chặn `ensure_connection`, do đó collectstatic/check cấu hình này không thể chạm DB production. Đây là kiểm đóng gói trên Windows, không phải đã build Linux hoặc deploy Render.

## Rà diff và bảo toàn

- Giữ nguyên hash **cả 43 tệp** thay đổi đã có ở đầu TASK 19D (19A–19C). Không reset/ghi đè. Những sửa mới của 19D: `finance/transaction_filters.py`, `finance/test_transaction_filters.py`, `finance/test_budgets.py`, cập nhật `docs/transaction-filters.md`, thêm biên bản này.
- Đã rà các đường query/report/category preview, escape HTML/`json_script`/`textContent`, JS pending/fetch/revoke, print CSS và các bài kiểm thử. Không sửa models/migrations, config production, dependency, artifact/hash mô hình hoặc thí nghiệm.
- Git chỉ có mã/template/CSS/JS, script kiểm thử và tài liệu phù hợp; không stage DB, dữ liệu, PDF/ảnh QA, session, credential hoặc config QA. Rà cả tệp tracked, diff và tệp mới; không có credential thật hoặc payload tài chính riêng được bổ sung. `git diff --check` đạt.
- SQLite thật SHA-256 giữ nguyên: `6f369683527616ba24559d00535f6b217d2d580e587ec86f80085811f4afb6dc`.
- Model EN giữ nguyên: `362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345`.
- Model VI giữ nguyên: `19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55`.

Không thay dữ liệu thật, không migrate SQLite thật/production, không chạy lại thí nghiệm ML. Schema QA đã áp dụng các migration hiện có đến 0013; các constraint public đều validated. Không cần migration mới.

## Bằng chứng, dọn QA và giới hạn

Tất cả đường dẫn tương đối trong mục bằng chứng dưới đây tính từ **`D:\POSTGRESQL QA\release19-20261027`**:

- `registration-ui.json`, `integration-phase1.json`, `integration-phase2.json`, `financial-acknowledgement-ui.json`, `english-save-and-http500.json`, `unicode-search-ui.json`.
- Ảnh: `desktop-rename-warning.png`, `desktop-report-current.png`, `desktop-long-report.png`, `desktop-simulated-http500.png`, `mobile-report.png`, `mobile-network-simulation.png`, `mobile-unicode-filter.png`; ảnh render PDF như trên.
- `pdf-check.json`, `final-verification.json`, `database-identity.json`, log kiểm thử/static, `shutdown-report.json`, `evidence-manifest.json` (kích thước/SHA-256).
- Công cụ tái chạy/harness, bản so sánh snapshot/report chi tiết chỉ nằm ngoài Git. Fixture có nhãn QA và dữ liệu tự tạo; không dùng các JSON/PDF riêng này làm tài liệu public của tài khoản thật.

**Đã dừng website 8004 và PostgreSQL 55432**, kiểm cả hai cổng đóng và `postmaster.pid` không còn. Xóa `credentials.json`, hai file session trình duyệt và body POST tạm; quét các tệp text còn lại trong thư mục QA không thấy các mật khẩu/secret tạm đó. Cluster QA giữ verifier và dữ liệu mô phỏng, không còn file mật khẩu plaintext; không xóa cluster/bằng chứng cũ.

Chưa kiểm: Linux/Render sau deploy, trình duyệt ngoài Edge Chromium, thiết bị điện thoại vật lý, screen reader, WCAG toàn diện, máy in/hộp thoại in thủ công, tải lớn, mọi tổ hợp request đồng thời. Viewport và mạng giả lập không chứng minh hành vi mạng/thiết bị thật. Back/Forward có thể tải lại trang và mất bản nháp theo browser; không thêm lưu dữ liệu tài chính vào storage. Report đọc dữ liệu hiện có, không cam kết snapshot nhất quán giữa nhiều truy vấn khi có người ghi đồng thời.

## Checklist online sau khi người dùng duyệt và deploy

Chỉ dùng hai tài khoản **thử mới**, ghi rõ dữ liệu mô phỏng; không dùng tài khoản/dữ liệu thật. Không đưa credential hay báo cáo riêng vào Git.

1. Kiểm Dashboard/log để xác nhận commit, Python/dependency giữ nguyên, PostgreSQL **18 UTF8**; build/static thành công. Không suy Deploy Live thành mọi mục dưới đây đạt.
2. Đăng ký → trang đăng nhập/thông báo thành công; trang bảo vệ vẫn yêu cầu đăng nhập. Đăng nhập rồi chọn danh mục mẫu, xác nhận chỉ thêm cấu hình đã chọn.
3. Tạo danh mục chưa ánh xạ, ánh xạ trùng; thông báo chỉ thuộc tài khoản. Đổi tên danh mục có giao dịch, kiểm cảnh báo, liên kết giao dịch và snapshot phản hồi cũ.
4. Nhập nhanh → kiểm form → VI và EN → Apply → tự Save. Đổi mô tả/loại/chế độ không dùng được gợi ý cũ. ML lỗi vẫn nhập tay được; không diễn giải ví dụ là chất lượng mô hình.
5. Tìm mô tả tiếng Việt hoa/thường, phối hợp loại/tháng/danh mục; thử qua trang và xuất CSV. Kiểm báo cáo tháng, Tổng quan, cơ cấu và chi tiết hơn 20 dòng khớp.
6. Dùng tháng thử không có dữ liệu và tháng chưa xác nhận; giữ cảnh báo. Định kỳ chưa ghi nhận/phân bổ tiết kiệm không cộng vào thu–chi. Không tự xác nhận coverage/tính dự báo khi xem báo cáo.
7. Trên desktop và mobile, thử Tab/Enter, lỗi form giữ input/focus, không kẹt nút sau Back/Forward. Khi mất kết nối, kiểm danh sách trước khi gửi lại, không tự retry thao tác tài chính.
8. In QA ngắn/nhiều trang bằng hộp thoại Save as PDF của máy người dùng; kiểm đủ dòng/tổng/cảnh báo. Không chia sẻ PDF tài chính ngoài ý muốn.
9. B đăng nhập kiểm chỉ thấy dữ liệu/báo cáo của B; URL ID của A bị từ chối. Ghi kết quả online riêng, không đánh dấu đạt trước khi thực hiện.

## Chốt mã đợt 19A–19D — 27/10/2026

Theo yêu cầu phát hành của người dùng, rà đủ **48 tệp** thay đổi tích lũy, gồm các tệp mới chưa theo dõi và bản sửa Unicode PostgreSQL. Giữ nguyên 43 tệp đã có từ đầu 19D; không reset/ghi đè. Tài liệu này chỉ được bổ sung trạng thái bàn giao; không sửa mã sau lượt suite cuối.

- Kiểm lại `makemigrations --check --dry-run`: **No changes detected**; system check **0 issues**, bằng cấu hình QA dùng SQLite `:memory:`. Không mở database thật hoặc khởi động lại PostgreSQL; đây không phải lượt kiểm migration production.
- Giữ kết quả cuối **395/395 PostgreSQL**, **43/43 JavaScript**, **34/34 SQLite bổ sung**; không chạy lại toàn bộ khi mã không đổi và không cộng trùng các nhóm.
- Đối chiếu hash SQLite thật và EN/VI vẫn nguyên; rà tệp tracked, diff và tệp mới không đưa database, model, credential, cấu hình QA hoặc PDF/ảnh riêng vào Git. Các URL giả được máy quét phát hiện chỉ thuộc ba tệp kiểm thử có sẵn, không phải bí mật mới. `git diff --check` đạt.
- Xác minh GitHub đúng **thiennamm**, repository **thiennamm/khoa_luan_tai_chinh_ca_nhan** vẫn **Private**, remote giữ nguyên, nhánh **main**. Commit và push thông thường theo yêu cầu, không force-push. SHA của commit được xác minh sau push và báo ở tin nhắn bàn giao, không nhúng SHA của chính commit vào tài liệu.
- Chưa kiểm kết quả triển khai online của commit này, không kết nối database production. Push có thể kích hoạt auto-deploy đã cấu hình ở hosting; chỉ đánh dấu checklist online khi có bằng chứng kiểm riêng.

Bằng chứng chốt mã tiếp tục nằm ngoài Git trong thư mục QA: `release-offline-check.log`, `release-github-identity.json`, `release-security-review.json`, `release-push-verification.json`.
