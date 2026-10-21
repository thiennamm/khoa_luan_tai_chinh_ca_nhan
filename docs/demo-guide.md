# TASK 09A — Demo dự báo độc lập

## Mục đích và giới hạn

Trang `/du-bao/demo/` yêu cầu đăng nhập, mở bằng nút **Demo dự báo** từ trang Dự báo cá nhân. Đây là **dữ liệu mô phỏng — chỉ để minh họa**, không phải MoneyData hoặc giao dịch thật của người Việt. Không diễn giải điểm trên chuỗi này thành hiệu quả dự báo tài khoản thực.

Kịch bản có 48 tổng chi VND từ **01/2022–12/2025**; tháng đích minh họa cố định **01/2026**, không phụ thuộc ngày hệ thống và không phải tháng hiện tại của tài khoản. Các tháng được **giả định đầy đủ trong kịch bản**, không phải được người dùng xác nhận. Không sinh giao dịch chi tiết hay giá trị thực tế của tháng đích.

## Thiết kế dữ liệu đã cố định trước lượt chạy đầu

Mã nguồn cấu hình và bộ sinh: `finance/forecast_demo.py`, phiên bản **synthetic-vnd-demo-v1**, seed **9048**, bộ sinh riêng `random.Random(9048)`; không thay trạng thái random toàn cục. Seed, công thức và thời gian đã được chốt trước khi chạy bất kỳ phương pháp nào; chỉ dùng một seed, không thử rồi chọn seed làm Ridge thắng.

Với chỉ số tháng `t=0..47`, tiền nguyên VND:

```text
Y[t] = max(0, 6_000_000 + 35_000*t + S[t mod 12] + E[t])
S = [900_000, 400_000, -200_000, -100_000, 0, 200_000,
     300_000, 100_000, -150_000, 0, 250_000, 700_000]
E[t] = lần gọi randint(-600_000, 600_000) thứ t, kể từ seed 9048
```

Số tiền sinh bằng số nguyên rồi chuyển Decimal. Không tự xác nhận coverage, không suy từ giao dịch thật, không lấy dữ liệu hay mô hình từ các thí nghiệm trước. Trên kịch bản v1, không có tổng âm cần chặn.

Hash SHA-256 của 48 cặp tháng/số tiền (JSON `sort_keys=True`, danh sách `{'month': ISO, 'expense': chuỗi Decimal}`, dùng mặc định phân cách của `json.dumps`):

```text
80e9c11c324370fa65ebb8ff2878346c2e70d963b6af43f2a2838bb57d42e04f
```

Giao diện mục mở rộng hiển thị hash dữ liệu và fingerprint. Fingerprint gồm cấu hình demo, hash dữ liệu, thiết kế thuật toán dùng lại, hash mã nguồn, Python và phiên bản thư viện. Mục tiêu trong metadata demo ghi rõ là tháng minh họa cố định. Thay dữ liệu/cấu hình/runtime/mã tương ứng làm cache không còn được hiển thị; GET không tự tính lại.

## Dùng lại TASK 08D và kiểm soát thời gian

`run_demo()` gọi trực tiếp **`finance.forecast_math.calculate(history)`** đang dùng trong TASK 08D. Không sao chép thuật toán và không gọi `snapshot(user)` hay `compute_and_store(user, ...)`. Giữ nguyên `forecast_math.py`, `forecast_config.py`, `forecasting.py` và các kết quả thí nghiệm trước.

- Sáu tháng validation: **07/2025–12/2025**, cuốn chiếu một bước, cập nhật bằng thực tế mô phỏng sau mỗi tháng.
- Lịch sử mốc đầu: 42 tháng 01/2022–06/2025; mốc cuối: 47 tháng 01/2022–11/2025. Chưa bao giờ đưa tháng đích của mỗi mốc vào đầu vào.
- Ba baseline: trung bình 3 tháng, tháng trước, cùng tháng năm trước.
- StandardScaler + Ridge, alpha **0.1, 1, 10**, solver cholesky; đặc trưng lag 1, 2, 3, 12 và trung bình 3 tháng trước.
- Mỗi Pipeline mới fit chỉ các hàng quá khứ của mốc đó. Có 30–35 hàng huấn luyện sau warmup 12 tháng ở mỗi mốc validation, tổng 18 lần fit để so sánh ba alpha.
- Chặn mọi dự báo âm về 0 trước tính MAE. Chọn MAE chưa làm tròn thấp nhất; hòa chính xác ưu tiên TB 3 tháng → tháng trước → cùng tháng năm trước → Ridge alpha nhỏ hơn.
- Sau chọn, dùng đủ 48 tháng để ước tính 01/2026. Chỉ fit Ridge cuối nếu Ridge được chọn (36 hàng sau warmup); không ép chọn ML.

MAE validation được dùng để chọn trên chính sáu tháng này, **không phải sai số test độc lập hay cam kết sai số tương lai**. Không tạo phần trăm chính xác/khoảng tin cậy. Biểu đồ tách đường lịch sử mô phỏng với đường đứt và điểm tròn cam của ước tính; không vẽ dự báo như thực tế. Bảng mở rộng có đủ 48 tổng tháng, không có tổng thực tế 01/2026.

## Kết quả chạy thực tế v1

Chạy ngày 20/10/2026 với Python **3.13.16**, scikit-learn **1.9.1**, NumPy **2.5.4**, SciPy **1.18.1**, không cài thêm thư viện hoặc dùng launcher can thiệp DLL.

| Phương pháp | MAE validation (VND, rút gọn đến 6 số lẻ) |
|---|---:|
| Trung bình 3 tháng | **313373.833333** |
| Tháng trước | 429598.166667 |
| Cùng tháng năm trước | 460417.500000 |
| Ridge alpha 0.1 | 384148.995166 |
| Ridge alpha 1 | 382519.355823 |
| Ridge alpha 10 | 386393.220494 |

Phương pháp thắng: **Ước tính theo trung bình 3 tháng**, không phải Machine Learning. Ước tính minh họa 01/2026: **7.802.124 VND**. Ridge đã chạy thật nhưng không thắng. Đây là kết quả mới của kịch bản v1, không lấy điểm từ MoneyData hoặc thí nghiệm cũ. Giao diện làm tròn MAE nguyên đồng để đọc; bộ chọn dùng giá trị thô.

## Vận hành và tách dữ liệu

- GET/HEAD chỉ dựng chuỗi cố định và đọc cache trong RAM, không fit/ghi kết quả. POST có CSRF mới gọi tính toán, sau thành công redirect GET; mở lại trang không fit lại.
- Cache chỉ chứa một kịch bản mô phỏng chung, không có chủ sở hữu, ID tài khoản, mô tả giao dịch, dữ liệu cá nhân hoặc mô hình đã lưu. Khách đăng nhập khác có thể xem cùng kết quả minh họa; không có kết quả cá nhân trong cache này.
- Cache nằm trong bộ nhớ riêng từng tiến trình máy chủ, không dùng session, SQLite, tệp mô hình hoặc thư mục dữ liệu. Restart/reload hoặc tiến trình khác chưa tính thì cần bấm nút lại. Hai POST đồng thời có thể cùng tính cùng dữ liệu; kết quả tương đương, không thêm bản ghi.
- Không đọc/ghi bảng Transaction, Category, MonthlyCoverage, ForecastDataVersion, ForecastResult hoặc CSV. Không có migration mới; không đổi môi trường/requirements hay thí nghiệm.
- Không nhận seed, số tiền, tháng đích, phương pháp, người dùng, đường dẫn hoặc model từ form. Lỗi ML trả thông báo rõ và HTTP 503; trang lỗi không hiển thị ước tính thay thế, không âm thầm gắn nhãn ML cho baseline. Kết quả cũ hợp lệ trong RAM vẫn có thể được đọc ở GET tiếp theo sau một lần POST lỗi; không được trình bày như lần tính mới thành công.
- Tiền/lỗi baseline dùng Decimal; chỉ Ridge chuyển float64 tại ranh giới đại số như 08D. Tọa độ SVG dùng float riêng để vẽ, không tham gia tính tiền hay chọn phương pháp.

## Kịch bản trình diễn 3–5 phút

1. **0:00–0:40:** Đăng nhập tài khoản đang có, vào Dự báo, bấm liên kết **Demo dự báo**. Đọc nhãn nổi bật và giải thích đây là chuỗi tự sinh độc lập; không cần sửa hay xác nhận lịch sử tài khoản thật.
2. **0:40–1:20:** Chỉ ra lịch sử 48 tháng, giả định đầy đủ và tháng đích cố định **01/2026**. Mở bảng tổng tháng nếu cần. Nhấn mạnh không dùng giao dịch cá nhân, không có thực tế tháng đích.
3. **1:20–2:10:** Bấm nút **Demo dự báo** để chạy thật. Nêu sáu tháng validation, ba đối chứng và ba alpha Ridge, chỉ dùng quá khứ ở mỗi mốc. Khi máy chủ vừa khởi động, GET trước thao tác chưa có ước tính; nếu đã có cache, nút vẫn chạy lại theo cùng cấu hình.
4. **2:10–3:10:** Đọc phương pháp thắng thực tế và bảng MAE. Với v1, TB 3 tháng thắng; Ridge được chạy nhưng không được ưu tiên. MAE chỉ đánh giá quá khứ mô phỏng dùng chọn, không hứa sai số tương lai.
5. **3:10–4:00:** Chỉ điểm cam/đường đứt là ước tính, không phải giá trị thực tế. Mở cấu hình để xem seed/hash. Tải lại trang: đọc kết quả RAM, không huấn luyện lại.
6. **4:00–4:30:** Bấm **Trở về dự báo cá nhân**. Giải thích phần thật vẫn cần lịch sử của tài khoản được xác nhận; demo không thêm giao dịch, coverage hay kết quả vào tài khoản.

## Kiểm tra chạy lại

Từ thư mục dự án trong PowerShell, không cần activate venv:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 manage.py test finance.test_forecast_demo
& '.\.venv\Scripts\python.exe' -X utf8 manage.py test
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py makemigrations --check --dry-run
```

12 kiểm thử demo: 48 tháng/seed/hash/Decimal; hai lần chạy thật (dung sai MAE và dự báo thô **0.001 VND**, phương pháp/ước tính nguyên đồng phải giống); quá khứ ở mọi mốc, thay điểm cuối không đổi dự báo sớm; biểu đồ tách ước tính; đăng nhập/CSRF; GET không ghi hoặc tính; POST không sửa bất kỳ nội dung dòng nào của hai tài khoản; cache chung không lộ dữ liệu cá nhân; đổi cấu hình ẩn cache; lỗi ML; dùng lại hàm lõi; không hỗ trợ PUT. Bản ghi tài khoản trong kiểm thử chỉ ở DB test riêng, không đưa vào website thật.

Kết quả thực tế ngày 20/10/2026:

- **137/137 kiểm thử Django đạt**, gồm 12 kiểm thử demo mới; **6/6 kiểm thử JavaScript** của biểu mẫu gợi ý phân loại đạt.
- Django system check: không có vấn đề. `makemigrations --check --dry-run`: không có thay đổi. Không cần migration hoặc thêm dependency.
- Trình duyệt đăng nhập tại `http://127.0.0.1:8001/du-bao/demo/`: GET đầu chỉ có lịch sử, chưa có ước tính; bấm POST chạy thành công, đúng TB 3 tháng/7.802.124 VND, đủ sáu dòng so sánh và điểm ước tính riêng. Đã thử nút quay về dự báo cá nhân rồi mở lại demo, kết quả RAM còn nguyên.
- Đối chiếu trước/sau thao tác thật: **8 bảng tài khoản/finance không đổi số lượng hoặc nội dung dòng** (so sánh hash toàn dòng, gồm giao dịch, coverage, counter và kết quả cá nhân). Không ghi dữ liệu tài khoản vào báo cáo này.
- **137 tệp được bảo vệ giữ nguyên SHA-256**, gồm dữ liệu/mô hình, thí nghiệm, metadata, requirements và thuật toán 08D. Sao lưu SQLite và bằng chứng đối chiếu nằm riêng ở `backups/task09a-20261020-230038/`, đã bị Git ignore.
- Máy chủ phát triển tiếp tục chạy cục bộ tại cổng 8001; chưa deploy, chưa commit hoặc push trong task này.

Tệp thêm: `finance/forecast_demo.py`, `finance/forecast_demo_views.py`, `finance/test_forecast_demo.py`, `templates/finance/forecast_demo.html`, tài liệu này. Tệp cập nhật: `finance/urls.py`, `templates/finance/forecast.html`, `templates/base.html`, `static/css/app.css`, `README.md`. Không sửa `.gitignore`, schema, logic dự báo lõi hoặc báo cáo thí nghiệm.
