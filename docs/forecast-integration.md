# TASK 08D — Ước tính tổng khoản chi theo từng tài khoản

## Phạm vi và mục tiêu

Chức năng dùng giao dịch `expense` và xác nhận mức đầy đủ của **chính tài khoản đăng nhập** để ước tính tổng khoản chi ghi trong website của **tháng hiện tại theo Asia/Ho_Chi_Minh**. Ví dụ đang tháng 10/2026 thì tháng đích là 10/2026, lịch sử tối đa đến hết 09/2026. Ước tính cho cả tháng, không dùng các giao dịch của tháng hiện tại làm đầu vào tính toán.

Không coi đây là toàn bộ chi tiêu thực tế, số dư, chi tiêu tiêu dùng đã đối soát hoặc độ phủ được hệ thống chứng minh. Trạng thái đầy đủ vẫn là xác nhận của người dùng. Không tạo dữ liệu demo, tự xác nhận hoặc huấn luyện trên MoneyData.

Đã đọc `docs/forecast-experiment.md`: thí nghiệm MoneyData có giả thuyết ngày chưa được tác giả xác nhận, đơn vị tiền chưa xác minh, mục tiêu tổng ghi nợ quan sát, và Ridge thua baseline trên test. Giữ nguyên toàn bộ thí nghiệm đó. Code website không đọc workbook, dữ liệu dẫn xuất, cấu hình thí nghiệm hoặc các Pipeline đã lưu của MoneyData, không đổi đơn vị sang VND. Thiết kế website riêng trong `finance/forecast_config.py`, theo yêu cầu TASK 08D.

## Lịch sử đủ điều kiện

1. Lấy tháng đích theo múi giờ Việt Nam, không theo múi giờ trình duyệt hay UTC.
2. Bắt đầu ở tháng liền trước, đi ngược chỉ khi trạng thái là `complete`; dừng ngay tại tháng thiếu/chưa xác nhận/chưa đầy đủ. Giữ toàn bộ đoạn liên tiếp đó theo thứ tự tăng dần, không chọn một đoạn cũ kết thúc xa tháng đích.
3. Tổng hợp bằng `monthly_history` của TASK 08C trong transaction đọc nhất quán. Tổng từng tháng là Decimal tổng expense của tài khoản. Thu nhập không cộng vào mục tiêu.
4. Tháng đã xác nhận đầy đủ, không có expense là Decimal(0) hợp lệ. Tháng chưa biết không được thay bằng 0 hoặc nối qua. Nếu tháng liền trước chưa đủ thì số tháng hợp lệ kết thúc đúng yêu cầu là 0, dù có nhiều tháng đầy đủ ở đoạn cũ.

Không dùng số giao dịch, danh mục, mô tả, khoản thu, tổng tháng hiện tại hoặc tương lai làm đặc trưng. Thay đổi giao dịch hiện tại/tương lai vẫn vô hiệu cache bằng **bộ đếm phiên bản**, không đọc số tiền của chúng vào chuỗi dự báo.

### Dưới 3 tháng

Trang báo thiếu lịch sử và chỉ ra các tháng chưa xác nhận đầy đủ trong ba tháng lịch ngay trước tháng đích, kèm liên kết tới trang xem lại/xác nhận. Không tạo ước tính. Chỉ xác nhận khi thật sự đã ghi đủ; tháng không chi vẫn cần xác nhận riêng theo 08C.

### Từ 3 đến 35 tháng

Tính trung bình đúng ba tổng tháng cuối bằng Decimal. Tên hiển thị **“Ước tính theo trung bình 3 tháng”**, ghi rõ không phải Machine Learning. Không gọi Ridge hoặc fit Pipeline trong chế độ này.

## Mức thử nghiệm từ 36 tháng

Thiết kế cố định:

| Thành phần | Quy tắc |
|---|---|
| Validation | Sáu tháng cuối đoạn hợp lệ, cuốn chiếu dự báo một bước |
| Lịch sử mỗi mốc | Chỉ các thực tế đã quan sát trước tháng đích của mốc đó |
| Đối chứng | Tháng trước; trung bình ba tháng; cùng tháng năm trước |
| Ridge | Pipeline StandardScaler(with_mean=True, with_std=True) + Ridge(fit_intercept=True, solver=cholesky) |
| Alpha | 0.1, 1, 10 |
| Đặc trưng | lag 1, 2, 3, 12 và trung bình ba tháng ngay trước mục tiêu |
| Warmup | Mười hai tháng đầu chỉ cung cấp lag, không tạo nhãn/lag giả |
| Chặn âm | max(0, prediction), áp dụng trước tính MAE cho mọi phương pháp |
| Lựa chọn | MAE validation chưa làm tròn nhỏ nhất |
| Hòa chính xác | TB 3 tháng → tháng trước → cùng tháng năm trước → Ridge alpha 0.1 → 1 → 10 |

Không dùng tolerance hoặc số đã làm tròn để phá hòa. Ridge không được ưu tiên khi baseline tốt hơn hoặc hòa điểm. Trong sáu ứng viên có ba đối chứng và ba alpha Ridge; mỗi ứng viên được đánh giá trên cùng sáu tháng validation.

Tại mốc có t tháng quá khứ, X/y fit gồm các mục tiêu chỉ số 12..t−1, với mọi đặc trưng nằm trước từng mục tiêu. StandardScaler chỉ fit các X quá khứ này, không fit cả chuỗi hoặc hàng X dùng predict. Khi t=30 ở validation đầu của đoạn 36 tháng, có 18 hàng fit; ở mốc cuối t=35 có 23 hàng. Mỗi alpha tạo Pipeline mới tại mỗi mốc, tổng 18 lần fit cho lựa chọn. Thực tế validation được đưa vào lịch sử ở mốc kế tiếp, không dùng dự báo làm lịch sử thay thực tế.

Sau chọn, tính tháng hiện tại bằng phương pháp thắng với toàn đoạn lịch sử hợp lệ. Nếu Ridge thắng, fit một Pipeline mới trên toàn lịch sử với alpha đã chọn, tối đa thêm một lần fit; nếu baseline thắng thì không fit Ridge cuối. Không điều chỉnh phương pháp theo dữ liệu/thực tế tháng hiện tại.

MAE được dùng để chọn trên chính sáu tháng này, **không phải sai số test độc lập**, không phải cam kết sai số tháng sắp tới hoặc bằng chứng tổng quát hóa. Không có phần trăm chính xác, khoảng tin cậy hoặc ngưỡng độ tin cậy được suy ra. Không đưa điểm MoneyData vào giao diện người dùng.

## Kiểu tiền và lưu kết quả

Giao dịch VND hiện có vẫn giữ DecimalField nguyên đồng, tối đa 15 chữ số/khoản. Cộng tổng tháng, baseline, xử lý lỗi tuyệt đối và trung bình MAE dùng Decimal. Chỉ khi fit/predict Ridge mới chuyển các tổng/đặc trưng sang float64 cho scikit-learn. Giá trị không hữu hạn gây lỗi rõ ràng, không thay bằng một baseline được gắn nhãn ML.

Tất cả ứng viên được chặn âm trước đánh giá. Không xóa khoản lớn, đỉnh hoặc dòng trùng. Số dự đoán/MAE thô giữ trước làm tròn; chọn bằng MAE thô. Ước tính cuối hiển thị nguyên đồng với ROUND_HALF_UP; MAE trên bảng cũng làm tròn để đọc, có thể nhìn bằng nhau dù giá trị thô khác.

`ForecastResult` giữ **kết quả mới nhất** theo OneToOne tài khoản, tháng đích, fingerprint, số/tháng lịch sử đầu–cuối, mã phương pháp, cấu hình/runtime, thời điểm tính, chi tiết sáu mốc validation nếu có. Các số tài chính trong JSON là chuỗi Decimal. Pipeline từng mốc chỉ ở bộ nhớ request và được bỏ sau tính; không pickle/joblib mô hình từng người ra đĩa.

Ước tính VND cuối lưu ở cột TEXT `estimate` dưới dạng chuỗi số nguyên không âm, tối đa 30 chữ số, đọc qua property `estimate_decimal` để hiển thị Decimal. Điều này tránh converter NUMERIC/DecimalField của SQLite làm mất chữ số khi tổng vượt 15 chữ số. Không chuyển qua float khi lưu/đọc baseline; có kiểm thử ghi/đọc tổng 16 chữ số chính xác.

Kết quả và chi tiết validation vẫn là dữ liệu tài chính riêng, chỉ ở SQLite đã được Git ignore; không chép vào tài liệu hoặc Git. Đây là cache mới nhất, không phải nhật ký giữ mọi lần chạy. Migration 0005 tạo bảng bộ đếm/kết quả; migration 0006 đổi lưu ước tính sang TEXT trong bảng kết quả mới (bảng này chưa có dòng khi áp dụng). Không sửa các bảng dữ liệu cũ.

## Dấu vân tay và vô hiệu kết quả cũ

`ForecastDataVersion` là bộ đếm riêng theo tài khoản. Hook ghi chung của 08C tăng phiên bản khi giao dịch được thêm/sửa/xóa/bulk/CSV thành công; MonthlyCoverage.save tăng phiên bản khi xác nhận hoặc đổi trạng thái. Counter cùng transaction với thay đổi dữ liệu. CSV chỉ xem trước hoặc import rollback không tăng phiên bản đã commit; rollback giao dịch khôi phục cả trạng thái và counter. Tài khoản khác không làm đổi phiên bản của tài khoản này.

Dấu vân tay SHA-256 snapshot gồm:

- Chủ sở hữu, tháng đích, phiên bản dữ liệu.
- Chuỗi tháng quan sát, tổng Decimal, trạng thái/thời điểm xác nhận và số giao dịch, cùng các tháng còn cần xác nhận nếu chưa đủ.
- Thiết kế cố định, Python/scikit-learn/NumPy/SciPy hiện có và hash nguồn thuật toán/đọc dữ liệu/hook liên quan.

Counter cũng vô hiệu kết quả khi sửa mô tả, khoản thu hoặc giao dịch hiện tại/tương lai, dù các giá trị đó không phải đặc trưng numeric. Đây là vô hiệu bảo thủ; tính lại có thể cho cùng số. Thay đổi xác nhận ở đoạn cũ qua giao diện cũng tăng phiên bản. Không nhận fingerprint, snapshot, tháng đích, phương pháp, model hoặc chủ sở hữu từ POST của trình duyệt.

GET tạo snapshot đọc, chỉ hiển thị kết quả nếu cùng tài khoản, đúng tháng hiện tại và đúng fingerprint. Nếu khác, ẩn hoàn toàn ước tính/bảng cũ và yêu cầu tính lại; không chỉ đặt một nhãn nhỏ bên cạnh số cũ. Nếu không kiểm tra được snapshot thì báo chưa hiển thị được kết quả, không dùng cache cũ.

POST tính trên snapshot rồi kiểm lại trong transaction ghi có khóa SQLite. Nếu dữ liệu/xác nhận/cấu hình hoặc tháng đích đổi trong lúc tính, không lưu/công bố kết quả đó. Việc fit nằm ngoài transaction dài để không giữ khóa DB trong suốt tính toán. Không huấn luyện lại lúc mở trang, không tự tính khi đổi giao dịch hoặc tới tháng mới.

Các đường ORM ghi website hiện có đều qua hook. Sửa SQLite trực tiếp/bỏ qua ORM hoặc API nội bộ không phải luồng được hỗ trợ. Khi xóa cascade toàn tài khoản, không tạo lại counter FK tới tài khoản đang bị xóa; kết quả/counter được cascade xóa cùng chủ sở hữu. Chưa có tính năng xóa tài khoản trong giao diện.

## Giao diện và lỗi

Trang **Dự báo** ở `/du-bao/`, yêu cầu đăng nhập, không cache. **Tính dự báo** là POST có CSRF; GET không fit hoặc ghi kết quả. Người dùng khác không có URL/ID để xem cache của nhau; mọi truy vấn dùng `request.user`.

Giao diện hiển thị tháng đích, số tháng hợp lệ, phương pháp, VND, phạm vi lịch sử/thời điểm tính và bảng so sánh sáu ứng viên khi đủ điều kiện. Baseline vẫn mang nhãn thống kê, kể cả khi thắng vòng so sánh có ML. Ridge mới mang nhãn thử nghiệm ML.

Lỗi fit/predict, thư viện/runtime hoặc giá trị không hữu hạn báo chưa tạo được kết quả mới, không fallback im lặng và không lưu kết quả giả. Nếu POST lỗi thì không hiện cache cũ như kết quả vừa tính; cache thành công trước đó không bị xóa, chỉ được dùng lại ở GET khi fingerprint vẫn hợp lệ và có thời điểm tính cũ rõ ràng. Không ghi mô tả hoặc dữ liệu huấn luyện vào log. Không đưa launcher tương thích DLL của nghiên cứu vào web server, không sửa thư viện hoặc cài trong request.

## Tệp thay đổi

- `finance/forecast_config.py`: thiết kế/nhãn phương pháp riêng cho website.
- `finance/forecast_math.py`: baseline, đặc trưng quá khứ, Pipeline, validation và chọn phương pháp.
- `finance/forecasting.py`: snapshot, đủ lịch sử, fingerprint, kiểm tra lại và lưu cache.
- `finance/forecast_state.py`: tăng bộ đếm dữ liệu theo tài khoản.
- `finance/models.py`, `coverage_state.py`, `signals.py`: bảng kết quả/phiên bản và hook vô hiệu cùng transaction.
- `finance/migrations/0005_forecastdataversion_forecastresult.py`, `0006_alter_forecastresult_estimate.py`: migration bảng mới/lưu số chính xác.
- `finance/forecast_views.py`, `finance/urls.py`, `templates/finance/forecast.html`, `templates/base.html`, `static/css/app.css`: giao diện và POST có CSRF.
- `finance/test_forecast.py`, `finance/test_forecast_migration.py`: kiểm thử.
- `README.md`, `docs/forecast-integration.md`: hướng dẫn và tài liệu này.

Không sửa requirements, môi trường, dữ liệu hoặc bất kỳ thí nghiệm MoneyData/phân loại nào. Không tạo dữ liệu demo, model người dùng trên đĩa hoặc deploy. Không commit/push trong TASK 08D.

## Kiểm tra thực tế

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py test --verbosity 1
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py makemigrations --check --dry-run
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate
```

Kiểm thử mới chỉ dùng dữ liệu cố định trong bộ nhớ/test DB: thiếu tháng, không nối qua gap, xác nhận zero, 35/36 tháng, đích hiện tại/đổi năm/nửa đêm Việt Nam khi timezone khác, không dùng tiền hiện tại/tương lai, thu nhập và người khác, tie baseline/alpha, MAE chưa làm tròn, chặn âm trước MAE, sáu mốc chỉ dùng quá khứ, fit cuối khi Ridge thắng, scaler fit trên đúng X quá khứ, mô hình thật khi toàn chuỗi zero vẫn chọn baseline, lỗi ML/NaN không fallback, GET không fit, POST/CSRF/đăng nhập, config/data/xác nhận/tháng đổi ẩn cache, thay đổi trong lúc tính bị từ chối, CSV và rollback/counter, số VND lớn đọc/lưu chính xác, và migration không sửa dòng cũ hoặc tự tạo kết quả.

Ridge/scaler chạy thực tế trong Python `.venv` và các test, không cần launcher DLL, không cài thêm. Các tài khoản/giao dịch thử không vào `db.sqlite3` đang sử dụng. Trước thay đổi có backup riêng ở `backups/task08d-20261020-223311/`, tiếp tục ngoài Git.

Kết quả kiểm tra: **125 kiểm thử Django đạt** (98 hồi quy + 27 mới), **6 kiểm thử JavaScript hồi quy đạt**; system check không có lỗi, không có migration còn thiếu. Migrations 0005 và 0006 đã áp dụng thành công. Kiểm thử ML/pipeline thật nằm trong test DB/bộ nhớ; không tuyên bố điểm test độc lập từ các chuỗi kiểm thử cố định này.

Đối chiếu tài khoản, danh mục, giao dịch, lô CSV/receipt và trạng thái tháng trước/sau: cột cũ, ID, số dòng và giá trị giữ nguyên. Đối chiếu **142 tệp** dữ liệu, mô hình, cấu hình/kết quả thí nghiệm, metadata, script nghiên cứu, requirements và báo cáo MoneyData: SHA-256 không thay đổi. Hai bảng mới vẫn có 0 dòng sau khi chuẩn bị và xem trang, không tự tạo kết quả hoặc counter cho tài khoản thật.

Đã kiểm tra bằng trình duyệt trên `http://127.0.0.1:8001/du-bao/`: hiển thị đúng tháng đích 10/2026, tài khoản hiện có chưa đủ lịch sử và liệt kê các tháng 07/2026–09/2026 cần kiểm tra/xác nhận. Không xác nhận thay người dùng hoặc thêm dữ liệu demo để tạo con số. Ảnh kiểm tra riêng ở thư mục backup, ngoài Git. Trang GET không fit hoặc ghi kết quả.
