# TASK 11A — Sao lưu mốc tiếng Việt và rà phạm vi sản phẩm

Ngày rà: **21/10/2026**, thư mục thực tế `D:\KHÓA LUẬN TỐT NGHIỆP`. Không thêm chức năng, huấn luyện, refit, chạy lại TASK 10D hoặc deploy. Tài liệu mô tả hiện trạng, không mở rộng yêu cầu khóa luận.

## 1. Cách đọc bằng chứng

- **Có mã:** đã đọc route, model, view, dịch vụ hoặc template tương ứng trong checkout hiện tại; không suy ra chạy được chỉ vì có tài liệu.
- **Đã kiểm thử:** có kết quả chạy được ghi ở task trước và mã kiểm thử tương ứng; không có nghĩa mọi tình huống đã được bao phủ.
- **Đã thử trình duyệt:** có ghi nhận thao tác UI thật và ảnh QA ở TASK 09B/09C/10C, tách dữ liệu thật. Không dùng HTTP 200 hoặc unit test làm bằng chứng giao diện.

TASK 11A chỉ đọc mã/bằng chứng và kiểm bản sao, Git; **không chạy lại toàn bộ kiểm thử hoặc thao tác UI**. Tận dụng hồi quy TASK 10C: **147 Django + 10 JavaScript đạt**; sau thay đổi cuối chỉ sửa thông báo, **27 kiểm thử phân loại liên quan đạt**. Từ đó đến mốc này không đổi mã ứng dụng. Sáu kiểm thử protocol TASK 10B là lượt riêng, không cộng vào 147 kiểm thử Django và không chạy lại trong 11A.

## 2. Bảng phạm vi sản phẩm

| Chức năng | Trạng thái hiện tại | Bằng chứng mã / kiểm thử / trình duyệt | Phần còn thiếu hoặc giới hạn |
|---|---|---|---|
| Đăng ký, đăng nhập, đăng xuất | Có mã; đã kiểm thử; đăng nhập/đăng xuất đã thử UI | `config/urls.py`, SignUpForm, `finance/views.py:signup`; AuthenticationTests trong `finance/tests.py`; 09B/09C đăng nhập QA và đổi tài khoản bằng UI | Đăng ký được kiểm tự động; không có bằng chứng đăng ký qua UI trong các smoke test đã ghi. Chưa có xác minh email, giới hạn thử đăng nhập hoặc quản lý phiên nâng cao |
| Phân quyền, tách tài khoản, CSRF | Có mã; đã kiểm thử; một phần đã thử UI | Query theo request.user; form kiểm chủ sở hữu; IsolationTests, kiểm CSV/coverage/forecast/phân loại; 09C tài khoản B không thấy kết quả A | Không phải kiểm toán bảo mật toàn diện. Chưa thử mọi tổ hợp URL/đồng thời qua UI hoặc pentest |
| Danh mục thu/chi và ánh xạ nhãn | Có mã; đã kiểm thử; đã thử UI | Category, CategoryForm, category_* view; `finance/tests.py`, `test_classification.py`, `test_vietnamese_classification.py`; 09B tạo danh mục, 10C dùng ánh xạ riêng | Danh mục đang dùng không đổi loại/xóa được; chưa có giao diện chuyển hàng loạt giao dịch. Không ánh xạ bằng tên tự động; Transfer không ánh xạ thu/chi |
| Thêm/xem/sửa/xóa giao dịch | Có mã; đã kiểm thử; đã thử các luồng thêm/xem/sửa trên UI | Transaction/TransactionForm; transaction_* view, kiểm owner/kind/Decimal; 09B và 10C lưu/sửa QA; `finance/tests.py` kiểm xóa GET/POST | Không đủ bằng chứng đã bấm xóa qua trình duyệt trong các báo cáo. Chưa có sửa hàng loạt/đính kèm biên lai; đây không phải yêu cầu bắt buộc đã chốt |
| Lọc và danh sách giao dịch | Có lọc theo tháng, phân trang 20 dòng; đã kiểm thử; đã xem theo tháng trên UI | `month_context`, `transaction_list`, MonthForm, includes/month_filter; `test_list_filters_month`; 09B tổng quan/danh sách theo tháng | **Chưa có** tìm mô tả, lọc riêng danh mục/loại/khoảng ngày tùy ý. Không gọi bộ lọc tháng là tìm kiếm đa điều kiện |
| Thống kê thu/chi | Có tổng tháng, chênh lệch, số giao dịch và giao dịch gần đây; đã kiểm thử, đã thử UI | `finance/services.py:monthly_totals`, dashboard template, SummaryTests; 09B đối chiếu số thu/chi/chênh lệch QA | Chưa có báo cáo cơ cấu chi theo danh mục, so sánh nhiều tháng hoặc số dư ngân hàng. Chênh lệch thu–chi không phải số dư tài khoản |
| Nhập CSV có xem trước | Có mã; đã kiểm thử; đã thử UI desktop/mobile | `csv_import.py`, `csv_views.py`, CsvImportBatch/Receipt, `test_csv_import.py`; 09B upload BOM/xem trước/xác nhận thực | Hạn 2 MiB/5.000 dòng, mẫu header cố định; không đọc sao kê ngân hàng tùy ý. Hash chỉ chặn cùng tệp theo tài khoản; không giải quyết mọi giao dịch trùng. Có lệnh cleanup nhưng **chưa lập lịch dọn tự động** |
| Gợi ý tiếng Việt/Anh và xác nhận thủ công | Hai chế độ có mã; đã kiểm thử; đã thử UI desktop/mobile | `classification_modes.py`, loader EN giữ nguyên, SuggestionForm, endpoint, JS; 10C kiểm artifact/hash, quyền, CSRF, invalidation; ảnh QA ở báo cáo tích hợp | VI từ dữ liệu mô phỏng nhỏ AI biên soạn, chưa đại diện người Việt thật; còn 24 cảnh báo gần giống chưa duyệt độc lập. Không phát hiện ngôn ngữ, không hiệu chỉnh xác suất, không tự lưu/học. Transfer luôn cần xem lại. 10D chỉ ví dụ minh họa, không chứng minh accuracy |
| Lịch sử ghi chép theo tháng | Có ba trạng thái, thời điểm, xác nhận tháng đã kết thúc; đã kiểm thử và thử UI | MonthlyCoverage, coverage*.py; `test_monthly_coverage.py`; 09B/09C xác nhận rồi sửa giao dịch làm mất xác nhận | Do người dùng tự xác nhận, không chứng minh dữ liệu đầy đủ. Không tự xác nhận từ CSV. Khoảng trống vẫn chưa biết, không lấp 0 |
| Dự báo cá nhân | Có mã; đã kiểm thử; đã thử UI thiếu và đủ 36 tháng | forecasting/forecast_math, ForecastResult; `test_forecast.py`; 09B thiếu lịch sử, 09C chuỗi QA 36 tháng so DOM/dịch vụ, vô hiệu rồi tính lại, tách tài khoản | Cần đoạn tháng liên tiếp đầy đủ kết thúc tháng trước; <3 tháng không tính, 3–35 dùng TB3, >=36 mới so baseline/Ridge. Chưa có bằng chứng chất lượng trên lịch sử thật của nhiều người; validation không là test độc lập |
| Demo dự báo độc lập | Có mã; đã kiểm thử; đã thử UI desktop/mobile | `forecast_demo.py`, `forecast_demo_views.py`, `test_forecast_demo.py`; 09B; kịch bản 3–5 phút trong `demo-guide.md` | Chỉ chuỗi tự sinh 48 tháng, đích cố định 01/2026, giả định đầy đủ. Cache RAM mất khi restart; baseline thắng vẫn báo baseline. Không thể dùng làm hiệu quả dự báo cá nhân |
| Xuất dữ liệu người dùng | **Chưa có chức năng** | Đã đối chiếu routes/view/template hiện tại, không có endpoint export. Tải mẫu CSV chỉ trả header | Chưa có kiểm thử hoặc UI xuất dữ liệu. Có thể đề xuất nếu người dùng cần; chưa mặc định bắt buộc. Backup quản trị không thay cho xuất dữ liệu của tài khoản |
| Ngân sách/hạn mức/cảnh báo vượt chi | **Chưa có chức năng** | Không có model/route/view/template ngân sách trong mã hiện tại | Chưa có kiểm thử hoặc UI; chưa nằm trong phạm vi tối thiểu đã chốt, không tự thêm |
| Đổi/quên mật khẩu | **Chưa có luồng sản phẩm** | `config/urls.py` chỉ đăng ký/đăng nhập/đăng xuất; không gắn PasswordChangeView/PasswordResetView, không template/email reset | Django có cơ chế nền nhưng website **chưa tích hợp**. Chưa có kiểm thử/UI hai luồng này. Email phục hồi chưa cấu hình; cần chốt trước khi dùng trực tuyến, không mặc định bắt buộc cho demo cục bộ |
| Giao diện điện thoại | Có responsive CSS; đã thử UI ở 390×844 | `static/css/app.css`; 09B tổng quan/CSV/coverage/demo, 09C forecast đủ lịch sử, 10C gợi ý VI/EN; ảnh QA cục bộ | Cùng engine IAB, chưa kiểm Android/iPhone/Safari thật hoặc mọi kích thước. Menu/biểu đồ có vùng cuộn ngang riêng; không khẳng định mọi thứ vừa một màn hình |
| Hướng dẫn chạy, sao lưu/phục hồi | Có README và quy trình; chạy cục bộ đã có bằng chứng; backup đã kiểm thật | README; mục 6 của milestone-review; backup API/integrity/hash ở 09B và 11A | **Chưa diễn tập phục hồi toàn bộ sang môi trường mới**; kiểm hash/integrity không tương đương dựng lại website thành công. .venv không sao lưu; cần Python/requirements. Backup cùng ổ D chưa chống mất cả ổ |
| Báo cáo khóa luận | Có tài liệu kỹ thuật, khảo sát, kiểm định/thí nghiệm/tích hợp; **chưa có bằng chứng bản thảo khóa luận hoàn chỉnh** | `docs/data-survey.md`, các audit/experiment/integration và metadata; không tìm thấy bản thảo .docx/.tex/.pdf trong nguồn dự án hiện tại | Cần tổng hợp chương, yêu cầu, thiết kế, sơ đồ, đánh giá/giới hạn, tài liệu tham khảo và hình theo mẫu trường. Tài liệu repo không tự là bản khóa luận đã duyệt; không suy ra ngoài thư mục này không có bản thảo |
| Chuẩn bị triển khai trực tuyến | Chỉ cấu hình phát triển cục bộ; **chưa deploy/chưa xác nhận sẵn sàng production** | settings mặc định DEBUG=1, ALLOWED_HOSTS chỉ localhost; runserver cục bộ, requirements và WSGI/ASGI có sẵn | Chưa chốt hosting/domain/HTTPS, server production, static collection, secure cookies/proxy, vận hành/backup ngoài máy/giám sát hoặc email. Không chạy deploy-check để tự coi đã deploy. Không thay cấu hình trong task |

Các báo cáo TASK 10A/10B/10C/10D là mốc lịch sử: dòng “chưa tích hợp VI” của 10B đúng tại thời điểm 10B; hiện trạng mới ở 10C là đã tích hợp hai chế độ. Giữ nguyên tài liệu cũ, không sửa kết quả nghiên cứu để làm đẹp sản phẩm.

## 3. Bản sao lưu mới

```text
D:\SAO LUU KHOA LUAN\milestone-11a-20261021-110513
```

Tạo thư mục mới, không ghi đè backup 09B hoặc dữ liệu đang dùng. Dùng lại nguyên tắc 09B: **SQLite backup API**, kiểm integrity trên bản sao, đối chiếu byte/hash trước/sau sao chép; không copy thô SQLite đang mở.

- `database.sqlite3`: mở DB nguồn read-only, dùng `sqlite3.Connection.backup`; đăng ký hàm SQLite của Django trên kết nối kiểm bản sao, **PRAGMA integrity_check = ok**. Không phục hồi đè hoặc chạy migration trên DB thật.
- `project-private/data/`: toàn bộ dữ liệu tải về, workbook gốc/derived MoneyData, phân loại tiếng Anh, VI v1, bản chia/manifest, cả hai mô hình đang cấu hình và artifact thí nghiệm hiện có. Không huấn luyện lại hoặc tải lại dữ liệu. Giữ nguyên nguồn/giấy phép/metadata đã ghi.
- `project-private/secrets/`, `config/`, source/script/template/static, `experiments/`, toàn bộ docs/metadata, README/requirements/.gitignore/manage.py: bản byte nguyên gốc để phục hồi mốc, giữ cả source hash và xuống dòng của thí nghiệm đã khóa. `.env`/local settings nếu tồn tại cũng chỉ vào bản riêng. Không sao lưu .venv hoặc kho credential GitHub/GCM.
- `local-environment.json`: chỉ biến cấu hình Django trong whitelist nếu đang đặt ở tiến trình sao lưu; không thu toàn bộ môi trường hoặc token. Đây **không phải** bằng chứng đọc được biến môi trường riêng của một web server đã chạy trước đó; khi phục hồi cần đối chiếu cấu hình vận hành thực tế. Mặc định local hiện dựa secrets/ và settings đã sao lưu.
- `runtime.json`, `backup-verification.json`, `backup-helper.py`: phiên bản runtime, đối chiếu nguồn/bản sao và script quản trị riêng. Không chạy script huấn luyện/thử 15 câu trong quá trình backup.
- `source.bundle`: tạo sau commit/push mốc, chứa lịch sử Git; `git-verification.json` ghi commit, SHA remote và kết quả Private; `git-safety-review.json` ghi rà tệp. Các bằng chứng này bổ sung trước khi niêm phong manifest cuối.
- `manifest.json` + `manifest.sha256`: inventory đường dẫn, số byte và SHA-256 mọi tệp còn lại; kiểm lại toàn bộ sau khi hoàn tất. Bằng chứng backup chỉ chứa thống kê/hash, báo cáo này không chứa SECRET_KEY, token hoặc mật khẩu.

Đợt sao chép ban đầu có **293 tệp / 115.585.807 byte** (chưa gồm bundle, bản tài liệu mới này và bằng chứng Git cuối). Tổng cuối lưu trong manifest, không ghi số ước lượng thành kết quả cuối. Hai artifact dùng trên website đều được sao chép đúng hash:

| Mô hình | SHA-256 |
|---|---|
| Tiếng Anh | `362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345` |
| Tiếng Việt | `19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55` |

Backup chứa tài chính, cấu hình riêng và dữ liệu nghiên cứu: **giữ cục bộ, không đưa lên GitHub**. Không gom các DB/credential QA bên ngoài vào bản dữ liệu sản phẩm. Bằng chứng QA cũ vẫn ở thư mục QA/backup tương ứng. Bản này ở cùng ổ vật lý D với dự án, chưa chống hỏng/mất cả ổ hoặc mất máy.

## 4. Rà Git và mốc mã nguồn

Giữ nhánh **main**, remote **origin** `https://github.com/thiennamm/khoa_luan_tai_chinh_ca_nhan.git`. Git 2.53.0.windows.2; dùng tên/email tác giả local đã có, không sửa cấu hình toàn máy. API GitHub dùng credential hiện có, chỉ in login/repository/private/quyền push: xác nhận **thiennamm**, đúng repository **Private**, có quyền push. Trước commit đã fetch và xác nhận HEAD/origin/main cùng SHA `50f58612686d78ee4208dad9c27988474645ecb6`.

Rà cả tệp đang theo dõi và tệp mới, gồm thay đổi trước task 11A: cập nhật báo cáo 09C, dữ liệu/tài liệu 10A, script/cấu hình/metadata tổng hợp 10B, tích hợp/kiểm thử 10C, tài liệu 10D. Không đưa dataset, bản ghi giao dịch, workbook, SQLite, mô hình, .venv, bí mật hoặc QA lên Git. Metadata VI công khai chỉ là thống kê/đánh giá tổng hợp, không có cột mô tả giao dịch. 15 ví dụ trong tài liệu 10D là AI biên soạn theo yêu cầu lưu báo cáo, không lấy từ tài khoản người dùng; không phải file dataset.

Rà secret bao gồm so với khóa cục bộ, mẫu token/private key/URL credential, các phép gán literal đáng chú ý và đường dẫn loại trừ. Những literal mật khẩu trong các module kiểm thử đã đọc ngữ cảnh, chỉ là fixture test/migration/concurrency trong DB riêng, không tạo tài khoản mặc định cho website. Đây là rà theo mẫu và thủ công, không khẳng định phát hiện được mọi bí mật có thể có.

Chỉ stage danh sách tệp nguồn/tài liệu đã rà; migrations cũ đã theo dõi, không có migration mới. Push bình thường, không force, đổi remote hoặc đổi quyền truy cập. **SHA commit cuối và SHA đọc trực tiếp từ remote sau push được lưu ở `git-verification.json` trong backup**, thay vì cố ghi SHA của chính commit vào nội dung commit. `source.bundle` kiểm bằng `git bundle verify`; manifest cuối kiểm lại sau bổ sung bằng chứng.

## 5. Phục hồi an toàn vào thư mục mới

Đây là hướng dẫn, **chưa thực hiện diễn tập phục hồi**. Không phục hồi đè website hiện tại hoặc backup cũ. Mở PowerShell từ thư mục dự án đang có venv:

```powershell
$backup = 'D:\SAO LUU KHOA LUAN\milestone-11a-20261021-110513'
# Chỉ verify: đọc manifest/hash toàn bộ và integrity_check bản DB, không chạy ML.
& '.\.venv\Scripts\python.exe' -X utf8 "$backup\backup-helper.py" verify "$backup"
if ($LASTEXITCODE -ne 0) { throw 'Không phục hồi khi xác minh thất bại' }
$receipt = Get-Content -Raw -LiteralPath "$backup\git-verification.json" | ConvertFrom-Json
$restore = 'D:\KHOI_PHUC_KHOA_LUAN_11A'
if (Test-Path -LiteralPath $restore) { throw 'Chọn thư mục mới chưa tồn tại' }
git clone --branch main "$backup\source.bundle" "$restore"
if ($LASTEXITCODE -ne 0) { throw 'Clone thất bại' }
$restoredHead = git -C "$restore" rev-parse HEAD
if ($restoredHead -ne $receipt.local_commit) { throw 'Sai mốc mã nguồn' }
# Chép nguyên byte source/config/data để giữ source hash của thí nghiệm.
# Chỉ ghi bên trong thư mục phục hồi mới, không vào dự án đang dùng.
Get-ChildItem -LiteralPath "$backup\project-private" -Force | Copy-Item -Destination "$restore" -Recurse -Force
Copy-Item -LiteralPath "$backup\database.sqlite3" -Destination "$restore\db.sqlite3"
Set-Location -LiteralPath $restore
py -3.13 -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py showmigrations
& '.\.venv\Scripts\python.exe' -X utf8 manage.py runserver 127.0.0.1:8003
```

Giữ đúng Python/runtime như runtime.json; khóa requirements không thay trong task này. Kiểm và áp dụng biến local-environment.json **chỉ tại máy**, không in chúng vào báo cáo/chat; sửa đường dẫn tuyệt đối model/manifest sang thư mục phục hồi nếu có. Mặc định cả hai model đã nằm đúng dưới data/, metadata dưới docs/metadata/. Bản helper verify chỉ cần Python/Django phù hợp, không import website hay huấn luyện. Không chạy subcommand create từ helper đã sao lưu vì nó dành cho đường dẫn dự án nguồn ban đầu.

DB bản sao đã có migration đúng mốc, không tự chạy migrate hoặc ghi đè dữ liệu hiện tại. Nếu dùng mã mới hơn, sao lưu bản phục hồi trước khi cân nhắc migration. Git origin của clone bundle là đường dẫn bundle; chỉ thay remote của **bản phục hồi** khi có nhu cầu/ủy quyền rõ ràng, không vô tình đụng remote dự án thật. Kiểm local website, nhập thủ công và cả hai model từ cấu hình đáng tin cậy trước khi quyết định chuyển sang sử dụng.

## 6. Tối đa ba việc ưu tiên tiếp theo — chưa thực hiện

1. **Diễn tập phục hồi sang thư mục mới và chép backup sang ổ vật lý khác.** Phạm vi: xác minh manifest, clone bundle, dựng venv đúng phiên bản, kiểm DB, đăng nhập/nhập thủ công/gợi ý trên bản phục hồi tách biệt; giữ bản gốc. Lý do: hiện mới kiểm hash và integrity, chưa chứng minh phục hồi toàn chuỗi; backup cùng ổ vẫn có điểm lỗi chung.
2. **Tổng hợp một bản thảo khóa luận theo mẫu trường từ bằng chứng hiện có.** Phạm vi: chốt mục tiêu/phạm vi, sơ đồ dữ liệu/luồng, gom kết quả phân loại EN/VI và dự báo đúng mục tiêu, bảng giới hạn, ảnh QA và nguồn tham khảo; không chạy thêm thí nghiệm hoặc nâng điểm. Lý do: mã/tài liệu kỹ thuật đã nhiều nhưng chưa có bản thảo hoàn chỉnh được xác minh; cần dành thời gian cho sản phẩm học thuật.
3. **Lập quyết định triển khai trong một trang, chưa deploy.** Phạm vi: chọn tiếp tục demo localhost hay staging riêng; nếu staging thì nêu hosting/HTTPS, cấu hình production, quản lý secret, backup/restore và quyết định có cần quên mật khẩu/email hay không. Lý do: hiện ứng dụng dùng cấu hình phát triển. Xuất dữ liệu/ngân sách chỉ đưa vào backlog sau khi xác nhận nhu cầu, không mở rộng đồng thời để giảm rủi ro tiến độ.
