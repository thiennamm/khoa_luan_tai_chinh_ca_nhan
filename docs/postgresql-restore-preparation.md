# TASK16C — Chuẩn bị diễn tập phục hồi PostgreSQL 18

Ghi chú bàn giao: các trạng thái “chưa chạy/chưa commit/push” dưới đây là lịch sử TASK16C; xem [chốt Git TASK16A–16E](production-verification.md#task16-handoff) để đọc kết quả cuối và phạm vi tệp được đưa vào Git.

**Cập nhật sau TASK16D:** Đã thực hiện restore và kiểm database trên PostgreSQL 18.6 QA ngày 23/10/2026, server đã dừng, kiểm lại ngày 24/10. Xem [biên bản kết quả thực tế](postgresql-restore-rehearsal.md). Cluster cuối ở `D:\POSTGRESQL QA\rehearsal-20261023\data-attempt2`; thư mục `data` của lần thử ban đầu được giữ nguyên, không ghi đè. Phần dưới giữ kế hoạch TASK16C tại thời điểm chưa chạy; không chạy lại các lệnh khởi tạo vào thư mục hiện đã tồn tại.

Ngày kiểm: **23/10/2026, giờ Việt Nam**. Đây là kế hoạch, **chưa cài thêm server, initdb, khởi chạy hoặc restore**. Không mở kết nối Render production; không sửa SQLite local, code ứng dụng, dependency hay mô hình. Không commit/push.

## 1. Backup đã kiểm trực tiếp

Thư mục ngoài Git:
`D:\SAO LUU KHOA LUAN\postgresql\postgres-20261023T093206237Z-f5e4a967`

| Thuộc tính | Kết quả thực tế |
|---|---|
| Tệp | `postgres-20261023T093206237Z-f5e4a967.dump` |
| Kích thước | **94.232 byte**, khớp manifest |
| SHA-256 | `31156a5b981da9156696f07ae9c97d0d7d4ad493deef1a8e3fa9a83dc218ccc6`, khớp manifest |
| Server nguồn theo manifest | `180006` — PostgreSQL **18.6**; thông tin do lần backup ghi, không phải kết nối lại nguồn trong TASK16C |
| TLS lúc backup theo manifest | `require` |
| Passfile tạm | Không có `.pgpass.tmp` trong thư mục backup |
| Đọc archive lại | `pg_restore 18.6 --list` và decode toàn bộ SQL/data vào Windows NUL, exit **0**, không thực thi SQL, không in TOC/dữ liệu ra báo cáo |
| Restore | **Chưa thực hiện**; manifest vẫn ghi `NOT_PERFORMED`, không sửa manifest gốc |

Kích thước nhỏ không chứng minh đủ hoặc thiếu dữ liệu. Hash/đọc archive đạt **không đồng nghĩa phục hồi thành công**. Chưa có đối chiếu số hàng nguồn cùng snapshot; không kết luận dữ liệu khớp tuyệt đối. Không chép SQL, tên tài khoản hoặc giao dịch vào tài liệu/Git.

Lệnh kiểm lại archive, đã chạy trong TASK16C (không kết nối database):

```powershell
& 'C:\Users\namt2\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe' -NoProfile -File 'D:\KHÓA LUẬN TỐT NGHIỆP\scripts\backup_postgresql.ps1' `
  -PgBin 'C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-client\bin' `
  -VerifyArchive 'D:\SAO LUU KHOA LUAN\postgresql\postgres-20261023T093206237Z-f5e4a967\postgres-20261023T093206237Z-f5e4a967.dump'
if ($LASTEXITCODE -ne 0) { throw 'Archive chưa đạt kiểm tra.' }
```

## 2. Thành phần còn thiếu — nêu trước, chưa cài

Đã có `pg_dump`, `pg_restore`, `psql` 18.6 và 8 DLL client tại `...\18.6-client\bin`. Không có `postgres.exe`, `initdb.exe`, `pg_ctl.exe` trong bộ portable hiện có hoặc PATH; không thấy `C:\Program Files\PostgreSQL`, service PostgreSQL hoặc listener cổng 55432 khi kiểm. Đây là kiểm các vị trí đã biết, không quét mọi ổ đĩa để khẳng định không có bản cài ở nơi khác.

**Cần bổ sung PostgreSQL server binaries Windows x86-64 18.6**, gồm:

- `bin\postgres.exe`, `bin\initdb.exe`, `bin\pg_ctl.exe`; thêm `createdb.exe`, `psql.exe`, `pg_restore.exe` để dùng trọn bộ cùng phiên bản.
- Các DLL đi kèm trong `bin`, `lib` (kể cả module của server), `share` (catalog, timezone, extension/control/SQL và cấu hình mẫu), license và thư mục hỗ trợ nguyên bản. Không chỉ copy ba EXE server vì initdb/server cần tài nguyên đi kèm.
- Nếu thiếu Microsoft VC++ runtime khi kiểm binary, dừng và xác định đúng runtime Microsoft trước khi bổ sung; không lấy DLL từ trang lạ. Chưa xác nhận bộ server chạy được vì chưa tải/cài.

Nguồn: [trang Windows chính thức PostgreSQL](https://www.postgresql.org/download/windows/) dẫn tới [ZIP binaries EDB](https://www.enterprisedb.com/download-postgresql-binaries), mục **18.6 Windows x86-64**. ZIP đã dùng để lấy client: [postgresql-18.6-5-windows-x64-binaries.zip](https://get.enterprisedb.com/postgresql/postgresql-18.6-5-windows-x64-binaries.zip). Kế hoạch tải toàn ZIP ngoài repository, kiểm nguồn/size/ZIP CRC, SHA-256 và Authenticode nếu có; không dùng các phần `.partial`/`.incomplete` của TASK16B như ZIP hoàn chỉnh. Nếu nhà phát hành không cấp checksum/chữ ký, ghi rõ giới hạn; hash tự tính không thay checksum công bố.

**Phương án đề xuất:** giải nén đầy đủ cây `pgsql` từ ZIP vào thư mục mới `C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-qa\pgsql`. Không installer, pgAdmin, StackBuilder, đăng ký service, mở firewall hoặc đổi PATH. Giữ bản client cũ. Phải kiểm vị trí giải nén, chữ ký/hash và phiên bản trước bước tiếp theo. Đường dẫn này là **dự kiến**, chưa tồn tại. Cluster mới ở `D:\POSTGRESQL QA\rehearsal-20261023`, cũng chưa tồn tại. Không tạo hai thư mục này trong TASK16C.

## 3. Lệnh dự kiến — CHỈ chạy ở bước diễn tập được cho phép sau

Các lệnh sau **chưa chạy**. Sau khi bộ server được cài/kiểm như mục 2, mở **PowerShell 7** riêng bằng đường dẫn tuyệt đối đã kiểm ở TASK16B. Không chạy bằng tài khoản Administrator nếu không cần. Đặt mật khẩu **QA mới**, không dùng URL/mật khẩu/SECRET_KEY production. Không bật transcript hoặc chia sẻ log SQL. Bản QA sau restore vẫn chứa dữ liệu riêng tư thật nên phải bảo vệ như backup.

### A. Kiểm đường dẫn, cổng và hash; chuẩn bị vùng riêng tư

```powershell
$ErrorActionPreference = 'Stop'
# Chỉ xóa override trong cửa sổ QA hiện tại; không in giá trị.
Get-ChildItem Env: | Where-Object Name -Like 'PG*' | ForEach-Object {
  Remove-Item -LiteralPath ('Env:' + $_.Name)
}
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$env:PGSSLMODE = 'disable'  # Chỉ TCP loopback QA, KHÔNG áp dụng cho Render.
$env:PGCONNECT_TIMEOUT = '5'

$qaBin = 'C:\Users\namt2\AppData\Local\Programs\PostgreSQL\18.6-qa\pgsql\bin'
$qaRoot = 'D:\POSTGRESQL QA\rehearsal-20261023'
$qaData = Join-Path $qaRoot 'data'
$sourceFolder = 'D:\SAO LUU KHOA LUAN\postgresql\postgres-20261023T093206237Z-f5e4a967'
$archive = Join-Path $sourceFolder 'postgres-20261023T093206237Z-f5e4a967.dump'
$expectedHash = '31156a5b981da9156696f07ae9c97d0d7d4ad493deef1a8e3fa9a83dc218ccc6'
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
  throw 'Hash backup thay đổi; dừng.'
}
foreach ($tool in @('postgres','initdb','pg_ctl','createdb','psql','pg_restore')) {
  $exe = Join-Path $qaBin ($tool + '.exe')
  if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Thiếu công cụ QA: $tool" }
  $version = & $exe --version
  if ($LASTEXITCODE -ne 0 -or "$version" -notmatch 'PostgreSQL\) 18\.6(?:\s|$)') {
    throw "Công cụ QA chưa đúng 18.6: $tool"
  }
}
if (Test-Path -LiteralPath $qaRoot) { throw 'Thư mục QA đã tồn tại; không tái sử dụng hoặc xóa đè.' }
if (Get-NetTCPConnection -State Listen -LocalPort 55432 -ErrorAction SilentlyContinue) {
  throw 'Cổng QA đã có listener; dừng để xác minh, không kết nối thử.'
}
# Trước tạo: bảo đảm D:\POSTGRESQL QA không phải junction/symlink sang nơi khác.
$ancestor = [IO.DirectoryInfo]::new($qaRoot)
while ($null -ne $ancestor) {
  if ($ancestor.Exists -and ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Đường dẫn QA có junction/symlink; dừng.'
  }
  $ancestor = $ancestor.Parent
}
[void][IO.Directory]::CreateDirectory($qaRoot)
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = [Security.AccessControl.DirectorySecurity]::new()
$acl.SetOwner($sid)
$acl.SetAccessRuleProtection($true, $false)
$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
  $sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
Set-Acl -LiteralPath $qaRoot -AclObject $acl
```

Chỉ tiếp tục khi bộ server nguyên vẹn và phiên bản đúng; chưa chạy block này nên chưa kiểm thực tế đường thành công. Nếu bất kỳ bước nào lỗi, dừng, không tự đổi port/đích hoặc tắt bảo vệ. Không xóa thư mục QA để thử lại bừa.

### B. Initdb và cấu hình chỉ loopback

```powershell
& (Join-Path $qaBin 'initdb.exe') -D $qaData --username=qa_admin `
  --pwprompt --auth=scram-sha-256 --encoding=UTF8 --locale=C
if ($LASTEXITCODE -ne 0) { throw 'Initdb QA lỗi; chưa khởi động.' }

@'
listen_addresses = '127.0.0.1'
port = 55432
ssl = off
timezone = 'Asia/Ho_Chi_Minh'
max_connections = 20
shared_buffers = '64MB'
password_encryption = 'scram-sha-256'
logging_collector = off
log_statement = 'none'
log_min_error_statement = 'panic'
log_parameter_max_length_on_error = 0
'@ | Add-Content -LiteralPath (Join-Path $qaData 'postgresql.conf') -Encoding utf8

# Không trust; không IPv6 hoặc các địa chỉ mạng khác.
'host all all 127.0.0.1/32 scram-sha-256' |
  Set-Content -LiteralPath (Join-Path $qaData 'pg_hba.conf') -Encoding utf8

& (Join-Path $qaBin 'pg_ctl.exe') -D $qaData -l (Join-Path $qaRoot 'server-private.log') -w start
if ($LASTEXITCODE -ne 0) { throw 'Server QA chưa chạy; log ở thư mục riêng tư.' }
$listeners = @(Get-NetTCPConnection -State Listen -LocalPort 55432)
if ($listeners.Count -ne 1 -or $listeners[0].LocalAddress -ne '127.0.0.1') {
  & (Join-Path $qaBin 'pg_ctl.exe') -D $qaData -m fast -w stop
  throw 'Listener không đúng loopback QA; đã yêu cầu dừng.'
}
$listenerProcess = Get-Process -Id $listeners[0].OwningProcess
if ($listenerProcess.Path -ne (Join-Path $qaBin 'postgres.exe')) {
  throw 'Listener không thuộc binary QA đã chọn; dừng kiểm tra.'
}
```

`initdb --pwprompt` hỏi mật khẩu admin QA ẩn. `--locale=C` là cấu hình QA cố định, chưa đối chiếu collation/locale nguồn; kiểm sort/unique và hành vi ứng dụng sau restore, không tuyên bố môi trường giống Render hoàn toàn. TLS tắt **chỉ trên 127.0.0.1 của server mới**; không sửa TLS backup/Render. Chạy bằng process người dùng, không `pg_ctl register`, không tự khởi động cùng Windows. [initdb 18](https://www.postgresql.org/docs/18/app-initdb.html), [pg_ctl 18](https://www.postgresql.org/docs/18/app-pg-ctl.html).

### C. Xác minh server, tạo role/database QA rỗng

```powershell
# Password QA được hỏi, không ghi trong lệnh.
$actualData = & (Join-Path $qaBin 'psql.exe') -X -h 127.0.0.1 -p 55432 `
  -U qa_admin -d postgres -W -At -v ON_ERROR_STOP=1 `
  -c "SELECT current_setting('data_directory');"
if ($LASTEXITCODE -ne 0 -or [IO.Path]::GetFullPath("$actualData".Trim()) -ne [IO.Path]::GetFullPath($qaData)) {
  throw 'Không đúng cluster QA; không tạo DB/restore.'
}
& (Join-Path $qaBin 'psql.exe') -X -h 127.0.0.1 -p 55432 -U qa_admin -d postgres -W `
  -v ON_ERROR_STOP=1 -c 'CREATE ROLE qa_restore LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;'
if ($LASTEXITCODE -ne 0) { throw 'Chưa tạo được role QA.' }
& (Join-Path $qaBin 'psql.exe') -X -h 127.0.0.1 -p 55432 -U qa_admin -d postgres -W `
  -c '\password qa_restore'
if ($LASTEXITCODE -ne 0) { throw 'Chưa đặt được mật khẩu QA.' }
& (Join-Path $qaBin 'createdb.exe') -h 127.0.0.1 -p 55432 -U qa_admin -W `
  --owner=qa_restore --template=template0 --encoding=UTF8 qa_restore_20261023
if ($LASTEXITCODE -ne 0) { throw 'Chưa tạo được database QA rỗng.' }

$identity = & (Join-Path $qaBin 'psql.exe') -X -h 127.0.0.1 -p 55432 -U qa_restore `
  -d qa_restore_20261023 -W -At -v ON_ERROR_STOP=1 `
  -c "SELECT current_database() || '|' || inet_server_addr()::text || '|' || inet_server_port()::text;"
if ($LASTEXITCODE -ne 0 -or "$identity".Trim() -ne 'qa_restore_20261023|127.0.0.1/32|55432' -and
    "$identity".Trim() -ne 'qa_restore_20261023|127.0.0.1|55432') {
  throw 'Danh tính database QA không đúng; dừng.'
}
$tableCount = & (Join-Path $qaBin 'psql.exe') -X -h 127.0.0.1 -p 55432 -U qa_restore `
  -d qa_restore_20261023 -W -At -v ON_ERROR_STOP=1 `
  -c "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','v','m','f');"
if ($LASTEXITCODE -ne 0 -or "$tableCount".Trim() -ne '0') { throw 'DB không rỗng; không restore.' }
```

`\password` hỏi mật khẩu mới cho role QA, tránh literal password trong SQL/log/history. Không tạo role giống username nguồn hoặc dùng quyền production. Role restore thường không cần superuser; nếu thiếu extension/quyền, dừng và chuẩn bị đúng extension bằng admin **QA**, không tự cấp superuser hoặc bỏ lỗi.

### D. Restore, kiểm tra và dừng server — chưa chạy

```powershell
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
  throw 'Archive đổi trước restore; dừng.'
}
# Nhập password QA tại prompt. Đầu ra có thể chứa SQL/dữ liệu riêng: lưu ngoài Git.
& (Join-Path $qaBin 'pg_restore.exe') -h 127.0.0.1 -p 55432 -U qa_restore `
  -d qa_restore_20261023 -W --no-owner --no-privileges `
  --exit-on-error --single-transaction $archive `
  1> (Join-Path $qaRoot 'restore-private.stdout.log') `
  2> (Join-Path $qaRoot 'restore-private.stderr.log')
if ($LASTEXITCODE -ne 0) { throw 'Restore QA chưa đạt; xem log riêng tư, không dán log gốc vào chat.' }
```

Không `--clean`, `--create`, `--disable-triggers`, không đổi đích sang URL khác. Không retry vào DB đã có dữ liệu. [pg_restore 18](https://www.postgresql.org/docs/18/app-pgrestore.html) mô tả archive được thực thi khi có đích database; chỉ restore bản tin cậy trong môi trường QA đã tách.

Sau exit 0 vẫn cần kiểm riêng: schema/index/FK/CHECK/unique/sequences, `django_migrations` thực tế, số hàng tổng hợp theo bảng và các constraint; so với bằng chứng snapshot nếu có. Không in bản ghi/tài khoản. Không tự migrate để che sai khác. Chạy ứng dụng bằng settings QA mới ngoài Git chỉ tới DB loopback này, secret QA mới, giữ nguyên cấu hình SQLite local/Render, tắt tích hợp ngoài. Không đăng nhập các tài khoản thật có trong bản restore; tạo tài khoản QA mới nếu được phép ở task diễn tập.

Chỉ sau restore và kiểm database/ứng dụng mới ghi thành công, kèm phiên bản, hash, exit code và giới hạn locale/extensions/đối chiếu nguồn. Dừng server đúng cluster khi xong (không xóa dữ liệu):

```powershell
& (Join-Path $qaBin 'pg_ctl.exe') -D $qaData -m fast -w stop
if ($LASTEXITCODE -ne 0) { throw 'Chưa xác nhận server QA đã dừng.' }
```

Không upload dump/log/cluster vào Git hoặc Release. Hạn lưu và xóa bản QA sau diễn tập sẽ do người dùng quyết định; chưa xóa hoặc thay bản backup nào.

## 4. Giới hạn của TASK16C

Đã xác minh hash/size và đọc archive bằng client thật; đã rà các vị trí công cụ/server đã biết và nguồn tải chính thức. **Chưa tải/cài server, chưa tạo thư mục cluster, chưa initdb/start/restore, chưa kiểm extension/locale hoặc ứng dụng trên PostgreSQL QA.** Các lệnh khởi tạo/restore là kế hoạch chưa kiểm chạy, không báo như kết quả đã đạt. Không thay bằng bằng chứng HTTP 200, SQLite QA hoặc SQL compile offline. Bước tiếp theo nhỏ nhất: bổ sung và kiểm server portable đúng nguồn trước khi cho phép initdb.
