# TASK 15C — Lịch sử dự báo và đối chiếu

Thực hiện ngày 22/10/2026 tại dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`. Không có AGENTS.md trong repository. Đã đọc forecast/ForecastResult, coverage, phiên bản dữ liệu, signals và kiểm thử. Không đổi thuật toán, điều kiện 3/36 tháng, validation, tiêu chí lựa chọn, model ML, dependency hoặc thí nghiệm. Giai đoạn triển khai chỉ migrate QA; giai đoạn bàn giao được phép sao lưu/migrate SQLite local thật và commit/push (mục 7). Không truy cập production.

## 1. Kiến trúc

Trước đây mỗi tài khoản có một `ForecastResult` (OneToOne User). Tính mới dùng `update_or_create`, ghi đè bản hiện hành. Giao dịch/coverage thay đổi làm tăng `ForecastDataVersion`; GET Dự báo so fingerprint/tháng và ẩn kết quả cũ, không xóa nó. Cơ chế này giữ nguyên.

Thêm `ForecastHistory` tách khỏi bản hiện hành. Sau khi tính thành công trong POST Dự báo hiện có, `compute_and_store()` kiểm lại snapshot trong transaction, lưu kết quả hiện hành và `get_or_create` lịch sử **cùng transaction**. Lỗi insert lịch sử rollback cả kết quả hiện hành. Không có endpoint nhận số tiền dự báo, tháng đích, nhãn phương pháp hoặc fingerprint từ browser; không có thao tác tính dự báo quá khứ.

GET `/du-bao/lich-su/` chỉ đọc. Demo dùng dịch vụ riêng và không gọi đường lưu lịch sử cá nhân. Không huấn luyện hoặc lưu thêm mô hình trong chức năng này.

## 2. Snapshot và chống trùng

| Trường | Ý nghĩa |
|---|---|
| user | Chủ sở hữu; FK CASCADE khi xóa tài khoản |
| calculated_at / target_month | Thời điểm hoàn thành lần tính đầu và tháng đích |
| estimate / method | Ước tính nguyên VND dạng chuỗi chính xác tới 30 chữ số; phục hồi Decimal; mã phương pháp đã chọn |
| configuration_version / configuration | Version thiết kế cùng cấu hình/runtime/engine hash tại thời điểm tính |
| fingerprint | Dấu vân tay server đã dùng để kiểm hiệu lực, gồm user, tháng, phiên bản dữ liệu, lịch sử/xác nhận và cấu hình |
| history_start/end/count | Khoảng đầu vào và số tháng liên tiếp |
| inputs | Tổng expense từng tháng, trạng thái, thời điểm xác nhận và số giao dịch; không chứa mô tả hoặc bản ghi giao dịch riêng lẻ |
| details | Chi tiết tính đã có: ứng viên/MAE validation, mốc validation, raw estimate, regime; giữ nguyên để kiểm lại |
| origin | `live-post-v1` cho đường tính mới; `legacy` cho kết quả cũ được bảo tồn bởi migration |

UNIQUE `(user, target_month, fingerprint, origin)` chặn trùng. Tính lại cùng fingerprint/config/tháng ở đường live giữ snapshot và thời điểm lịch sử đầu tiên, mặc dù `ForecastResult.calculated_at` có thể cập nhật. Một legacy không được nâng thành live; hai loại nguồn có thể cùng fingerprint nhưng legacy luôn bị loại khỏi đánh giá. Không gộp các phiên bản chỉ vì số tiền dự báo bằng nhau. Fingerprint tái sử dụng phiên bản dữ liệu toàn tài khoản hiện có: một thao tác ghi ở tháng khác cũng có thể làm fingerprint đổi, dù tổng các tháng đầu vào không đổi.

Lấy khóa ghi coverage trước khi kiểm snapshot/lưu (đã có, lịch sử hợp lệ có ít nhất 3 dòng coverage) và unique constraint bảo vệ hai phép tính đồng thời. PostgreSQL khóa các dòng coverage, `ForecastResult` OneToOne và `get_or_create`/unique là lớp bổ sung. SQLite có thể trả lỗi locked cho request thua; view hiện có báo DB bận và cho thử lại, không báo thành công giả. Không khóa trong lúc chạy thuật toán; nếu dữ liệu/tháng/cấu hình đổi khi tính, `StaleForecast` từ chối lưu. Chưa khẳng định khả năng xử lý tải cao hoặc thử đồng thời trên PostgreSQL thật.

Snapshot bất biến qua model `save` và QuerySet `update`/bulk_update; insert dùng force_insert để không ghi đè bằng PK. Bulk upsert update bị chặn. Không có UI sửa/xóa lịch sử riêng. Đây là bảo vệ ở ứng dụng, **không phải trigger database chống mọi SQL trực tiếp hoặc quản trị sửa dữ liệu**. Xóa tài khoản bằng ORM xóa lịch sử theo cascade. Sửa/xóa danh mục/giao dịch không sửa snapshot; không có FK từ snapshot tới giao dịch. Snapshot chứa tổng tài chính nhạy cảm, cần bảo vệ database/backup, không đưa vào Git hoặc tập huấn luyện/test nghiên cứu.

## 3. Chọn bản và đối chiếu

Một bản có bằng chứng hợp lệ khi origin live, có version/phương pháp nhận diện được, estimate hợp lệ và timestamp theo Việt Nam nằm **trong tháng đích**, trước thời điểm kết thúc tháng. Các tháng đầu vào snapshot phải liên tiếp, đủ ít nhất 3, đã xác nhận đầy đủ, có tổng không âm, khớp start/end/count và kết thúc đúng tháng trước tháng đích. Nếu thiếu bằng chứng, đầu vào chạm tháng đích hoặc timestamp sau tháng đích: “Không đủ thông tin đánh giá”, không đưa vào MAE.

Mỗi tháng chọn bản hợp lệ sớm nhất theo `(calculated_at, pk)`; PK phá hòa timestamp. Đây là **dự báo được lập trong tháng**, không phải đã lập trước đầu tháng. Các bản khác vẫn hiển thị đối chiếu riêng nếu đủ điều kiện, nhưng ghi “Chỉ xem lịch sử, không tính MAE”. Không chọn lại bản theo mức sai số và không sửa snapshot để gần thực tế hơn.

| Trạng thái | Điều kiện |
|---|---|
| Không đủ thông tin đánh giá | Thiếu bằng chứng nói trên; legacy luôn thuộc trạng thái này |
| Tháng chưa kết thúc | Có bằng chứng nhưng tháng đích chưa kết thúc theo Asia/Ho_Chi_Minh |
| Chưa đủ dữ liệu đối chiếu | Tháng đã kết thúc, coverage chưa xác nhận đầy đủ |
| Đã đối chiếu | Tháng kết thúc và coverage đầy đủ; có tổng expense hiện tại để so sánh |

Tái sử dụng `coverage.monthly_history()` để đọc tổng expense của chính tài khoản bằng Decimal, không dùng dự kiến định kỳ, income hoặc demo. Chỉ `forecast_expense` của tháng COMPLETE mới dùng làm thực tế, gồm số 0 khi đã xác nhận rõ và không có expense. Không coi thiếu coverage là 0.

Thực tế **không được đóng băng trong bảng lịch sử**: mỗi GET tính lại từ database. CRUD/CSV reset coverage qua hook hiện có nên đối chiếu mất hiệu lực; xác nhận lại thì dùng tổng mới, kể cả bằng 0. Nếu dữ liệu hoặc tháng thay đổi giữa các lần đọc, kiểm `ForecastDataVersion` trước/sau và tháng hiện tại; trả 409 yêu cầu tải lại, không giữ kết quả tổng hợp nửa cũ nửa mới. SQLite đọc trong atomic có snapshot nhất quán; PostgreSQL thêm version guard, chưa thử tải thật. Trang đã mở không tự cập nhật bằng WebSocket: cần tải lại để thấy thay đổi, thời điểm cập nhật luôn hiển thị. Thay đổi dữ liệu bằng SQL ngoài hook không được hỗ trợ.

## 4. Chỉ số và UI

- Sai lệch có dấu = dự báo − expense thực tế đã ghi; dương là cao hơn, âm là thấp hơn.
- Sai số tuyệt đối bỏ dấu; MAE = tổng sai số tuyệt đối / số tháng đủ điều kiện, đúng một bản mỗi tháng. Không có tháng hợp lệ thì MAE chưa có, không gán bằng 0. Không dùng MAPE.
- Tính Decimal với precision 64 cho phép trừ/cộng/chia trên estimate tới 30 chữ số; không chuyển float. Tiền và MAE hiển thị VND nguyên đồng bằng filter `vnd` chung (định dạng làm tròn của filter hiện có); số dùng tính MAE không làm tròn trước. MAE có thể có phần lẻ dù UI làm tròn VND.
- Tổng hợp đọc toàn bộ lịch sử đủ điều kiện, không chỉ 20 dòng trang đang xem. Không gắn MAE của nhiều phương pháp thành thành tích riêng của Ridge, không trộn MAE validation và không dùng tỷ lệ phần trăm chắc chắn/accuracy.
- Trang yêu cầu đăng nhập, filter user trước mọi xử lý, GET-only, never_cache. Liên kết từ trang Dự báo, các phiên bản cùng tháng liền nhau; đánh dấu bản được chọn/chờ đủ điều kiện hoặc đang dùng MAE. Trống có link chủ động tính dự báo. Nội dung chính và bảng/thẻ hoạt động không cần JavaScript mới.

## 5. Migration và triển khai sau khi được phép

Migration mới `0012_forecast_history`, phụ thuộc 0011 + User. Tạo **một bảng mới**, index, unique và CHECK tháng đầu ngày 1/origin hợp lệ. `RunPython` chỉ đọc các `ForecastResult` còn lại và copy sang origin legacy, inputs rỗng; không sửa User, giao dịch, coverage, ForecastResult hoặc dữ liệu cũ khác. Thời điểm legacy giữ giá trị cũ để tham khảo, **không chứng minh đã dự báo trước thực tế**, không thể phục hồi các lần đã bị ghi đè trước chức năng này.

Giai đoạn triển khai chỉ migrate SQLite QA; bàn giao ở mục 7 đã sao lưu và áp dụng 0012 trên local thật. Với máy khác hoặc lần triển khai tiếp theo, sau review và trước khi dùng luồng tính/lịch sử mới:

1. Dừng thao tác ghi, tạo backup SQLite qua backup API theo quy trình bàn giao đã có; integrity_check/FK/hash và kiểm phục hồi riêng. Không chỉ copy tệp live hoặc ghi đè backup cũ.
2. Áp dụng trên local bằng Python dự án, settings rõ ràng:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate --settings=config.local
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check --settings=config.local
& '.\.venv\Scripts\python.exe' -X utf8 manage.py showmigrations finance --settings=config.local
```

3. Đối chiếu dữ liệu cũ, số legacy bằng số ForecastResult trước migration, thử tài khoản QA riêng. Không seed tài khoản mặc định hoặc lịch sử giả vào tài khoản thật.
4. Render: backup PostgreSQL/kiểm phục hồi trước phát hành, giữ quy trình migrate/advisory lock đã có; theo dõi log migration/check. Chưa kết nối hoặc chạy các bước production trong task này. Migration ngược sẽ xóa toàn bộ lịch sử mới; không reverse nếu chưa sao lưu và đánh giá mất dữ liệu.

Rà PostgreSQL offline: compile **4 DDL + 2 dạng truy vấn**, chặn ensure_connection/cursor. Schema dùng bigint PK identity, FK user đúng kiểu auth_user integer và deferrable, date/timestamptz, jsonb, varchar; unique/index/CHECK extraction ngày dùng compiler PostgreSQL. Không thêm NOT NULL hoặc CHECK vào hàng cũ. RunPython dùng historical models và alias schema_editor, không có SQL riêng SQLite trong backfill. Unique có thể chờ khóa, backfill thêm dữ liệu theo số tài khoản hiện có nên cần dự trù thời gian/dung lượng.

**Chưa migrate, thử transaction/lock/role/deletion collector hoặc concurrency trên PostgreSQL thật**; compile không phải bằng chứng triển khai PostgreSQL thành công. Chưa đổi DB, hosting hoặc dependency.

## 6. Kiểm chứng thực tế

QA riêng: `D:\SAO LUU KHOA LUAN\task15c-qa-20261022-231917`, server `127.0.0.1:8018`. Runner từ config.base, khóa sqlite3 chỉ cho mở QA/RAM, không import production. Dữ liệu và mọi thời điểm tính quá khứ giả lập trong `seed.py` **chỉ để kiểm thử luồng**, không phải lịch sử dự báo thực tế, không phải kết quả MoneyData/demo hoặc bằng chứng chất lượng mô hình.

Đã migrate SQLite QA đến 0012; system check không lỗi; makemigrations --check --dry-run không có thay đổi. Migration test có ForecastResult cũ giữ nguyên values và tạo legacy không đủ bằng chứng. Kiểm hồi quy migration trước cũng giữ các hàng tài chính/auth/ML feedback.

Đã chạy 301/301 hồi quy toàn finance ở phiên bản đầu (74,262 giây). Sau bổ sung precision Decimal tới 30 chữ số và kiểm CSRF, nhóm forecast/history/demo/coverage/CSV đạt 100/100 (13,444 giây). Sau chỉnh wrapper template mobile, nhóm lịch sử đạt **14/14** (5,969 giây). Không chạy lại thí nghiệm nghiên cứu.

Các ca kiểm tra gồm: snapshot bất biến, POST lặp và đồng thời chỉ một hàng; rollback; cách ly hai tài khoản; GET không tạo lịch sử, CSRF; legacy/đầu vào chạm đích/tính quá muộn bị loại; chọn bản đầu mỗi tháng; tháng hiện tại và ranh giới 17:00 UTC; COMPLETE zero, unknown/incomplete/hủy xác nhận; CRUD/CSV rồi xác nhận lại; sai lệch ± và MAE Decimal, 30 chữ số, không có tháng đủ điều kiện, phân trang nhưng tổng hợp toàn bộ; demo không thêm lịch sử; xóa tài khoản cascade; đọc gặp version đổi trả 409; kết quả hiện hành tiếp tục bị ẩn khi stale. Hai thread SQLite có thể một request locked, một thành công; không tạo hai hàng lịch sử/current result.

Browser QA: đã đăng nhập, xem đủ bốn trạng thái và hai bản tháng 7 chỉ một bản tính MAE; xem current forecast bị ẩn khi hủy coverage; xác nhận rõ tháng 9 không chi và thấy đối chiếu cập nhật; bấm POST Tính dự báo và thấy thêm phiên bản tháng hiện tại; đăng nhập tài khoản QA thứ hai chỉ thấy trạng thái trống. Desktop và **390×844 CSS** (đo DOM; clientWidth=scrollWidth=367, phần còn lại là scrollbar), không tràn ngang. Đã sửa wrapper nội dung mỗi ô để ghi chú không chạy sang cột nhãn khi hiển thị thẻ trên mobile; không đổi CSS/framework/JS. Viewport đã reset. Chưa thử thiết bị vật lý hoặc UI PostgreSQL.

Ảnh QA ngoài Git, trong thư mục trên: `history-desktop.png`, `history-mobile-390x844.png`, `history-mobile-row.png` (sau chỉnh wrapper), `history-mobile-after-post.png`, `history-other-empty-mobile.png`. Khi cuộn lớn bằng API có lúc screenshot trả nền trống dù DOM có nội dung; dùng cuộn bàn phím để chụp lại thẻ thành công, không coi ảnh nền trống là bằng chứng UI. Ảnh sau POST thể hiện **dữ liệu mô phỏng QA**, không dùng các số MAE trong ảnh làm báo cáo chất lượng thực tế.

Giới hạn: bất biến ở ứng dụng, không chống sửa SQL/quyền quản trị; cần clock máy chủ đúng; chưa có đánh giá thật nhiều tháng sau triển khai; không xác nhận được toàn bộ chi tiêu ngoài website. Dịch vụ hiện đọc toàn bộ snapshot lịch sử và dải tổng tháng của tài khoản để tổng hợp rồi phân trang; cần tối ưu khi có quy mô lớn, chưa đo hiệu năng PostgreSQL hoặc tải nhiều worker.

Kiểm tra cuối SQLite QA: integrity_check=ok, foreign_key_check không vi phạm; 7 snapshot mô phỏng sau thao tác POST, 3 tháng giả lập đủ điều kiện; tài khoản thứ hai không có snapshot. Tệp SQLite local thật giữ nguyên SHA-256 so với trước khi bắt đầu QA. Đây là kết quả trước bàn giao; chưa stage/commit/push ở giai đoạn triển khai, không có database/model/dataset/ảnh QA trong diff.

Tệp thay đổi: `README.md`, `finance/models.py`, `finance/forecasting.py`, `finance/urls.py`, `templates/finance/forecast.html`; mới: `finance/forecast_history.py`, `finance/forecast_history_views.py`, `finance/migrations/0012_forecast_history.py`, `finance/test_forecast_history.py`, `templates/finance/forecast_history.html`, tài liệu này. Không sửa các báo cáo/thí nghiệm đã chốt hoặc requirements. `git diff --check` và rà bí mật trên nội dung mới/sửa đạt; kiểm thử và script QA không truy cập database production.

## 7. Bàn giao local và mã nguồn — 22/10/2026

Rà diff cuối không phát hiện lỗi cần sửa mã thực thi. Đã đối chiếu migration 0012 (historical models, đúng alias, thêm bảng và copy legacy, không sửa hàng cũ); filter theo user; unique/transaction chống trùng; lựa chọn một bản hợp lệ sớm nhất theo thời điểm rồi PK. MAE chỉ cộng khi tháng kết thúc ở Việt Nam và coverage COMPLETE. Thực tế đọc lại bằng monthly_history; CRUD/CSV/hủy xác nhận loại tháng khỏi đối chiếu đến khi xác nhận lại. Snapshot dự báo không bị sửa theo thực tế.

- Backup mới ngoài dự án: `D:\SAO LUU KHOA LUAN\task15c-local-handover-20261022-234629\db.sqlite3`. Giữ các backup cũ. Có `manifest.json`, script backup/migrate và script kiểm chứng local chỉ đọc; thư mục chứa dữ liệu tài khoản, không đưa lên Git.
- Dùng SQLite backup API, kiểm integrity_check=ok, foreign_key_check không vi phạm; fingerprint từng bảng của bản sao khớp nguồn trước migration. SHA-256: `ed56345d06d568f7f0d71fcd4a2731ce1d7c07477922b4899596a8ba55acba2a`, đã kiểm lại sau migration.
- Runtime Python `.venv\Scripts\python.exe`, settings `config.local`, kiểm engine/path và guard sqlite3 chỉ cho mở đúng SQLite dự án chính/bản sao mới. Migration plan chỉ gồm 0012; migrate thành công, system check không lỗi, migrate --check đạt; makemigrations --check --dry-run không có thay đổi.
- Tất cả bảng nghiệp vụ cũ giữ nguyên số hàng/fingerprint. Hàng metadata framework cũ giữ nguyên; Django bổ sung đúng 1 content type và 4 quyền cho model mới. Local có **0 ForecastResult** trước migration nên copy **0 legacy**, bảng lịch sử mới rỗng; không tạo live snapshot hoặc lịch sử giả.
- Gọi dịch vụ review và render view bằng RequestFactory trên các tài khoản local hiện có (chỉ đọc, không đăng nhập hoặc tạo session). Mỗi tài khoản chỉ nhận dữ liệu của nó, số tháng đánh giá 0 và MAE chưa có; fingerprint mọi bảng trước/sau khớp. Không tạo tài khoản, giao dịch, coverage hoặc thời gian giả lập QA trong SQLite thật.
- Chạy lại **14/14** kiểm thử lịch sử liên quan trong SQLite RAM (6,535 giây): quyền sở hữu, thời điểm/coverage, MAE, cập nhật CRUD/CSV, chống trùng/đồng thời và migration legacy đều đạt. Không chạy lại toàn bộ hồi quy vì mã thực thi không đổi; tái sử dụng kết quả mục 6. Chỉ cập nhật README/tài liệu trong lượt bàn giao, không thay thuật toán, model ML hoặc dependency.
- PostgreSQL vẫn chỉ được rà schema/query và compile offline như mục 5: **chưa thử database PostgreSQL thật**, chưa kết nối production. Rà offline không chứng minh migration/lock/role/timeout trên Render đã chạy thành công. Push main có thể kích hoạt auto-deploy nếu hosting đã bật; không coi push thành công là kiểm chứng production.

Phục hồi local nếu cần: dừng các tiến trình ghi, kiểm SHA-256/integrity bản sao, giữ riêng database hiện tại trước phục hồi. Backup này ở schema 0011; dùng mã tương ứng hoặc áp dụng lại 0012 có kiểm tra trước khi chạy mã mới. Không ghi đè database đang phục vụ hoặc dùng backup local thay database production. Bàn giao commit/push đúng 11 tệp TASK15C lên main qua remote hiện có, không force-push; SHA local/remote báo trong kết quả bàn giao, không tự chèn SHA vào chính commit này.
