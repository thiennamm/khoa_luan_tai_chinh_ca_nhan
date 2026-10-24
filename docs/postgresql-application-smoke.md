# TASK16E — Smoke test website trên PostgreSQL QA đã phục hồi

Ghi chú bàn giao: “chưa commit/push” mô tả lúc kết thúc TASK16E, trước đợt [chốt Git TASK16A–16E](production-verification.md#task16-handoff). Không chạy lại website/backup/restore trong đợt chốt này; giới hạn UI/JavaScript vẫn giữ nguyên.

Ngày thực hiện: **24/10/2026, giờ Việt Nam**. **8 nhóm smoke test qua HTTP thật có CSRF và đối chiếu database đạt**. Không coi đây là kiểm thử toàn bộ hoặc mọi luồng UI đã đạt. Website và PostgreSQL QA đã dừng; cổng **8004/55432 đóng**.

Đọc [biên bản TASK16D](postgresql-restore-rehearsal.md), cấu hình base/local, routes, dịch vụ phân loại/phản hồi, định kỳ, ngân sách và dự báo trước khi thực hiện. Không kết nối Render/URL production; không sửa cấu hình website chính, SQLite thật, archive, model, requirements hoặc kết quả thí nghiệm. Chưa commit/push.

## 1. Cấu hình và đích thực sự đã dùng

| Thành phần | Vị trí/cấu hình |
|---|---|
| Cluster đã phục hồi | `D:\POSTGRESQL QA\rehearsal-20261023\data-attempt2` — dùng lại, không initdb/restore lần nữa |
| PostgreSQL | **18.6**, chỉ `127.0.0.1:55432`, database `qa_restore_20261023` |
| Role ứng dụng mới | `qa_web_16e`, mật khẩu ngẫu nhiên; không superuser/CREATEDB/CREATEROLE, quyền DML trên bảng và USAGE/SELECT sequence của QA |
| Vùng ứng dụng QA | `D:\POSTGRESQL QA\application-16e-20261024`, ngoài repository, ACL riêng theo SID hiện tại |
| Python QA riêng | `D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe`, nhánh **3.13**, cài đúng `requirements-render.txt` hiện hành |
| Settings | `qa_settings.py` ngoài repository, kế thừa **config.base**, không import config.local/render; không lấy DATABASE_URL, không fallback SQLite |
| Website | **Waitress**, 2 threads, chỉ `127.0.0.1:8004`; WhiteNoise phục vụ static từ source cục bộ, không CDN |
| Model | Đọc đúng hai artifact EN/VI gốc cùng metadata trong dự án; không copy/sửa model, fit hoặc adapter DLL |

Đã kiểm cổng 55432 và 8004 trống trước chạy. Do TASK16D đã hủy mật khẩu quản trị QA, đã dùng **postgres --single khi cluster QA dừng** để đặt lại mật khẩu ngẫu nhiên cho **role database qa_admin của cluster QA**, rồi khởi chạy bằng pg_ctl. Không đặt lại mật khẩu Django của bất kỳ tài khoản đã phục hồi nào. Cách dùng single-user được đối chiếu [tài liệu PostgreSQL 18](https://www.postgresql.org/docs/18/app-postgres.html#APP-POSTGRES-SINGLE-USER).

Trước cấp quyền cho role ứng dụng, kiểm `data_directory`, server version, `listen_addresses`, localhost/port/database và system identifier đúng cluster của TASK16D. Sau đó settings QA có `QaIdentityMiddleware`: **mỗi request kiểm lại database, địa chỉ, port, role và system identifier trước view**; các helper thao tác/kiểm dữ liệu cũng gọi guard trước kết nối. Sai đích thì dừng, không chọn database khác.

Secret QA và mật khẩu ngẫu nhiên chỉ được cấp trong vùng ACL riêng, không in vào log/chat/argument; tệp passfile/credential tạm đã xóa sau dừng. Settings QA dùng cookie session/CSRF tên riêng `qa16e_session`/`qa16e_csrf`, tránh dùng lẫn phiên local cổng khác trên cùng hostname; secret, cache, upload temp và log riêng. TLS tắt chỉ ở TCP loopback QA, không thay cấu hình Render.

## 2. Preflight đã chạy

| Kiểm tra | Kết quả |
|---|---|
| `pip check` trong venv QA mới | Không có dependency hỏng; dependency website gốc không đổi |
| Django `check` với settings QA | **0 issues**, 0 silenced |
| `migrate --check --noinput` | Đạt; chỉ kiểm, không áp dụng migration |
| `showmigrations finance` | Đủ **0001–0012_forecast_history**, tất cả `[X]` |
| Tải model qua loader hiện có | EN/VI hash/metadata/cấu trúc được kiểm, load thành công; không fit/adapter |
| Khởi động WSGI và static | Waitress chạy localhost:8004, trang và static nguồn cục bộ được cấu hình qua WhiteNoise |

EN SHA-256: `362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345`.
VI SHA-256: `19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55`.

Không chạy full regression hoặc thí nghiệm ML vì không sửa mã ứng dụng/model. Kết quả cài dependency ở venv QA mới không thay requirements đã khóa. Runtime chi tiết lưu riêng trong `runtime-freeze.txt`.

## 3. Bằng chứng cấp ứng dụng — HTTP thật và database

`smoke_http.py` dùng URL cố định `http://127.0.0.1:8004`, cookie jar riêng, tắt proxy kế thừa, CSRF lấy từ form thật và giữ redirect trong đúng localhost. Đây là request tới WSGI đang chạy và render template thật, **không phải chỉ kiểm HTTP 200**, cũng không phải browser/JavaScript automation.

Tạo **một tài khoản QA mới** bằng luồng đăng ký hiện có; chỉ ghi dữ liệu mô phỏng vào tài khoản đó. Không đăng nhập hoặc thêm dữ liệu vào hai tài khoản có sẵn trong bản restore. Không dùng dữ liệu demo dự báo làm kết quả thật.

| Nhóm smoke | Thao tác và bằng chứng thực tế | Kết quả |
|---|---|---|
| 1. Đăng ký/đăng nhập | POST đăng ký tạo tài khoản mới, redirect login có thông báo; vẫn bị yêu cầu login khi vào giao dịch. Đăng nhập bằng tài khoản mới tới Tổng quan | Đạt |
| 2. CSRF | POST tạo danh mục thiếu CSRF bị **403**, không tạo bản ghi | Đạt |
| 3. Danh mục | Qua form HTTP tạo 3 danh mục của tài khoản mới, ánh xạ chuẩn Restaurants/Income/Shopping; kiểm owner/loại/nhãn trong DB | Đạt |
| 4. Giao dịch | Tạo chi 120.000 VND, thu 1.000.000 VND; đọc chi tiết và sửa chi thành 125.000 VND; kiểm Decimal, ngày, category, owner của hàng được lưu | Đạt |
| 5. VI/EN → Apply → feedback | Hai mô tả cố định được gửi vào hai mode thật; mỗi mode trả Restaurants. Gọi endpoint Apply với receipt server, sau đó POST Lưu; có 2 feedback cùng nhãn, applied=True, đúng mode/hash/transaction/user | Đạt |
| 6. Định kỳ | Tạo rule dự kiến 60.000 VND, ngày hạn 31: chưa tăng số giao dịch. Form ghi nhận mặc định hôm nay VN. Ghi nhận thực tế 65.000 VND ngày hôm nay, gửi lại POST: vẫn **1 occurrence/1 giao dịch định kỳ**; không tạo feedback ML thêm | Đạt |
| 7. Ngân sách/Tổng quan | Tổng chi thực tế tài khoản QA **263.000 VND**, ngân sách tổng **200.000 VND**, vượt **63.000 VND**; DB/service Decimal và template ngân sách/Tổng quan khớp. Thu 1.000.000 VND hiển thị trên Tổng quan | Đạt |
| 8. Dự báo/lịch sử | GET Dự báo hiện “Chưa đủ lịch sử”; GET Lịch sử hiện “Chưa có lịch sử dự báo”. POST tính khi thiếu lịch sử không tạo ForecastResult/ForecastHistory hay coverage complete giả | Đạt |

Mô tả suy luận cố định: VI “Ăn sáng phở bò + cà phê đá”; EN “Lunch at a restaurant”. Đây là đầu vào mô phỏng cho smoke, không phải tập test độc lập và không dùng để đánh giá chất lượng ML. Hai phản hồi **cùng nhãn/applied** chỉ chứng minh server lưu lựa chọn của người dùng theo receipt hợp lệ, không phải nhãn đúng đã kiểm định. Không in decision score hoặc phần trăm chắc chắn.

Sau smoke, chỉ tài khoản QA mới có: **3 danh mục, 5 giao dịch, 2 feedback, 1 rule, 1 occurrence**, **0 lịch sử dự báo**. Không tạo ≥3/36 tháng dữ liệu hoặc xác nhận đầy đủ giả để ép mở chức năng dự báo. POST lặp định kỳ đã thử tuần tự; không coi là kiểm cạnh tranh hai request đồng thời.

## 4. Bằng chứng trình duyệt và phần chưa thử

Công cụ computer-use/Sky điều khiển được Edge tới **trang đăng nhập tại localhost:8004**, đọc được nhãn “Tên đăng nhập”, “Mật khẩu”, nút “Đăng nhập”, và điền username QA. Các lần nhập tiếp bị guard của công cụ chặn với thông báo **“user input was detected in this window; call get_window_state before continuing”**, kể cả sau làm mới quan sát. Đã dừng thao tác thay vì tiếp tục tranh quyền điều khiển cửa sổ.

**Chưa hoàn tất đăng nhập qua trình duyệt**, chưa bấm nút Apply bằng JavaScript, chưa kiểm responsive/mobile hoặc chụp bộ ảnh UI. Không có ảnh QA mới để viện dẫn; không lưu cây UI của các tab cá nhân vào repo. Những thao tác đăng nhập/Apply/lưu ở mục 3 có bằng chứng **HTTP + DB**, không đổi nhãn thành “đã thử UI”.

Không thấy lỗi ứng dụng qua 8 nhóm smoke đã chạy. Chưa thử mọi validator, CRUD xóa, CSV, đủ 36 tháng/Ridge, MAE lịch sử khi đủ điều kiện, nhiều phiên/concurrency hoặc mọi tình huống phân quyền; không suy từ test SQLite trước đây thành các mục PostgreSQL này đã được kiểm trọn vẹn.

## 5. Bảo toàn dữ liệu, dừng dịch vụ và lỗi công cụ đã xử lý

Trước tài khoản QA mới phát sinh dữ liệu, đã tạo hash theo PK của **141 bản ghi có sẵn trong 24 bảng public**. Kiểm lại sau HTTP/browser: **0 bản ghi ban đầu đổi hoặc mất**. Hash chỉ dùng trong vùng bằng chứng riêng; không in bản ghi, username, mô tả, password hash hoặc session. Baseline này bao gồm các bản ghi tài khoản/phân quyền/giao dịch đã phục hồi, không bao gồm catalog role PostgreSQL; role QA mới và mật khẩu admin QA là thay đổi quản trị QA có chủ đích ở mục 1.

Đối chiếu **5 tệp được bảo vệ** trước/sau: SQLite thật, model EN, model VI, archive dump và manifest gốc — **0 lệch hash**. Catalog sau smoke có **0 constraint chưa validated**. Không chạy migration, cleanup dữ liệu hoặc sửa tài khoản đã phục hồi để làm test đạt.

Lệnh ghép dừng cưỡng bức process và lệnh ghép mã hóa/lưu credential bằng DPAPI bị bộ kiểm duyệt tự động từ chối với lý do “blocked by policy”, không được thực thi. Không thử lại thao tác cưỡng bức đó: đã dừng website qua **Ctrl+C của đúng session máy chủ**, sau đó `pg_ctl -D ...\data-attempt2 -m fast -w stop` exit **0**. Không giữ credential DPAPI; đã xóa riêng hai tệp secret QA tạm thay vì lưu lâu dài, xóa tham chiếu credential khỏi công cụ browser.

Kiểm cuối:

- Cổng **8004 đóng**, cổng **55432 đóng**; **0 process postgres**, **0 service PostgreSQL**.
- Không còn `credentials.json` hoặc `.admin-pass.tmp` trong vùng ứng dụng QA.
- Dữ liệu mô phỏng của tài khoản mới vẫn chỉ nằm trong database QA. Không xóa đè cluster hay archive để dọn test.
- Cấu hình QA được giữ ngoài repo nhưng cố ý **fail closed khi thiếu credential tạm**. Không chạy lại nguyên xi `bootstrap_qa.py` vì role đã tồn tại; lần truy cập QA sau cần quy trình cấp credential riêng, không lấy URL/password production hoặc đổi mật khẩu tài khoản Django đã phục hồi.

## 6. Bằng chứng và bàn giao

Vùng riêng: `D:\POSTGRESQL QA\application-16e-20261024`:

- `database-identity.json`: đích cluster/database đã xác minh, không password.
- `qa_settings.py`, `qa_manage.py`, `serve_qa.py`, `bootstrap_qa.py`: cấu hình/helper ngoài Git; không có literal secret.
- `preflight-results.json`, `runtime-freeze.txt`: kết quả check/migration/load model và dependency QA.
- `smoke_http.py`, `http-smoke-result.json`: 8 nhóm smoke và đối chiếu DB.
- `original-row-digests.json`, `final_verify.py`, `final-application-verification.json`: chứng minh 141 bản ghi gốc giữ nguyên và 5 tệp bảo vệ không đổi.
- `shutdown-result.json`: xác minh hai cổng đóng và credential đã dọn.
- `evidence-manifest.json`: hash **20 tệp bằng chứng cấp trên**, kiểm lại **0 lệch hash**; không bao gồm venv, dữ liệu cluster hoặc secret đã dọn.
- Log riêng tư ở cùng vùng; không chép vào Git/chat. ACL không thay mã hóa ổ đĩa; bản QA vẫn chứa dữ liệu riêng tư thật đã phục hồi.

**Phân biệt phạm vi:** TASK16D chứng minh restore/schema/data ở cấp database; TASK16E bổ sung smoke qua Django/WSGI, HTTP/CSRF và database PostgreSQL thật. Bằng chứng browser chỉ tới form đăng nhập. Không có bằng chứng mới về Render production hoặc kiểm thử ứng dụng toàn diện. Không sửa mã/dependency/model dự án, chưa commit/push.
