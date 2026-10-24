# TASK16D — Kết quả diễn tập phục hồi PostgreSQL QA

Ghi chú bàn giao: “chưa commit/push” mô tả lúc kết thúc TASK16D, trước đợt [chốt Git TASK16A–16E](production-verification.md#task16-handoff). Không chạy lại restore trong đợt chốt này.

**Bổ sung TASK16E (24/10/2026):** Đã chạy website riêng cổng 8004 với database phục hồi, 8 nhóm smoke HTTP/CSRF + đối chiếu DB đạt; 141 bản ghi phục hồi ban đầu giữ nguyên. Browser mới xác nhận được form đăng nhập, chưa hoàn tất các luồng UI. Website và PostgreSQL đều đã dừng. Xem [biên bản cấp ứng dụng và giới hạn](postgresql-application-smoke.md); nội dung TASK16D bên dưới giữ đúng phạm vi kiểm database ở thời điểm đó.

Thực hiện **23/10/2026**, hoàn tất kiểm lại bằng chứng và biên bản **24/10/2026**, giờ Việt Nam. **Phục hồi archive và các kiểm tra database QA đạt**; chưa thử website trên database phục hồi. Không kết nối Render, không dùng URL production, không migrate, không đổi SQLite local, website, dependency hoặc model. Chưa commit/push.

## 1. Nguồn và bộ server portable

Nguồn xác minh: [PostgreSQL Windows downloads](https://www.postgresql.org/download/windows/) dẫn tới [EDB ZIP binaries](https://www.enterprisedb.com/download-postgresql-binaries), bản **18.6 Windows x86-64**. Tệp [postgresql-18.6-5-windows-x64-binaries.zip](https://get.enterprisedb.com/postgresql/postgresql-18.6-5-windows-x64-binaries.zip) được tải hoàn chỉnh bằng HTTPS Range, nối các phần đúng Content-Range và độ dài, sau đó kiểm CRC **mọi member** của ZIP.

- ZIP: **384.620.317 byte**.
- SHA-256 cục bộ: `e2246ba91d22345bc3d017586c09ede52d9df180b1eeb480f050445f1cad84e2`.
- Không tìm thấy checksum công bố trên các trang chính thức đã đọc; không tuyên bố hash này đã đối chiếu digest của EDB.
- Authenticode của `postgres`, `initdb`, `pg_ctl`, `createdb`, `psql`, `pg_restore`: **NotSigned**. Không có chữ ký để xác minh publisher của các binary này. Nguồn HTTPS chính thức, CRC và hash tự tính không thay chữ ký/checksum độc lập.
- Giải nén an toàn vào thư mục mới: `C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-qa\pgsql`. Chặn đường dẫn tuyệt đối, `..`, symlink và đường dẫn ra ngoài đích. Chỉ lấy `bin/lib/share` cùng license server/client: **1.585 tệp**; không cài pgAdmin/StackBuilder, installer, service, không đổi PATH/firewall. Bộ client cũ giữ nguyên.
- Sáu công cụ trên chạy `--version` thành công: **18.6**. Manifest cài đặt chứa hash từng tệp tại `C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-qa\installation-manifest.json`; kiểm lại ngày 24/10: **1.585/1.585 khớp**, 0 lệch hash.

ZIP và helper tải/cài nằm ngoài Git: `D:\SAO LUU KHOA LUAN\task16b-client-preparation-20261023-133319`. Các phần tải chưa đủ của TASK16B không được dùng như ZIP hoàn chỉnh; chỉ sau nối đủ và CRC đạt mới giải nén server.

## 2. Đích QA và cách bảo vệ

Thư mục phiên diễn tập: `D:\POSTGRESQL QA\rehearsal-20261023`. Đã kiểm chưa tồn tại và cổng 55432 trống trước khi tạo; không có junction/symlink trong đường dẫn. ACL tắt kế thừa và chỉ cấp FullControl cho SID người dùng hiện tại, áp xuống tệp/thư mục con.

**Cluster phục hồi cuối cùng:** `D:\POSTGRESQL QA\rehearsal-20261023\data-attempt2`.

- Chỉ lắng nghe **127.0.0.1:55432**, không IPv6/địa chỉ mạng ngoài. Kiểm listener và đường dẫn process là binary QA đã cài.
- PostgreSQL **18.6**, UTF-8, locale **C**, timezone **Asia/Ho_Chi_Minh**; cấu hình QA riêng, không dùng cấu hình website.
- DB **qa_restore_20261023**, owner/login restore **qa_restore**, không superuser/CREATEDB/CREATEROLE. Admin **qa_admin** chỉ thuộc cluster mới này.
- Sinh ngẫu nhiên hai mật khẩu độc lập, không in hoặc đưa vào argument/lịch sử lệnh. `initdb` dùng pwfile tạm; kết nối dùng passfile tạm trong thư mục ACL riêng. Mật khẩu role được đặt bằng SCRAM verifier sinh trong bộ nhớ, không lưu SQL credential vào log. Tệp credential tạm đã xóa; không giữ mật khẩu QA dài hạn trong tài liệu hoặc repository.
- Xóa PG*/DATABASE_URL kế thừa khỏi môi trường process con; mọi kết nối có host/port/role/DB QA cố định. Không đọc `.env` hoặc settings Render/local. TLS tắt **chỉ trên loopback QA**, không đổi TLS của Render/backup.
- Log SQL statement tắt và giảm ghi nội dung lỗi trong server log; native stderr có thể chứa dữ liệu riêng nên chỉ lưu trong vùng QA được bảo vệ, không đưa vào tài liệu/Git.

Trước restore đã kiểm bằng SQL qua admin: `data_directory` đúng cluster mới, server version 180006, `listen_addresses=127.0.0.1`; kiểm lại identity qua role restore: đúng localhost, port 55432, DB QA và database chưa có bảng public. Không chỉ dựa vào chữ “QA” trong tên.

## 3. Lỗi điều phối đã xử lý, không ghi đè cluster

1. Lần đầu initdb/start ở thư mục `data`: `pg_ctl` đã thoát nhưng process server Windows còn giữ handle của pipe thu đầu ra, khiến điều phối chờ EOF. **Chưa chạy restore.** Đã gọi `pg_ctl -D ...\data -m fast -w stop` đúng cluster, exit 0; lệnh điều phối được giải phóng và ghi thất bại ở bước identity vì server đã dừng. Lần dọn tự động sau đó báo stop lỗi do server không còn chạy; đã lưu cả thất bại và bằng chứng dừng thủ công, không sửa thành bản ghi đạt.
2. Đổi thu đầu ra start/stop `pg_ctl` từ PIPE sang tệp thường ngoài Git. Một lần preflight sau đó bắt lỗi nhánh xử lý `--version` trả chuỗi rỗng; đã tách `--version` khỏi nhánh start/stop. Lỗi được chặn trước initdb/restore.
3. Giữ nguyên thư mục `data` ban đầu, không xóa/khởi tạo đè. Tạo cluster mới **data-attempt2** trong cùng vùng QA; mọi bước kiểm đích và restore chạy lại cho cluster mới. Không sửa công cụ/source website để xử lý hai lỗi điều phối này.

Bằng chứng các lần lỗi: `attempt1-result.json`, `attempt1-resolution.json`, `attempt1-run_rehearsal.py`, `attempt2-preflight-result.json` trong vùng QA. Các lỗi trên đã xử lý; không có lỗi restore/database còn được phát hiện trong lần kiểm cuối.

## 4. Archive gốc và restore thực tế

Nguồn: `D:\SAO LUU KHOA LUAN\postgresql\postgres-20261023T093206237Z-f5e4a967\postgres-20261023T093206237Z-f5e4a967.dump`.

- Kích thước **94.232 byte**, SHA-256 trước/sau đều `31156a5b981da9156696f07ae9c97d0d7d4ad493deef1a8e3fa9a83dc218ccc6`, khớp manifest gốc.
- TOC đọc được; dùng `pg_restore --data-only --file=-` đọc các phần COPY **trong bộ nhớ**, đếm hàng mỗi bảng để đối chiếu. Không lưu thêm bản SQL/data đã giải mã hoặc in mô tả/tài khoản.
- Restore vào database QA rỗng bằng `pg_restore 18.6`, chỉ định rõ `-h 127.0.0.1 -p 55432 -U qa_restore -d qa_restore_20261023`, `--no-owner --no-privileges --exit-on-error --single-transaction`.
- Exit **0**. Không `--clean`, `--create`, bỏ trigger/ràng buộc hoặc chọn lọc bỏ dữ liệu lỗi. Không migrate sau restore để che sai khác.
- Lần chạy đạt bắt đầu khoảng **16:51:43**, hoàn tất kiểm database/dừng khoảng **16:52:01 ngày 23/10/2026**, giờ Việt Nam.
- Không sửa manifest/archive gốc; manifest gốc vẫn ghi `restore_into_qa=NOT_PERFORMED` ở thời điểm tạo backup. Kết quả diễn tập mới nằm riêng tại `rehearsal-result.json`.

## 5. Kết quả kiểm database

### Schema, migration, constraint và sequence

| Kiểm tra | Kết quả |
|---|---|
| Schema public | **24 bảng, 162 cột, 81 index**; inventory lưu riêng |
| Finance migrations | Đủ **12 migration 0001–0012_forecast_history**, tên khớp các tệp migration của dự án; không chạy migrate |
| Ràng buộc | **247**: 24 PK, 17 UNIQUE, 34 FK, 23 CHECK, 149 NOT NULL theo catalog PostgreSQL 18 |
| Index/constraint/triggers | 0 index invalid/not-ready; 0 constraint chưa validated; 0 trigger bị disable |
| FK | Quét **34 FK**, không có hàng mồ côi |
| CHECK | Đánh giá lại biểu thức trên dữ liệu cho **23 CHECK**, 0 vi phạm |
| NOT NULL | Quét **149 cột**, 0 giá trị NULL trái ràng buộc |
| Trigger riêng của ngân sách | Có `budget_category_guard`, `category_budget_guard`; không tự tuyên bố đã thử mọi hành vi trigger qua website |
| Nhất quán nghiệp vụ đã quét | Giao dịch–danh mục đúng chủ/loại; budget–category đúng chủ và expense; recurring rule–category đúng chủ/loại; occurrence–rule/transaction đúng chủ; tiền giao dịch nguyên VND: **0 vi phạm** |
| Sequence | **20/20** có ứng viên ID kế tiếp hợp lệ, lớn hơn MAX ID của bảng không rỗng và chưa vượt giới hạn sequence; xét `is_called` và increment. Không gọi `nextval`, không `setval` hoặc sửa sequence |

UNIQUE/PK và các index tương ứng được tạo thành công trong transaction restore, catalog valid. Không thử chèn dữ liệu giả hoặc gây lỗi ràng buộc vào bản dữ liệu phục hồi. Một số bảng trống nên việc quét hiện trạng không thay cho kiểm thử nghiệp vụ đầy đủ.

### Số hàng — chỉ thống kê tổng hợp

**24/24 bảng có số hàng bằng đúng số bản ghi COPY trong archive**. Đây là đối chiếu với archive, không phải truy vấn nguồn production sau backup.

| Bảng | Số hàng |
|---|---:|
| auth_group | 0 |
| auth_group_permissions | 0 |
| auth_permission | 80 |
| auth_user | 2 |
| auth_user_groups | 0 |
| auth_user_user_permissions | 0 |
| django_content_type | 20 |
| django_migrations | 27 |
| django_session | 2 |
| finance_budget | 0 |
| finance_category | 2 |
| finance_classificationfeedback | 0 |
| finance_classificationsuggestion | 0 |
| finance_csvimportbatch | 0 |
| finance_csvimportreceipt | 0 |
| finance_forecastdataversion | 2 |
| finance_forecasthistory | 0 |
| finance_forecastresult | 0 |
| finance_monthlycoverage | 0 |
| finance_recurringevent | 1 |
| finance_recurringoccurrence | 1 |
| finance_recurringrevision | 1 |
| finance_recurringrule | 1 |
| finance_transaction | 2 |

Không in username, mô tả, số tiền của từng giao dịch, password hash hoặc session từ các bảng này.

## 6. Dừng server và giữ nguyên dữ liệu khác

`pg_ctl -D ...\data-attempt2 -m fast -w stop` exit **0**. Kiểm độc lập sau đó và kiểm lại ngày 24/10:

- Cổng **55432 đã đóng**, không còn listener.
- **0 process postgres**, **0 Windows service PostgreSQL**.
- Không còn `.qa-pgpass.tmp` hoặc `.initdb-password.tmp`.
- Hash SQLite local `db.sqlite3` và hai artifact EN/VI khớp trước/sau và khi bàn giao; archive gốc không đổi. Không thay mã/config website, dependency hoặc model.

Cluster dữ liệu đầu tiên chưa restore và cluster phục hồi cuối đều được giữ riêng, đã dừng; không tự xóa để làm sạch bằng chứng. ACL không mã hóa ổ đĩa; bản phục hồi vẫn là dữ liệu riêng tư cần hạn lưu/thiết bị tin cậy do người dùng quyết định. Không khởi chạy lại chỉ để minh họa hoặc dùng mật khẩu production để đăng nhập QA.

## 7. Bằng chứng ngoài repository và giới hạn

Vùng bằng chứng: `D:\POSTGRESQL QA\rehearsal-20261023`:

- `rehearsal-result.json`: kết quả cuối, identity, số hàng, migration, kiểm ràng buộc/sequence, hash bảo vệ và dừng server.
- `schema-inventory.json`: cột, kiểu, index, định nghĩa constraint; không có bản ghi người dùng.
- `shutdown-verification.json`: kiểm cổng/process/service và credential cleanup sau chạy.
- `protected-files-before.json`, `signatures.json`, `run_rehearsal.py`: baseline hash, chữ ký đã kiểm và helper điều phối cuối; helper không chứa literal password/URL production.
- `evidence-manifest.json`: SHA-256 **25 tệp bằng chứng cấp trên**, kiểm lại **0 lệch hash** ngày 24/10; không bao gồm toàn bộ file cluster. Native logs riêng tư và bằng chứng các lần lỗi cũng ở vùng này, không sao chép vào Git/chat.
- Manifest tải/cài server nằm ở các đường dẫn mục 1; không đưa binary/ZIP lên Git.

Giới hạn: chưa kết nối production để so số hàng tại mốc nguồn; chưa chứng minh toàn bộ nội dung từng ô khớp bằng checksum dữ liệu; locale C/Windows không giống hẳn Linux Render, chưa đối chiếu collation nguồn; chưa kiểm thử website/UI hay mọi nhánh nghiệp vụ trên PostgreSQL phục hồi. Mật khẩu QA tạm đã hủy, chưa chuẩn bị cơ chế truy cập QA dài hạn. Không đổi các giới hạn này thành lỗi restore còn tồn tại hoặc tuyên bố mọi chức năng online đã đạt.

**Kết luận đúng phạm vi:** archive đã phục hồi thành công vào PostgreSQL 18.6 QA và qua các kiểm tra database nêu trên, server đã dừng. Đây không phải biên bản triển khai lại production hoặc kiểm thử ứng dụng hoàn chỉnh. Không chạy lại thí nghiệm ML hoặc test website vì không đổi mã ứng dụng. Chưa commit/push.
