# TASK 20B — Lịch thu–chi theo tháng

Ngày thực hiện **27/10/2026**, dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`. Đã đọc giao dịch, dịch vụ tổng hợp Decimal, định kỳ/hiệu lực, quyền và template dùng chung. Không có AGENTS.md trong repository. **Không thay schema, model ML, dependency hoặc dữ liệu thật.** Giai đoạn QA chưa commit/push/deploy; phần chốt mã theo yêu cầu tiếp theo ở mục cuối.

## Cách dùng và ý nghĩa dữ liệu

1. Vào **Ghi chép → Lịch thu–chi**. Mặc định tháng hiện tại theo Asia/Ho_Chi_Minh; chọn tháng hoặc dùng Tháng trước/sau/hiện tại. Chuyển năm, tháng 2 và năm nhuận được xử lý bằng ngày lịch.
2. Desktop: bảng 7 cột bắt đầu **Thứ Hai**; ngày ngoài tháng làm nhạt, không lấy dữ liệu tháng bên cạnh vào tổng. Hôm nay có nhãn chữ và viền. Mobile ≤760px mặc định danh sách ngày, không ép 7 cột.
3. Tổng ngày/tháng là **thu/chi đã ghi nhận** từ Transaction, tiền Decimal và filter VND dùng chung. Không phải số dư ngân hàng hoặc lịch sử đã được chứng minh đầy đủ. Ngày trống hiển thị số đã ghi là 0, không biến thành xác nhận không có chi hoặc zero hợp lệ cho dự báo.
4. Giao dịch **ngày tương lai đã lưu** vẫn được tính trong tổng đã ghi, có nhãn tại ô/ngày/chi tiết; không tự sửa ngày, loại bỏ hoặc đổi chính sách ngày của CRUD/CSV.
5. Mỗi ngày có tối đa **3 mục xem trước**, ưu tiên giao dịch mới nhất theo ID rồi khoản dự kiến. Số đếm thu/chi và số khoản dự kiến vẫn tính đầy đủ; một khoản dự kiến có thể nằm trong **Xem thêm**. Bấm ngày để xem đủ, không cắt thiếu giao dịch.
6. Trang ngày có hai danh sách riêng: giao dịch đã ghi và định kỳ dự kiến, mỗi danh sách **20 dòng/trang**. Chuyển trang giữ trang của danh sách còn lại. Tổng thu/chi luôn tính toàn bộ giao dịch ngày, không chỉ trang đang xem. Mô tả đầy đủ xuống dòng/escape; xem trước chỉ giới hạn hiển thị bằng CSS.
7. Ngày/tháng không có bản ghi ghi rõ **Không có giao dịch được ghi nhận**, không khẳng định không phát sinh thu/chi. Coverage của chính tài khoản vẫn hiển thị; không tự xác nhận tháng.

## URL, phân quyền và cache

| URL | Hành vi |
|---|---|
| GET `/lich-thu-chi/?month=YYYY-MM` | Thiếu month dùng tháng Việt Nam hiện tại; có month rỗng/sai trả **400**, giữ lỗi, không trả tổng/lịch tháng khác |
| GET `/lich-thu-chi/ngay/YYYY-MM-DD/?page=1&plans_page=1` | Ngày lịch hợp lệ đúng định dạng; sai ngày trả **404**; tháng được suy từ ngày trên URL |

Cả hai chỉ GET, yêu cầu đăng nhập; POST trả 405, không có nhánh ghi dữ liệu. Mọi queryset giao dịch lọc `user=request.user` và category cùng tài khoản; định kỳ/coverage cũng theo request.user. Không nhận user_id từ query làm chủ dữ liệu. Các URL chi tiết giao dịch/định kỳ tiếp tục kiểm quyền bằng luồng hiện có. Header phản hồi có **private/no-store** qua `never_cache`, không có cache dữ liệu riêng dùng chung.

Phạm vi năm 0001–9999: điều hướng vượt biên bị ẩn, các ô lưới vượt phạm vi date được để trống; không cộng/trừ ngày gây overflow. Không có JavaScript mới: form GET, liên kết, menu/details gốc và nội dung tài chính vẫn dùng khi tắt JS. Dùng icon SVG local, nhãn chữ Thu/Chi/Dự kiến và màu, focus bàn phím dùng CSS chung. Không thêm CDN/font hoặc thư viện lịch.

## Định kỳ: dùng lại quy tắc hiện có

`plans_for_month` dùng `recurring.window()` và **`recurring.monthly_items` → `item/planned`**. Không viết lại thuật toán hiệu lực, pause/resume hoặc ngày đến hạn. Ngày 31 trong tháng ngắn chuyển về ngày cuối tháng theo dịch vụ cũ. Kích hoạt lại có hiệu lực tháng sau, không tạo bù tháng đã dừng; thay đổi thông tin theo revision tháng sau; occurrence đã xử lý giữ snapshot.

- Chỉ các trạng thái `due`/`upcoming` được trình bày như **Dự kiến**, chưa cộng vào thu/chi. Ngày tương lai của một kỳ đang trong tháng hiện tại vẫn có thể mở xác nhận như luồng định kỳ hiện có; người dùng tự xác nhận khoản đã thực sự phát sinh.
- Kỳ recorded không tiếp tục là khoản chưa trả ở ngày đến hạn. Giao dịch xuất hiện theo ngày thực tế, kể cả khác tháng đến hạn. Trang ngày/chi tiết ghi tháng kỳ, ngày đến hạn và giải thích chỉ tính một lần theo ngày thực tế.
- Kỳ skipped/deleted không tự hiện trở lại như khoản cần trả. Có thông tin tổng hợp trạng thái trong phần mở rộng và liên kết sang Định kỳ; mở lại kỳ vẫn cần luồng xác nhận cũ.
- **Ghi nhận** là liên kết tới GET biểu mẫu xác nhận hiện có; GET đó không tạo giao dịch. Chỉ POST xác nhận hợp lệ trong luồng cũ mới ghi. Lịch không gọi `recurring.process`.
- Giữ phạm vi **12 tháng đến tháng hiện tại + xem trước tháng sau**. Ngoài phạm vi không gọi dịch vụ lấy dự kiến và hiện cảnh báo rõ, không suy không có khoản đến hạn. Giao dịch thực tế vẫn xem được ở mọi tháng hợp lệ.

Khoản tiết kiệm không thuộc Transaction nên không cộng; không suy luận ML, tạo feedback, đổi ngân sách, coverage, forecast version hoặc lịch sử dự báo khi xem lịch.

## Truy vấn và độ chính xác

- Tách phép cộng Decimal hiện có thành `services.recorded_totals`, `monthly_totals` dùng lại helper này. Lịch nhóm các tuple ngày/kind/amount của **đúng tháng đang xem**, cộng bằng Decimal; không dùng SUM NUMERIC/float trên SQLite để tránh làm tròn tổng lớn. Tổng tháng tính từ cùng tổng ngày, không có nguồn số liệu biểu đồ/bảng khác nhau.
- Xem trước dùng SQL **ROW_NUMBER partition theo ngày, ID giảm dần, rank ≤3**, join category và OneToOne occurrence trước; tối đa 93 bản ghi mô tả trong một tháng 31 ngày. Không tải toàn bộ mô tả của tháng rồi cắt bằng Python, không tải lịch sử giao dịch toàn tài khoản.
- `recurring.monthly_items` nay prefetch **một revision có hiệu lực gần nhất cho mỗi rule**, dùng ROW_NUMBER theo rule, lọc effective_month ≤ tháng xem. Vẫn để hàm `planned` cũ quyết định nội dung; occurrence vẫn ưu tiên snapshot. Không lấy toàn bộ lịch sử revision hoặc một truy vấn cho mỗi rule. Các view định kỳ dùng `monthly_items` cũng nhận tối ưu này; dashboard/quy tắc/lịch sử khác giữ truy vấn riêng như trước.
- Trang ngày chỉ lấy tuple số tiền của ngày, COUNT phân trang và tối đa 20 Transaction có join; định kỳ dùng cùng dịch vụ. Các DTO đưa cho template đã có thông tin cần dùng, không dereference category/rule trong từng ô để gây N+1.
- Không nhận đường dẫn, ghi file dữ liệu, tạo kỳ chờ hay dùng session để lưu bản sao giao dịch. Không thêm log mô tả hoặc dữ liệu cá nhân.

**Đo PostgreSQL 18.6 QA thật**, request qua Django Client gồm session/auth thông thường:

| Tập QA của một tài khoản | Trang tháng | Trang ngày |
|---|---:|---:|
| 1 giao dịch, 1 quy tắc; ngày chọn chưa có giao dịch | **8 truy vấn** | **8 truy vấn** |
| 41 giao dịch, 16 quy tắc; ngày chọn có dữ liệu | **8 truy vấn** | **9 truy vấn** |

Một SELECT trang dữ liệu được thêm khi ngày có giao dịch; không tăng theo mỗi ô/giao dịch/quy tắc. Kiểm bổ sung một rule có **13 revision** (có revision tương lai): chỉ prefetch **1 revision có hiệu lực**, không lấy tương lai; số truy vấn tháng/ngày vẫn **8/9**. Tổng chi ngày cộng lại bằng tổng tháng và dịch vụ cũ (**4.100 VND** trong fixture đo PostgreSQL). Capture SQL các GET không có INSERT/UPDATE/DELETE. Guard kiểm đích mỗi kết nối vẫn bật; không tính SELECT bổ sung của middleware giám sát QA vào chi phí middleware sản phẩm.

Số truy vấn ổn định **không phải** bằng chứng thời gian xử lý cố định: vẫn quét tuple của tháng và các rule của tài khoản, tính toàn bộ kế hoạch tháng để đếm/phân trang trong bộ nhớ. Chưa benchmark tập rất lớn, nhiều worker hoặc mọi trường hợp ghi đồng thời. Báo cáo gồm nhiều lần đọc, không phải snapshot bất biến; dữ liệu thay đổi trong lúc duyệt thì tải lại.

## Kiểm thử sau thay đổi cuối

| Kiểm tra | Kết quả | Bằng chứng ngoài Git |
|---|---|---|
| Hồi quy toàn bộ Django trên PostgreSQL QA | **435/435**, 186,375 giây, không skip | `postgresql-regression-final.log` |
| Lịch + định kỳ PostgreSQL | **55/55**, 15,550 giây | `postgresql-related-window-final.log` |
| Cùng nhóm trên SQLite test memory riêng | **55/55**, 14,347 giây | `sqlite-related-final.log` |
| JavaScript hồi quy (không sửa JS) | **43/43** | `javascript.log` |
| System check, makemigrations dry-run | **0 issues; No changes detected** | Các log QA và kiểm cuối |
| Production QA collectstatic | **11 copied, 22 postprocessed**; manifest/URL hash/gzip CSS/JS/icon đúng | `handoff-static-report.json`, `collectstatic-final.log` |

19 bài lịch mới đã nằm trong 435 và nhóm 55; nhóm 55 PostgreSQL là tập con của 435, SQLite là lượt bổ sung cùng nhóm. Không cộng trùng các lượt hoặc số bài trước tinh chỉnh. Full suite chạy sau thay đổi chung `recurring.monthly_items` cuối, không chạy lại thí nghiệm ML.

Các ca mới kiểm: tháng sai/rỗng, ngày sai; mặc định/ranh giới 17:00 UTC sang ngày Việt Nam; tuần thứ Hai, ngoài tháng, đầu/cuối tháng, năm nhuận, chuyển năm và biên 0001/9999; tổng Decimal lớn khớp danh sách/dịch vụ cũ; giao dịch tương lai; tháng/ngày trống và coverage chưa xác nhận; cửa sổ định kỳ; ngày 31/2; pause/resume; recorded/skipped/deleted; ngày thực tế khác tháng đến hạn không đếm đôi; revision cũ/mới; link mở xác nhận không ghi; 46 giao dịch và 25 dự kiến/ngày, hai phân trang; chuỗi HTML/tên/mô tả dài; hai tài khoản; GET bảo toàn toàn bộ bảng finance; số truy vấn khi tăng dữ liệu. Các bài định kỳ cũ vẫn kiểm xử lý/khóa/chống trùng.

Trong QA đã xử lý:

- Một failure ngưỡng truy vấn do middleware identity QA thêm SELECT riêng. Loại riêng middleware phụ khỏi profile đo sản phẩm, **giữ guard mỗi kết nối**; không nới ngưỡng bài kiểm hay bỏ bài.
- Thử prefetch có slice ban đầu gây `Cannot filter a query once a slice has been taken` trong Django. Sửa bằng prefetch queryset window/rank không slice; nhóm 55 và toàn suite 435 sau sửa đạt. Đây là lỗi phát hiện trong phát triển QA, chưa phát hành.
- CSS dl dùng chung làm ô lịch thừa khoảng trống; giới hạn padding/border riêng trong CSS lịch, chỉnh thẻ tổng mobile thành hai cột và thẻ số mục hàng riêng; không đổi tổng tiền. Kiểm lại UI/ảnh cuối sau sửa.

## QA giao diện và bảo toàn dữ liệu

Thư mục riêng: **`D:\POSTGRESQL QA\task20b-20261027`**. Website QA **127.0.0.1:8022**, SQLite mới **`qa.sqlite3`**, hai tài khoản ngẫu nhiên, dữ liệu mô phỏng và banner QA. PostgreSQL dùng cluster localhost TASK 16 `D:\POSTGRESQL QA\rehearsal-20261023\data-attempt2`, system identifier **7699798773140758112**, chỉ **127.0.0.1:55432**; app DB mới `qa_task20b_20261027`, test DB `qa_task20b_suite`. Kiểm identity trước kết nối, không dùng database đã phục hồi chứa dữ liệu cũ hoặc URL Render. Test DB đã được xóa sau suite.

Đã điều khiển **Edge Chromium headless**, desktop **1280×900**, mobile **390×844**, reduced motion, và context tắt JavaScript:

| Luồng | Quan sát thực tế |
|---|---|
| Điều hướng → Lịch tháng | Đúng menu đang mở, thứ Hai, hôm nay, ngày ngoài tháng; thu **17.500.000 VND**, chi **7.120.000 VND**, **36 giao dịch**, **4 dự kiến** trong tháng QA 10/2026 |
| Ngày 10/10 nhiều mục | Ô ghi **25 giao dịch · 1 dự kiến**, xem trước 3, Xem thêm 26 mục; trang ngày **20+5** giao dịch không lặp/mất, tổng **550.000 VND** ở cả hai trang, Internet dự kiến không cộng |
| Định kỳ và ngày thực tế | Kỳ đã ghi nhận hiển thị một khoản ở 03/10 hoặc 30/09, giải thích đến hạn 31/10; không hiện tiếp như chưa trả; Ghi nhận cho kỳ open chỉ mở form xác nhận, không submit |
| Tương lai/đổi tháng | 31/10 có cảnh báo ngày tương lai, tổng vẫn chứa bản ghi đó. Tháng trước/sau/hiện tại và tháng 2/2024 29 ngày đúng; ngoài cửa sổ có cảnh báo; URL month sai hiện lỗi 400 |
| Mobile | Tự dùng danh sách ngày, Xem thêm và phân trang hoạt động; không tràn ngang toàn trang. Tiền, nhãn Thu/Chi/Dự kiến đọc được |
| Không JavaScript/bàn phím | Enter mở menu native, chọn Lịch, gửi form tháng, Enter trên liên kết ngày đến chi tiết đầy đủ; không cần script lịch |
| Tách tài khoản | B kèm `user_id=A` vẫn chỉ thấy thu 0/chi **987.654 VND** và dữ liệu của B; URL giao dịch A trả 404 |

7 nhóm browser check đều đạt, không page error, không có POST tài chính trong quá trình xem lịch. Login là POST xác thực riêng. Một harness ban đầu gửi Enter vào thẻ time không focusable thay vì anchor; đã sửa harness để dùng liên kết thực và thử lại khi tắt JS, không sửa ứng dụng cho lỗi công cụ.

Sau các GET, đối chiếu **cả 19 bảng finance** với hash nội dung/số dòng trước UI: **không đổi**. Tổng ngày/tháng khớp SQL trực tiếp và dịch vụ cũ; phân bổ tiết kiệm **20.000.000 VND** của fixture không cộng vào thu–chi. SQLite QA integrity_check=ok, foreign_key_check không vi phạm. SQLite thật, hai model EN/VI và hai requirements giữ nguyên SHA-256. Không thử ghi trên tài khoản thật.

Ảnh cuối **ngoài Git**, đã xem trực quan:

- `desktop-calendar.png` (full page, viewport 1280×900), `desktop-calendar-viewport.png`.
- `mobile-calendar-top.png`, **`mobile-calendar-list.png`** (ngày nhiều mục trong khung 390×844).
- `mobile-day-detail.png`, `mobile-no-javascript.png`.
- Ảnh `*-before-spacing.png` chỉ để đối chiếu nội bộ trước tinh chỉnh CSS, không coi là ảnh giao diện cuối.

Bằng chứng riêng: `browser-checks.json`, `final-verification.json`, `postgresql-query-check.json`, `postgresql-final-query-check.json`, `database-identity.json`, log suite/static, `shutdown-report.json`, `diff-secret-review.json`, `evidence-manifest.json`. Snapshot/hash QA không chứa trong Git; database/credential/config/ảnh không vào static/public.

Đã dừng website **8022** và PostgreSQL **55432**, kiểm hai cổng đóng và postmaster.pid không còn. Đã xóa file credential, session trình duyệt và secret SQLite QA tạm; context B không tạo file session lưu trên đĩa. Dữ liệu/bằng chứng mô phỏng giữ riêng ngoài repository.

## Tệp thay đổi và giới hạn

- Mới: `finance/financial_calendar.py`, `financial_calendar_views.py`, `test_financial_calendar.py`; CSS `static/css/financial-calendar.css`; hai template `financial_calendar.html`, `financial_calendar_day.html`; hai include `calendar_cell.html`, `calendar_scope.html`.
- Sửa: `finance/services.py` (helper Decimal chung), `recurring.py` (giới hạn revision cho monthly_items), `urls.py`, `views.py` (nhãn ngày tương lai ở chi tiết); `templates/includes/navigation.html`, `templates/finance/transaction_detail.html`; README và tài liệu này.
- **Không cần migration**, không đổi model/schema/dependency. Chỉ migrate các migration hiện có trên DB QA mới, không migrate SQLite thật hoặc production. Rà diff/secret chỉ có mã, kiểm thử, CSS/template và tài liệu; tại thời điểm kết thúc QA chưa stage/commit/push/deploy.

Chưa kiểm trình duyệt khác, thiết bị điện thoại vật lý, screen reader, WCAG toàn diện, Linux/Render, UI online, tải lớn hoặc tính snapshot nhất quán khi ghi đồng thời. CSS line-clamp có thể khác trên browser khác, nhưng liên kết ngày luôn cho xem đầy đủ. Không coi số truy vấn nhỏ hoặc một smoke test là kiểm mọi tình huống vận hành. Chưa thêm scheduler, thông báo, biểu đồ mới, ghi nhận trực tiếp, tự retry, dữ liệu giả trong tài khoản thật hoặc thay quy tắc tài chính.

## Bàn giao và chốt mã — 27/10/2026

Theo yêu cầu bàn giao tiếp theo, rà đủ **16 tệp** mới/sửa của TASK 20B, gồm helper Decimal, tối ưu monthly_items và template chi tiết giao dịch. Không cần sửa mã thực thi; đối chiếu toàn bộ hash tệp với manifest QA cuối trước khi cập nhật riêng biên bản này.

- Tổng thực tế chỉ nhận Transaction của tài khoản đăng nhập; Dự kiến từ dịch vụ cũ được lọc riêng `due`/`upcoming`, không đưa vào phép cộng. Recorded/skipped/deleted không thành khoản chưa trả. Ngày thực tế khác hạn chỉ tính tại ngày thực tế, có giải thích.
- Hai endpoint chỉ GET, yêu cầu đăng nhập, truy vấn theo request.user, private/no-store; không gọi process/save/ML/forecast. Giữ bằng chứng SQL và hash toàn bộ 19 bảng finance không đổi từ lượt QA.
- Chạy lại **system check: 0 issues** và **makemigrations --check --dry-run: No changes detected** bằng cấu hình độc lập từ config.base, SQLite **`:memory:`** và secret ngẫu nhiên trong tiến trình. Không dùng config.local/config.production, không mở SQLite thật hoặc kết nối PostgreSQL/Render trong bước kiểm này.
- Mã không đổi nên **không chạy lại toàn bộ suite**. Giữ kết quả cuối **435/435 PostgreSQL**, **55/55 SQLite bổ sung**, **43/43 JavaScript**. 55 PostgreSQL liên quan đã nằm trong 435; 19 bài lịch nằm trong cả nhóm 55 và toàn suite. Không cộng các nhóm này thành tổng bài mới.
- Rà cả tệp tracked và tệp mới, không thêm database, credential, cấu hình QA, log hoặc ảnh riêng vào Git. Kiểm hash SQLite thật, hai artifact EN/VI và hai requirements vẫn nguyên; `git diff --check` đạt.
- Xác minh đúng tài khoản **thiennamm**, repository **thiennamm/khoa_luan_tai_chinh_ca_nhan** vẫn **Private**, giữ remote/main. Commit và push bình thường theo yêu cầu, không force-push. SHA local/remote và working tree được kiểm sau push và báo trong tin nhắn bàn giao, không nhúng SHA của chính commit vào tài liệu.

Bằng chứng chốt mã ngoài Git: `handover-offline-check.log`, `handover-github-identity.json`, `handover-security-review.json`, `handover-push-verification.json` trong thư mục QA nêu trên. Không truy cập production; push có thể kích hoạt auto-deploy đã cấu hình ở hosting, nhưng chưa xác minh kết quả triển khai/hoạt động online của commit này. Các giới hạn QA ở trên vẫn giữ nguyên.
