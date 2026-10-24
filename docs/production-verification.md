# TASK 16A — Rà sau triển khai và chuẩn bị backup PostgreSQL

<a id="task16-handoff"></a>

## Chốt bàn giao Git TASK16A–16E — 24/10/2026

| Mức bằng chứng | Kết quả được giữ khi bàn giao |
|---|---|
| Backup PostgreSQL thật | Người dùng đã tạo archive 23/10; hash/size khớp manifest, đọc TOC và giải mã offline đạt. Archive và manifest gốc giữ ngoài Git |
| Restore database QA | TASK16D phục hồi vào PostgreSQL 18.6 riêng đạt; 24 bảng khớp số hàng COPY, migration 0012, ràng buộc và sequence đã kiểm; server đã dừng |
| Smoke ứng dụng | TASK16E có 8 nhóm HTTP/CSRF + đối chiếu DB đạt; 141 bản ghi phục hồi ban đầu giữ nguyên, SQLite thật/archive/model không đổi |
| UI/JavaScript | Chỉ quan sát form đăng nhập; chưa hoàn tất login/browser Apply/JavaScript/responsive. Không gọi smoke là kiểm thử toàn bộ hoặc bằng chứng production |

Phạm vi commit bàn giao: **2 script vận hành/kiểm thử offline và 4 tài liệu**. Không đưa dump, cluster, tài khoản/giao dịch, credential, native log, ảnh/UI tree hoặc các tệp bằng chứng riêng tư vào Git. Đường dẫn/hash/thống kê tổng hợp trong tài liệu là metadata để tìm bằng chứng đã giữ ngoài repository, không phải sao chép dữ liệu gốc.

Đợt chốt chỉ rà mã/tài liệu và chạy lại **28/28 kiểm tra offline đạt**; không chạy backup/restore, mở database hoặc đổi website/model/dependency. Lệnh PowerShell tuyệt đối đã kiểm nằm ở mục TASK16B; kế hoạch initdb/restore bên dưới là lịch sử, không chạy lại vào cluster đã tồn tại.

Các câu “chưa commit/push”, “chưa có công cụ/dump/restore” trong phần theo từng task ghi trạng thái **tại thời điểm task đó**, trước đợt chốt Git này. Kết quả cuối xem [restore database](postgresql-restore-rehearsal.md) và [smoke ứng dụng](postgresql-application-smoke.md). Hạn Free 21/11/2026 vẫn là mốc dự kiến cần kiểm Dashboard, không được xác minh lại trong đợt bàn giao.

**Cập nhật TASK16E:** [Smoke website trên PostgreSQL QA phục hồi](postgresql-application-smoke.md) đã đạt 8 nhóm qua HTTP/CSRF và đối chiếu database. Browser chỉ xác nhận form login; chưa hoàn tất kiểm UI/JavaScript. Không có kiểm production mới. Website QA cổng 8004 và PostgreSQL QA cổng 55432 đã dừng, các bản ghi phục hồi ban đầu và tệp thật được bảo toàn.

**Cập nhật TASK16D:** Đã phục hồi backup thật vào PostgreSQL 18.6 QA riêng, đối chiếu 24/24 bảng với COPY trong archive, kiểm migration 0012, FK/CHECK/NOT NULL và 20 sequence đạt; server đã dừng và cổng 55432 đóng. [Biên bản và giới hạn thực tế](postgresql-restore-rehearsal.md) ghi cả các lỗi điều phối đã xử lý. Không kết nối Render hoặc thử lại website production; kết quả database QA không thay bằng chứng online ở bảng bên dưới.

**Cập nhật TASK16C (23/10/2026):** backup người dùng vừa tạo tại `D:\SAO LUU KHOA LUAN\postgresql\postgres-20261023T093206237Z-f5e4a967` đã được kiểm lại: 94.232 byte, SHA-256 `31156a5b981da9156696f07ae9c97d0d7d4ad493deef1a8e3fa9a83dc218ccc6` khớp manifest; TOC/decode offline bằng pg_restore thật exit 0, không còn passfile tạm. Manifest ghi server 180006 và TLS require. Chưa phục hồi hoặc kết nối lại production. [Kế hoạch TASK16C và lệnh QA cụ thể](postgresql-restore-preparation.md) bổ sung thành phần server còn thiếu; **chưa cài server/initdb/start/restore**. Những đoạn “chưa có dump thật” dưới đây ghi hiện trạng ở TASK16A/16B, đã được cập nhật bằng bằng chứng archive này.

Ngày rà: **23/10/2026, giờ Việt Nam**. Dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`; website người dùng cung cấp: <https://so-thu-chi-thiennam.onrender.com>. HEAD khi rà: `444e4b2c321e6d30f56cb21d50583bc0eda1f175`. Đây là bảng bằng chứng và kế hoạch vận hành, **không phải biên bản mọi chức năng production đã đạt**.

Đã đọc README, [triển khai Render](render-deployment.md), [chuẩn bị triển khai lịch sử](deployment-preparation.md), [15A](classification-feedback.md), [15B/15B.1](recurring-transactions.md), [15C](forecast-history.md) và mã cấu hình/startup. Không cài công cụ, kết nối PostgreSQL/website production, tạo tài khoản online hoặc sửa dữ liệu thật trong TASK 16A. Không chạy lại ML hoặc kiểm thử website vì mã ứng dụng không đổi. Công cụ trình duyệt đã dùng cho QA ở các task trước hiện không còn khả dụng trong phiên này.

## 1. Phân biệt bằng chứng

### Có kiểm thử local/QA, không tự nâng thành online

| Phần | Bằng chứng đã có | Bằng chứng online hiện có | Còn chưa xác minh online |
|---|---|---|---|
| Tài khoản/đăng ký/đăng nhập | Test đăng ký không auto-login; hồi quy tài khoản, CSRF và ownership; các lần QA browser | Không có biên bản online riêng trong tài liệu đã đọc | Thông báo đăng ký, phiên khách, login/logout, cookie/TLS trên domain hiện tại |
| Danh mục, giao dịch, lọc, thống kê | TASK 11B/11C, bộ kiểm thử giao dịch và browser SQLite QA | Chưa có bằng chứng độc lập; phản ánh 15B.1 có giao dịch online được tạo nhưng không chứng minh tổng/lọc đúng | CRUD, ngày biên, tổng/phân trang, tách tài khoản trên PostgreSQL |
| Gợi ý VI/EN và phản hồi 15A | 252/252 hồi quy, 17/17 JS; browser QA VI Apply→lưu, EN chọn khác→lưu; migration local 0010; PG compile offline | Chưa có biên bản online của hai artifact/receipt/feedback | Tải đúng hai model/hash trên Linux, Apply/lưu, TTL, CSRF và chống dùng lại trên production |
| Định kỳ 15B/15B.1 | 279/279 ban đầu; 37/37 và 118/118 liên quan; browser QA desktop/mobile 390×844; local 0011 | **Người dùng đã phản ánh** quy tắc 10–12/2026 ghi nhận kỳ 10, trạng thái cũ “Đã bật / chờ tháng hiệu lực”, giao dịch ngày 31/10. Đây là báo cáo online từ người dùng, không phải lần tôi kiểm trực tiếp | Commit 1051193/444e4b2 đã chạy online chưa; trạng thái/ngày mặc định đã sửa chưa; không đủ bằng chứng kết luận backend đổi ngày nhập thành 31/10 |
| Ngân sách | Test ownership, 80%/100%/vượt, CRUD và browser SQLite QA 13A | Chưa có biên bản online | Tính tổng trên Postgres, bảo vệ category và giao diện |
| Nhập/xuất CSV | Test BOM, lỗi, Decimal, rollback/dedup, quyền và browser QA; chưa mở bằng Excel thật | Chưa có biên bản online | Upload/preview/confirm/download, lưu payload qua restart, quyền/TTL; Excel thật |
| Coverage/dự báo | Test liên tục/tháng unknown/zero, thời gian VN, lựa chọn baseline/Ridge; browser QA; không dùng MoneyData cho người dùng | Chưa có biên bản online | Điều kiện đủ dữ liệu, ML trên Linux, invalidation và tài nguyên Free |
| Lịch sử dự báo 15C | 301/301 hồi quy trước bổ sung cuối; 100/100 liên quan và 14/14 cuối; bàn giao chạy lại 14/14; browser QA 390×844/tài khoản thứ hai; local 0012 | Chưa có biên bản online. Những ngày dự báo quá khứ trong ảnh QA **giả lập**, không phải dự báo thật | Migration 0012 trên Render, trang trống với tài khoản mới, chống trùng/MAE/lock trên PostgreSQL thật |
| Backup/restore PostgreSQL | Rà cấu hình và script Windows mới, kiểm offline ở mục 6 | Chưa sao lưu hoặc phục hồi PostgreSQL thật | Server version, archive thật, restore thành công, quyền/TLS/allowlist |

Các tài liệu cũ có câu “chưa triển khai”, “chưa tạo Postgres” mô tả **thời điểm task đó**; README mở đầu cũng còn câu này. Không dùng chúng để phủ nhận URL online người dùng cung cấp hoặc suy ra đã xác minh môi trường hiện tại. Các mốc local đã bàn giao: 15A `ba60fe7`, 15B `a865d11`, 15B.1 `1051193`, 15C `444e4b2`; SHA trên GitHub **không chứng minh Render đang phục vụ đúng SHA**.

### Cần tự ghi bằng chứng Dashboard, chưa điền “đạt”

- [ ] Web Service: đúng domain, branch main, deploy SHA đầy đủ, thời gian deploy, kết quả build/start, có lỗi log không. “Deploy Live” chỉ là trạng thái triển khai, không thay checklist chức năng.
- [ ] PostgreSQL: đúng DB mà `DATABASE_URL` của web trỏ tới, region, major version, hạn Free, quyền/networking. Chỉ ghi tên dịch vụ/ID không bí mật vào biên bản riêng; **không chụp phần URL/password**.
- [ ] Migration startup log: thấy áp dụng/không còn chờ đến `finance.0012_forecast_history`; không chỉ xem build log. Đọc phần log an toàn, không dump env, DSN, cookie hoặc token.
- [ ] Ngày, tài khoản QA, thiết bị/viewport, bước thử, kết quả thực tế và ảnh đã che thông tin đăng nhập. Mỗi dòng ghi **Đạt / Lỗi / Chưa thử**. HTTP 200 không phải bằng chứng thao tác UI đúng.

## 2. Checklist thủ công ngắn cho người mới

**Chưa thực hiện các bước dưới trên online.** Dành khoảng 20–30 phút; có thể dừng và ghi “Chưa thử”. Chỉ dùng hai tài khoản **mới, dành riêng kiểm thử** A/B, ví dụ tiền tố `qa16a_20261023_`; tự đặt mật khẩu riêng, không gửi vào chat. Mọi mô tả/danh mục bắt đầu `QA16A`, không dùng thông tin cá nhân hoặc giao dịch thật. Chọn tháng hiện tại theo Việt Nam (ngày soạn: 10/2026). Đăng nhập A/B ở hai browser/profile riêng để tránh nhầm phiên.

| Bước | Thao tác | Kết quả mong đợi |
|---|---|---|
| 1. Đăng ký → login | Đăng ký A, rồi thử mở Giao dịch trước khi login; sau đó đăng nhập A | Tạo tài khoản, chuyển login với “Đăng ký thành công. Vui lòng đăng nhập để tiếp tục.”; vẫn là khách trước login; trang bảo vệ yêu cầu login |
| 2. Danh mục/giao dịch | Tạo `QA16A Thu` (income/Income), `QA16A Chợ` (expense/Groceries), `QA16A Học` (expense/Education). Thêm thu 1.000.000, chi chợ 150.000, chi học 50.000, đều ngày hôm nay; mô tả tiền tố QA16A | Tổng thu 1.000.000, chi 200.000, chênh lệch 800.000 VND. Danh mục đúng loại; thử amount 0 không lưu. Sửa/xóa **một khoản QA thêm riêng** rồi kiểm tổng trở lại đúng các số này |
| 3. Tìm/lọc | Tìm `qa16a`, loại Chi, category Chợ, chế độ tháng hiện tại. Thử khoảng ngày hôm nay–hôm nay; sau đó start>end | Chỉ chi chợ 150.000 khi phối hợp đúng; ngày biên gồm cả hai đầu; dữ liệu sai báo lỗi, không tự bỏ lọc/xuất toàn bộ. Xóa bộ lọc trở về tháng hiện tại |
| 4. Gợi ý VI | Thêm chi 20.000; mô tả QA không chứa dữ liệu thật, có thể thử “Đóng học phí học kỳ đại học”, chọn VI; yêu cầu gợi ý, kiểm nhãn/category của A, Apply rồi tự Lưu | Apply chưa lưu giao dịch. Khi lưu thành công và final category có canonical label: một feedback đúng snapshot, có Apply; cùng/khác nhãn theo lựa chọn cuối. Không hiển thị score như % chắc chắn |
| 5. Gợi ý EN | Thêm chi 30.000, thử “Grocery shopping at Whole Foods”, chọn EN; yêu cầu gợi ý → Apply → Lưu | Dùng đúng chế độ, có feedback tương ứng. Hai khoản VI/EN khiến tổng chi 250.000. Không ép đổi nhãn/category sai ý nghĩa chỉ để khớp. Nếu thiếu ánh xạ/model lỗi, ghi nhánh thực tế; **chưa đánh dấu Apply đạt**, vẫn thử lưu thủ công. Transfer luôn cần xem lại |
| 6. Định kỳ | Tạo chi QA 100.000, ngày đến hạn 31, start tháng này/end tháng 12/2026 (hoặc end phù hợp lúc thử). Mở Ghi nhận, xem ngày thực tế trước khi bấm; chọn hôm nay, xác nhận | Quy tắc trong hạn là Đang hoạt động. Ngày đến hạn riêng, ngày thực tế mặc định hôm nay VN, không phải ngày 31 tương lai. Chỉ sau xác nhận mới có giao dịch; chi lên 350.000. Refresh/quay lại kỳ không tự tạo thêm. Thử double-click xác nhận nếu UI cho phép: vẫn một giao dịch; UI chặn double-click **chưa chứng minh backend concurrent** |
| 7. Ngân sách | Đặt ngân sách tổng tháng 300.000; xem Ngân sách và Tổng quan | Đã ghi nhận 350.000, vượt 50.000, chữ vượt hạn mức và thanh không vẽ quá 100%; không cộng thêm khoản dự kiến chưa ghi nhận, không cộng ngân sách category vào tổng |
| 8. CSV | Tạo tệp thử ngoài repo theo mẫu bên dưới, UTF-8/BOM; upload → preview → confirm. Thử upload lại đúng tệp; xuất CSV với filter QA16A | Preview 2 dòng: thu 40.000, chi 10.000; xác nhận thêm đúng 2 giao dịch, không tự tạo category/ML. Tệp cùng hash bị chặn theo A. Xuất đủ kết quả lọc/header chuẩn; xác minh bằng trình soạn thảo UTF-8, chưa mở Excel thì ghi chưa thử |
| 9. Tổng sau CSV | Xóa lọc, chọn tháng hiện tại; đọc tổng và ngân sách | Thu **1.040.000**, chi **360.000**, chênh lệch **680.000**, ngân sách vượt **60.000**. Chỉ đúng nếu các bước tiền trước đã làm đủ và không thêm khoản khác |
| 10. Coverage/dự báo | Với A mới: xem dự báo khi chưa đủ 3 tháng. Nếu kiểm zero: chọn **một tháng đã kết thúc** của riêng A không có giao dịch, xác nhận rõ không có chi; vẫn giữ dưới 3 tháng liên tiếp | Chưa đủ lịch sử, không tính được. Tháng zero chỉ được coi đầy đủ sau xác nhận. Tháng hiện tại/tương lai không được xác nhận. Sửa một giao dịch QA của tháng đã xác nhận làm mất xác nhận tháng đó; chỉ thử trên dữ liệu QA riêng |
| 11. Lịch sử dự báo | Mở Dự báo → Lịch sử, khi A chưa tính thành công lần nào | Trống, MAE chưa có; mở lại không tự tạo snapshot. Nếu có legacy, phải ghi nguồn cụ thể, không tự coi là dự báo trước thực tế. Với tài khoản A **mới**, có hàng không rõ nguồn thì ghi lỗi và dừng |
| 12. Hai tài khoản | Đăng ký/login B riêng. Xem danh mục, giao dịch, feedback, định kỳ, coverage, budget và lịch sử. Dán vào B **URL xem/sửa một bản QA của A đã ghi lại** | B không thấy dữ liệu A; URL ID của A trả 404/không tìm thấy hoặc chuyển login nếu chưa login, không lộ nội dung. POST giả mạo/cạnh tranh phức tạp chưa thử online thì ghi chưa thử, không suy từ QA SQLite |

Ở bước 10, nếu thử reset coverage bằng giao dịch quá khứ, làm sau đối chiếu các tổng bước 9 hoặc loại riêng khoản đó khỏi phép cộng. Không xác nhận lịch sử tài khoản thật chỉ để mở chức năng dự báo; không đổi đồng hồ server/tạo timestamp quá khứ trên online để tạo bằng chứng dự báo. Luồng ≥36 tháng/Ridge và MAE thực tế nhiều tháng vẫn **chưa xác minh online**, không dùng demo thay thế.

Tệp CSV **mô phỏng để người kiểm tự tạo ngoài repo**; đổi ngày theo ngày thử và đúng tên category QA đã tạo:

```csv
date,kind,amount,category,description
2026-10-23,expense,10000,QA16A Chợ,QA16A CSV chi
2026-10-23,income,40000,QA16A Thu,QA16A CSV thu
```

Mẫu ghi kết quả: `Ngày giờ VN | Bước | Tài khoản QA (không mật khẩu) | Đạt/Lỗi/Chưa thử | Kết quả thực tế | ảnh/log đã che secret`. Thử desktop và DevTools responsive 390×844; đọc menu/form/thẻ, kiểm toàn trang không tràn ngang. Không coi ảnh QA local là ảnh online. Không tự SQL xóa dữ liệu production để “dọn test”; giữ tài khoản QA có nhãn, chỉ quản lý các bản QA bằng UI, tạm dừng rule QA khi xong.

## 3. Đọc cấu hình hiện hành

- `config.render` bắt buộc `RENDER=true`/`DATABASE_URL`, parse PostgreSQL và không fallback SQLite; internal connection của web dùng `sslmode=require`, timeout 10 giây, CONN_MAX_AGE=0. **Không import settings hoặc mở kết nối thật để rà cấu hình trong task này.** `config.production` cũ là profile SQLite, không dùng nó cho Render Postgres.
- Start `deploy/render-start.sh` → `scripts/render_start.py`: check --deploy/model, advisory lock, migrate/check, cleanup CSV rồi serve. Đọc mã này không chứng minh startup online đã thành công hoặc bản DB hiện tại đã tới 0012.
- DB chứa tài khoản/password hash/session, giao dịch, category, CSV preview/receipt, coverage, ngân sách, feedback ML, rules/revisions/occurrences/events, forecast current/history. Backup CSV export không bao phủ tất cả. Model EN/VI và static được cấp lại từ release/build, **không nằm trong pg_dump**; phải giữ riêng code commit, private bundle/hash và secret cấu hình trong kho bí mật.
- Cấu hình web dùng Internal URL. Máy Windows ngoài Render cần **External Database URL**; không dùng Internal hostname, địa chỉ IP đã resolve hoặc chép DATABASE_URL web sang command line. External access/IP allowlist và TLS phải kiểm trên Dashboard; không tự mở `0.0.0.0/0` hoặc đổi quyền trong task này. [Render: kết nối PostgreSQL](https://render.com/docs/postgresql-creating-connecting).

## 4. Công cụ Windows và sao lưu cụ thể

### Hiện trạng đã kiểm trên máy

PowerShell **7.6.5** có sẵn. Không tìm thấy `pg_dump`, `pg_restore`, `psql` trên PATH; không có `C:\Program Files\PostgreSQL`. Đây là tìm PATH/vị trí chuẩn, không khẳng định máy không có bản portable ở nơi khác. **Chưa xác minh major version server**; không tự chọn PostgreSQL 17/18 hoặc dùng CLI cũ trong pgAdmin tùy tiện.

Khi người dùng cho phép bước sau: Dashboard DB → Info → PostgreSQL version, ghi major. Từ [PostgreSQL Windows downloads](https://www.postgresql.org/download/windows/) đi theo installer EDB được trang chính thức dẫn; chọn bản ổn định/patch còn hỗ trợ **cùng major server**, thành phần Command Line Tools. Chưa cài trong TASK16A. Không tải RC/devel, không dùng một URL binary ngẫu nhiên; kiểm nhà phát hành/chữ ký Windows. Giữ đầy đủ DLL đi kèm tools. Nếu đã có tools portable từ nguồn chính thức, chỉ rõ bin path để kiểm trước.

`pg_dump` không dump server mới hơn major của nó và không bảo đảm restore xuống major cũ. Kế hoạch này chủ động yêu cầu **cùng major** cho dump/restore/psql/server nguồn; đích QA cùng major/compatible extensions. Đây là chính sách đơn giản để tránh nhầm phiên bản, không phải tuyên bố PostgreSQL luôn bắt buộc exact major. [PostgreSQL pg_dump: compatibility](https://www.postgresql.org/docs/current/app-pgdump.html).

### Script đã chuẩn bị, chưa chạy backup

`scripts/backup_postgresql.ps1` cần `pwsh` 7+ và Windows. Mặc định **chỉ kiểm tool local**. Không đọc `.env`, import Django hoặc tự tìm DATABASE_URL. Lệnh bên dưới chỉ có placeholder/đường dẫn công khai; thay `<MAJOR>` sau khi xem Dashboard, không chép dấu `< >` nguyên văn.

```powershell
# Chỉ kiểm công cụ; không kết nối DB hoặc hỏi secret.
pwsh -NoProfile -File .\scripts\backup_postgresql.ps1 `
  -PgBin 'C:\Program Files\PostgreSQL\<MAJOR>\bin' -CheckToolsOnly

# CHỈ chạy sau khi đã cho phép sao lưu production, đúng server major và endpoint.
pwsh -NoProfile -File .\scripts\backup_postgresql.ps1 `
  -PgBin 'C:\Program Files\PostgreSQL\<MAJOR>\bin' -Backup -ServerMajor <MAJOR> `
  -BackupRoot 'D:\SAO LUU KHOA LUAN\PostgreSQL'
```

Nhập **External Database URL vào prompt ẩn**, không gán literal URL vào lệnh/env toàn máy hoặc gửi chat. Không chạy trong phiên bật transcript, screen recording, debug/trace; không paste Render PSQL Command có credential. URL chỉ được giải mã trong bộ nhớ. Script nhận hostname đầy đủ `.render.com`, không Internal/IP; không có chế độ restore hoặc SQL ghi vào nguồn. Sau này script đọc `SHOW server_version_num` để so với major người dùng nhập trước khi dump.

Mật khẩu được ghi **tạm** vào passfile trong thư mục riêng có ACL chỉ SID người chạy; chỉ đường dẫn `PGPASSFILE` đi vào process con. Không dùng PGPASSWORD. Script dọn passfile trong finally, không ghi URL/host/user/password vào manifest hoặc in native error body. Không ghi vào lịch sử lệnh vì secret chỉ vào Read-Host -AsSecureString. Dữ liệu bí mật vẫn tồn tại thoáng qua trong RAM và tệp tạm riêng tư; không hứa xóa tuyệt đối dấu vết ổ đĩa/RAM. Nếu tiến trình bị kill/mất điện hoặc báo dọn lỗi, kiểm/xóa **chỉ `.pgpass.tmp`** trong thư mục backup đó trước khi copy/chia sẻ; không upload cả thư mục khi còn credential. [PostgreSQL password file](https://www.postgresql.org/docs/current/libpq-pgpass.html), [lý do tránh PGPASSWORD](https://www.postgresql.org/docs/current/libpq-envars.html).

Mặc định TLS `require` theo tài liệu external Render: mã hóa, không tuyên bố xác minh hostname/CA đầy đủ. Muốn `verify-full`, lấy CA bundle đáng tin cậy qua quy trình TLS của tổ chức/client, kiểm chain rồi thêm `-SslRootCert 'D:\duong-dan-rieng\trusted-ca.pem'`; không tải cert từ link lạ hoặc hạ TLS nếu lỗi. URL yêu cầu verify-full nhưng chưa cấp CA sẽ bị từ chối, không âm thầm hạ chế độ. Chưa kiểm TLS thực tế; CA hết hạn hoặc không đúng phải dừng xử lý, không bỏ kiểm để “chạy được”. [Render external TLS](https://render.com/docs/postgresql-creating-connecting#external-connections), [PostgreSQL SSL](https://www.postgresql.org/docs/current/libpq-ssl.html).

Script tạo thư mục mới và **tên archive có timestamp UTC** ngoài repo, ví dụ:

```text
D:\SAO LUU KHOA LUAN\PostgreSQL\postgres-YYYYMMDDTHHmmssfffZ-xxxxxxxx\
  postgres-YYYYMMDDTHHmmssfffZ-xxxxxxxx.dump
  manifest.json
```

`pg_dump --format=custom` đọc snapshot nhất quán của một database, không phải SQLite backup, không ghi thay đổi nghiệp vụ. PGOPTIONS đặt read-only; lock-wait timeout 30 giây. Dump không có global roles/tablespaces hoặc secret hosting/model; phải ghi **ID DB nguồn, deploy SHA và thời điểm VN** vào biên bản vận hành riêng đã bảo vệ để biết bản nào thuộc dịch vụ nào. Snapshot không bao gồm thay đổi phát sinh sau mốc của nó. [PostgreSQL pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html).

Exit code lỗi hoặc stderr bất kỳ làm dừng, không coi `.partial` là backup đạt. Nếu thành công: kiểm `pg_restore --list`, decode toàn bộ archive thành SQL vào Windows `NUL` **không có --dbname, không thực thi SQL**, rồi SHA-256/size/versions/thời gian/ssl mode vào manifest. Không lưu TOC hoặc SQL chứa dữ liệu vào Git/log. Archive đọc và decode được **chưa chứng minh phục hồi/constraints/ứng dụng hoạt động**. SHA-256 phát hiện tệp đổi, không chứng minh đủ dữ liệu hoặc nguồn đáng tin. [PostgreSQL pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html).

Có thể kiểm đọc lại offline (không kết nối) sau khi thực sự đã có archive:

```powershell
pwsh -NoProfile -File .\scripts\backup_postgresql.ps1 `
  -PgBin 'C:\Program Files\PostgreSQL\<MAJOR>\bin' `
  -VerifyArchive 'D:\SAO LUU KHOA LUAN\PostgreSQL\<thu-muc>\<ten-co-timestamp>.dump'
Get-FileHash -Algorithm SHA256 -LiteralPath 'D:\SAO LUU KHOA LUAN\PostgreSQL\<thu-muc>\<ten-co-timestamp>.dump'
```

Sau kiểm passfile đã dọn, giữ bản gốc và một bản thứ hai trên thiết bị/kho **riêng tư được người dùng chọn**, mã hóa disk/backup và quyền truy cập phù hợp. ACL không mã hóa archive; archive chứa password hash, session và tài chính thật. Không để trên filesystem Render Free, GitHub/repo/Release, thư mục sync/public hoặc gửi chat. Không có upload hay automation được tạo trong task này.

## 5. Kế hoạch phục hồi vào PostgreSQL QA riêng — CHƯA thực hiện

1. Chỉ sau khi có backup đạt và được phép diễn tập: chuẩn bị PostgreSQL QA **mới, riêng trên máy**, cùng major, role riêng, chỉ nghe `127.0.0.1:55432`, không tunnel/proxy tới Render, không chạy app thật. Hiện chưa có server/tools này; chưa cài hoặc tạo dịch vụ nào. Dùng pgAdmin hoặc quản trị local tạo database **rỗng** `qa_restore_20261023`, owner `qa_restore`; không chọn DB đang dùng. Nếu thay ngày, giữ tiền tố qa_restore.
2. Dùng Terminal mới, không có PGHOST/PGDATABASE/PGSERVICE/PGOPTIONS/DATABASE_URL cũ; kiểm chỉ tên biến trước và xóa cấu hình PG của **phiên QA này**, không in giá trị/env đầy đủ. Tuyệt đối không dùng Render External/Internal URL ở bước restore. Xác minh listener là server local riêng rồi hỏi identity bằng psql; không chỉ dựa vào chữ “QA” trong tên:

```powershell
# Chỉ trong cửa sổ PowerShell QA mới, xóa override libpq để tránh dùng nhầm nguồn.
Get-ChildItem Env: | Where-Object Name -Like 'PG*' | ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$pgTools = 'C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-client\bin'
& (Join-Path $pgTools 'psql.exe') -X --host=127.0.0.1 --port=55432 `
  --username=qa_restore --dbname=qa_restore_20261023 --password `
  --command='SELECT current_database(), inet_server_addr(), inet_server_port();'
```

Kết quả phải đúng tên QA, loopback và port QA; không có bảng ứng dụng. Mật khẩu QA nhập ở prompt, không phải argument. Dừng nếu danh tính không đúng hoặc có dữ liệu. Không dùng mật khẩu/SECRET_KEY production để khởi chạy website QA.

3. Đối chiếu SHA manifest trước restore, chỉ dùng archive do chính dự án tạo từ nguồn tin cậy. Chạy restore **không --clean, không --create**, một transaction, lỗi dừng/rollback. SQL trong archive sẽ được thực thi ở QA, cần môi trường riêng và quyền phù hợp:

```powershell
& (Join-Path $pgTools 'pg_restore.exe') --host=127.0.0.1 --port=55432 `
  --username=qa_restore --dbname=qa_restore_20261023 --password `
  --no-owner --no-privileges --exit-on-error --single-transaction `
  'D:\SAO LUU KHOA LUAN\PostgreSQL\<thu-muc>\<ten-co-timestamp>.dump'
if ($LASTEXITCODE -ne 0) { throw 'Restore QA chưa đạt; không đổi sang database khác để thử lại.' }
```

Owner/ACL nguồn không được áp sang QA; roles/extensions có thể cần chuẩn bị bằng quản trị **QA**, không dùng superuser production. Không dùng `--disable-triggers`, xóa constraints hoặc bỏ lỗi để đạt. Không coi `pg_restore --list` trước đó là bước này đã thành công.

4. Giữ log restore **riêng tư ngoài repo** nếu cần (native error có thể có dữ liệu/SQL); báo cáo chỉ mã giai đoạn/exit code đã che thông tin. Kiểm schema, index/FK/CHECK/triggers, `django_migrations` đến 0012, số hàng theo từng bảng (auth/category/transaction/coverage/budget/CSV receipts/feedback/rules/forecast/history), sequences/unique bằng thao tác QA có rollback; so với số nguồn tại mốc backup nếu đã ghi được. Chưa có phép đếm nguồn đồng snapshot thì ghi giới hạn, không tự khẳng định khớp tuyệt đối.
5. Chạy mã đúng deploy SHA với **settings QA riêng ngoài Git** kế thừa config.base, PostgreSQL chỉ 127.0.0.1:55432, secret QA mới, ALLOWED_HOSTS loopback; không import config.local/render hoặc dùng DATABASE_URL production. Bind app loopback cổng QA riêng. `check`, `showmigrations`, `migrate --check` với settings QA; chỉ xem migration, không tự migrate bừa archive khi đang kiểm khớp bản gốc. Dùng tài khoản QA mới để thử login/CRUD/coverage/feedback/dự báo; không đăng nhập tài khoản thật có trong bản phục hồi hoặc bật email/job/tích hợp ngoài.
6. Chỉ sau exit 0 + kiểm database + thử ứng dụng mới ghi **“phục hồi QA thành công”** với thời điểm, archive hash, server/client version và kết quả. Không chuyển DATABASE_URL web sang QA hoặc ghi đè production. Bản phục hồi vẫn chứa dữ liệu riêng tư thật, chỉ giữ trong môi trường tin cậy có hạn lưu rõ ràng. Chưa kiểm backup/restore PostgreSQL thật trong TASK16A.

## 6. Kiểm tra công cụ ở TASK16A và việc còn thiếu

Thêm hai script vận hành, không đổi website/schema/requirements/model:

- `scripts/backup_postgresql.ps1`: default tool-check; -Backup mới kết nối; -VerifyArchive chỉ đọc archive offline. Không có chế độ restore.
- `scripts/test_backup_postgresql.ps1`: parser + hàm tách URL/passfile, chặn đích trong repo, kiểm ACL thư mục QA, môi trường con không thừa kế PG/DATABASE_URL và che native stderr; mock các bước TOC/decode. **Không gọi binary PostgreSQL, không kết nối DB, không tạo dump thật.** Fixture có nhãn synthetic ngoài repo. Mã có guard reparse/junction ở đường đích nhưng chưa dựng junction thật để thử nhánh đó.

Chạy kiểm offline cuối bằng PowerShell 7.6.5: **22/22 assertion đạt**, gồm tool chưa cài dừng an toàn, yêu cầu TLS không bị bỏ qua, TOC/decode lỗi bị từ chối. Fixture cuối: `D:\SAO LUU KHOA LUAN\task16a-offline-b0c22201f88d4f9eb2fca2a9f9ba8086`, chỉ dữ liệu giả có nhãn, không phải dump database. Chưa cài pg tools nên **chưa** thử archive đọc thật, --file=NUL với pg_restore thật, TLS, quyền read-only nguồn, pg_dump hay restore/constraints thực tế. Còn thiếu: server major/Dashboard expiry đã đối chiếu, tool chính thức phù hợp, external access được phép từ máy này, archive thật và một database QA riêng để diễn tập. Không chạy lại toàn bộ tests website chỉ vì thêm công cụ vận hành.

## 7. Hạn Free và thứ tự việc tiếp theo

Ghi **dự kiến DB Free hết hạn 21/11/2026 theo mốc người dùng cung cấp trong TASK16A**. Không tìm thấy ảnh Dashboard/biên bản ngày cụ thể này trong tài liệu repository đã rà; chưa truy cập Dashboard để xác nhận độc lập. Không tự suy ngày hết hạn chỉ từ thời điểm commit hoặc ngày tạo web. **Phải xem lại Info/expiry của đúng DB trên Dashboard trước quyết định nâng cấp/chuyển và trước lịch backup cuối.**

Tài liệu Render hiện nêu Free Postgres hết hạn sau 30 ngày; sau hết hạn không truy cập được nếu chưa nâng gói, 14 ngày grace để nâng cấp trước xóa dữ liệu, **không phải thêm 14 ngày sử dụng miễn phí hoặc cửa sổ backup chắc chắn**. Free không có managed backup/recovery. [Render Free](https://render.com/docs/free#free-postgres), [Render recovery/backups](https://render.com/docs/postgresql-backups).

Thứ tự kế hoạch thủ công (chưa tạo lịch tự động, dịch vụ hoặc chi phí):

1. Xác minh SHA chạy online/0012, server major, expiry; điền checklist QA ở mục 2. Không đợi tới 21/11 mới kiểm quyền tải backup.
2. Khi được phép, cài tools chính thức phù hợp, thực hiện backup sớm và restore QA. Ghi rõ archive-read đạt và restore đạt là hai mốc riêng.
3. Nếu Dashboard vẫn là 21/11: rà lại lựa chọn giữ/chuyển trước **14/11**, chốt phương án và có backup/restore thử trước **18/11**, backup cuối trong khoảng dừng ghi **trước giờ hết hạn thực tế**. Đây là mốc đề xuất VN, không khẳng định DB còn truy cập cả ngày 21/11; không tự nâng gói hay tạo dịch vụ mới.

## 8. TASK16B — Client đã chuẩn bị; người dùng tự chạy backup thật

**Bổ sung xử lý `pwsh is not recognized` (23/10/2026):** PowerShell 7.6.5 có sẵn trong runtime Codex tại `C:\Users\namt2\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe`, không phải bản cài chuẩn ở Program Files. Chữ ký Authenticode kiểm thực tế: **Valid**, nhà phát hành **Microsoft Corporation**. PATH của terminal Codex tìm được binary này nhưng Windows PowerShell người dùng đang mở không tìm được; không cần cài thêm hoặc đổi PATH. Script yêu cầu `#requires -Version 7.0`, không thay bằng `powershell.exe` 5.1. Đã dùng đường dẫn tuyệt đối chạy `-CheckToolsOnly`: ba client 18.6, exit **0**, không kết nối DB. Đường dẫn runtime có thể đổi khi Codex cập nhật; khi đó cần kiểm lại, không tự chọn binary khác.

Lệnh không phụ thuộc PATH hoặc thư mục đang mở, copy vào Windows PowerShell (dấu `&` là bắt buộc):

```powershell
& 'C:\Users\namt2\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe' -NoProfile -File 'D:\KHÓA LUẬN TỐT NGHIỆP\scripts\backup_postgresql.ps1' `
  -PgBin 'C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-client\bin' `
  -Backup -ServerMajor 18 `
  -BackupRoot 'D:\SAO LUU KHOA LUAN\postgresql'
if ($LASTEXITCODE -ne 0) { throw 'Backup chưa hoàn tất.' }
```

Đây là lệnh để **người dùng tự chạy**, chưa được chạy với `-Backup` trong lần khắc phục PATH này. URL chỉ nhập tại prompt ẩn, không gửi chat; cơ chế bảo vệ bí mật/TLS của script giữ nguyên.

### Việc đã thực hiện ngày 23/10/2026

- Người dùng xác nhận bằng chứng Dashboard trước đây ghi **PostgreSQL 18**. Chưa kết nối để xác minh server hiện tại; script sẽ đọc `SHOW server_version_num` và dừng nếu major khác 18 trước khi dump.
- Máy Windows x64: đã cài **client portable cho người dùng hiện tại**, không installer, không đổi PATH, không cài server/service. Vị trí: `C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-client\bin`.
- Chạy thực tế `pg_dump --version`, `pg_restore --version`, `psql --version`: cả ba trả **18.6**, exit code 0. Có đúng 3 EXE client và 8 DLL đi kèm được xác định từ PE imports; dùng Windows runtime đã có. Không có `postgres.exe` trong bản cài; không tìm thấy PostgreSQL service/process sau cài.
- Đã tạo `D:\SAO LUU KHOA LUAN\postgresql` ngoài repository. **Chưa chạy -Backup, chưa nhập URL, chưa mở kết nối production, chưa có dump thật hoặc phục hồi QA.** Không thay Python, dependency, cấu hình website hay dữ liệu local.

### Nguồn tải và mức xác minh

Đi từ [PostgreSQL Windows downloads](https://www.postgresql.org/download/windows/) → liên kết ZIP binary trên [EDB binaries](https://www.enterprisedb.com/download-postgresql-binaries) → Windows x86-64 18.6, `https://sbp.enterprisedb.com/getfile.jsp?fileid=1260609` chuyển tới [ZIP EDB chính thức](https://get.enterprisedb.com/postgresql/postgresql-18.6-5-windows-x64-binaries.zip).

Gói nguồn có kích thước HTTP **384.620.317 byte**. Vì tải toàn ZIP chậm, chỉ đọc central directory và các member cần thiết qua HTTPS Range (kiểm 206/Content-Range/độ dài), tổng **9.230.109 byte** qua phương thức này; ZIP CRC được kiểm cho từng member đã giải nén. Chỉ lấy ba client, DLL phụ thuộc và license; không giải nén server. Các lần tải toàn gói bị hủy được giữ với tên `.incomplete`/`.partial` trong thư mục chuẩn bị, không coi là ZIP đầy đủ.

**Không có SHA-256 toàn ZIP vì chưa tải toàn bộ. Không tìm thấy digest do nhà phát hành công bố trên trang đã đọc.** Kiểm Authenticode cả 11 EXE/DLL trả `NotSigned`; không có chữ ký để xác minh nhà phát hành. HTTPS/nguồn liên kết chính thức và CRC không thay thế chữ ký hoặc digest độc lập. Hash dưới đây chỉ nhận diện các tệp đã nhận, không chứng minh bằng checksum của EDB:

| Client | SHA-256 cục bộ |
|---|---|
| pg_dump.exe | `9414dac0554065aa6edf739d7126b6e6e6d6fc3b56b9706b72cee47cee45b22c` |
| pg_restore.exe | `94c2b545fb870c08414dcf03cd93723f78662e1d489a0272150b40a0267f0d55` |
| psql.exe | `fde952534f520909c02db04675588ecb1da8d618b6e5c93e106f42a752daf720` |

Hash/size của cả 11 tệp và nguồn được lưu ở `C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-client\installation-manifest.json`; đọc lại đối chiếu **11/11 khớp**. Helper tải/chọn member nằm ngoài Git tại `D:\SAO LUU KHOA LUAN\task16b-client-preparation-20261023-133319`. Không có binary/tool được đưa vào repository.

### Rà script và kết quả kiểm tra

Giữ prompt `Read-Host -AsSecureString`, không nhận URL qua argument, không log native stderr; môi trường con loại bỏ PG*/DATABASE_URL kế thừa. Passfile UTF-8 nằm trong thư mục ACL riêng, dọn ở finally cả khi dump/kiểm archive lỗi. Đã bổ sung `Remove-BackupPassfile` và yêu cầu **dọn thành công trước đổi `.partial` sang `.dump` và ghi manifest/thông báo thành công**. Nếu dọn thất bại: exit khác 0, tệp giữ `.partial`, finally thử dọn lại; cần tự kiểm `.pgpass.tmp` nếu kill/mất điện. Lỗi ở bước ghi manifest cũng trả lỗi; không coi một tệp `.dump` đứng riêng là lần backup đạt.

Chạy `pwsh -NoProfile -File .\scripts\test_backup_postgresql.ps1`: **28/28 assertion đạt**. Có kiểm xóa passfile lặp, file bị khóa bị từ chối, thứ tự dọn trước finalize, TOC/decode lỗi, che lỗi và tách môi trường. Fixture cuối: `D:\SAO LUU KHOA LUAN\task16a-offline-a3d0e3e13f32407c84bd9ca9be2d8644`. Archive trong test vẫn là mock, không phải dump thật.

Ngoài test mock: chạy chế độ `-CheckToolsOnly` với binary thật đạt; `-VerifyArchive` trên tệp giả có nhãn bị **pg_restore 18.6 thật từ chối**, exit code **1**, không có thông báo thành công. Chưa kiểm đường thành công của archive thật, TLS/auth/allowlist/server read-only, dump hoặc restore. Không chạy lại test ứng dụng vì không đổi mã ứng dụng. Chưa commit/push.

### Lệnh người dùng chạy trên PowerShell — không gửi URL vào chat

Trước khi chạy: kiểm đúng DB/major 18 và External Access trên Dashboard, chưa hết hạn; đóng transcript/ghi màn hình/trace. Không tự mở quyền toàn Internet nếu kết nối lỗi. Script chỉ đọc nguồn để backup, không có migrate/restore/SQL sửa dữ liệu. Chạy nguyên lệnh sau (không thay URL vào lệnh):

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'
pwsh -NoProfile -File '.\scripts\backup_postgresql.ps1' `
  -PgBin 'C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-client\bin' `
  -Backup -ServerMajor 18 `
  -BackupRoot 'D:\SAO LUU KHOA LUAN\postgresql'
if ($LASTEXITCODE -ne 0) { throw 'Backup chưa hoàn tất. Kiểm giai đoạn lỗi; không gửi URL hoặc lỗi gốc chứa dữ liệu riêng.' }
```

Tại prompt ẩn, tự dán **External Database URL** từ Dashboard và Enter; không chép vào lệnh, biến toàn máy, file hướng dẫn hoặc chat. TLS mặc định `require` theo Render; xem mục 4 về giới hạn xác minh CA/hostname và tùy chọn `-SslRootCert` cho verify-full. Nếu server thực tế khác major, dừng để chuẩn bị client đúng; không sửa script bỏ kiểm phiên bản hoặc hạ TLS.

Chỉ ghi “backup đã kiểm archive” khi exit 0, có thông báo thành công, `.dump` và `manifest.json` mới cùng thư mục timestamp, không còn `.pgpass.tmp` hoặc `.partial`. Script đã kiểm `pg_restore --list`, decode vào NUL, SHA-256 và ghi manifest. Để kiểm lại offline mà không đưa tên tệp vào lịch sử lệnh, tự nhập đường dẫn **archive local** khi được hỏi (không phải URL):

```powershell
$archivePath = Read-Host 'Đường dẫn đầy đủ tệp .dump vừa tạo'
pwsh -NoProfile -File '.\scripts\backup_postgresql.ps1' `
  -PgBin 'C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-client\bin' `
  -VerifyArchive $archivePath
if ($LASTEXITCODE -ne 0) { throw 'Archive chưa đạt kiểm tra; chưa sử dụng để phục hồi.' }
$backupManifest = Get-Content -LiteralPath (Join-Path (Split-Path -Parent $archivePath) 'manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $backupManifest.sha256) {
  throw 'SHA-256 không khớp manifest.'
}
```

Kiểm đọc/giải mã/hash **không đồng nghĩa phục hồi thành công**. Chưa restore ở TASK16B. Kế hoạch mục 5 vẫn áp dụng: phải chuẩn bị riêng server QA cùng major (bản client vừa cài không cung cấp server), database rỗng trên `127.0.0.1:55432`, kiểm danh tính rồi mới restore trong transaction; tuyệt đối không dùng endpoint production. Ngày hết hạn **21/11/2026** vẫn là mốc dự kiến cần đối chiếu Dashboard, không được nâng thành ngày đã xác minh trong task này.
