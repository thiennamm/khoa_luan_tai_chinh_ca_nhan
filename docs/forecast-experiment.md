# TASK 07B — Thí nghiệm dự báo có điều kiện trên MoneyData

Ngày thực hiện: **20/10/2026**. Run: `task07b-v1`.

**Kết quả chính:** Ridge với alpha=0,1 được chọn bằng MAE validation, nhưng **thua baseline trung bình ba tháng trên test**: MAE **1320,6704** so với **383,9950**, khoảng **3,44 lần**. Không chỉnh mô hình, xóa đỉnh hoặc thay mục tiêu sau khi xem test. Chưa tích hợp website.

## 1. Quyết định nghiên cứu và giới hạn ngay từ đầu

Đã đọc [forecast-data-audit.md](forecast-data-audit.md) và [forecast-monthly-summary.md](metadata/forecast-monthly-summary.md). Theo quyết định TASK 07B, dùng **`swap_numeric_month_day_hypothesis`** để thực hiện một thí nghiệm có điều kiện. Điều này không thay đổi mức xác minh trong báo cáo kiểm định cũ:

- Ngày văn bản được đọc DD/MM/YYYY; ngày số Excel được chuyển sang lịch rồi đổi vị trí month/day. **Đây là giả thuyết xử lý có bằng chứng nội tại, chưa được tác giả xác nhận.** Thứ tự ngày giảm dần, khoảng thời gian và việc không còn ngày cuối tuần hỗ trợ giả thuyết; không chứng minh lịch đã được sửa đúng một cách độc lập.
- Đơn vị tiền gốc **chưa xác minh**; không gọi là GBP hoặc VND và không quy đổi.
- Độ phủ **chưa được xác nhận đầy đủ**. Tháng có bản ghi không đồng nghĩa mọi giao dịch trong tháng đã được ghi nhận.
- **Toàn chuỗi, gồm giai đoạn test, đã được xem trong kiểm định TASK 07A.** Đây là **holdout theo thời gian cho thí nghiệm thăm dò**, không phải đánh giá mù hoàn toàn. Khóa thiết kế trước khi chạy mô hình giúp ngăn điều chỉnh theo lỗi test trong lượt này, không xóa được việc chuỗi từng được khảo sát.

Mục tiêu duy nhất: **tổng Debit Amount quan sát trong workbook theo tháng hạch toán dưới giả thuyết ngày đã chọn**. Giữ các khoản chuyển tiền, tiết kiệm, đầu tư, rút tiền và các debit khác. Không gọi đây là tổng chi tiêu tiêu dùng, toàn bộ chi thực của một người hoặc thu nhập ròng.

## 2. Nguồn và dữ liệu dẫn xuất có phiên bản

Nguồn: **Laramee, Robert (2026), “Bank Transactions Dataset”, Mendeley Data, V1**, [trang chính thức](https://data.mendeley.com/datasets/dnxtg6n4rv/1), [DOI 10.17632/dnxtg6n4rv.1](https://doi.org/10.17632/dnxtg6n4rv.1), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Ghi công tác giả, dẫn nguồn/giấy phép và nêu thay đổi dẫn xuất; không ngụ ý tác giả xác nhận giả thuyết hoặc bảo chứng kết quả.

Workbook: `data/external/moneydata/v1/laramee26openBankTransactionData.xlsx`, **507389 byte**. SHA-256:

`716eaf9ad4a3cf60dc9c9c8a20ed9a917c545a1b5f139f40ed91d2104faa3ff7`

Script dùng bộ đọc ZIP/XML của kiểm định, kiểm hash trước mỗi lần đọc; không mở rồi lưu lại workbook, không nhập SQLite. Bản gốc giữ nguyên byte. Dữ liệu dẫn xuất có mã **`moneydata-v1-swap-monthly-debits-v1`**, lưu riêng trong `data/experiments/forecast/task07b-v1/` ngoài Git.

Đọc số từ chuỗi XML bằng Decimal; giữ quy tắc TASK 07A: làm tròn **từng debit** bằng `quantize(0.01, ROUND_HALF_UP)` rồi cộng theo tháng. Đây là xử lý đuôi độ chính xác lưu Excel đã công bố, không xác nhận đơn vị nhỏ nhất của tiền tệ. Chỉ chuyển tổng tháng sang float64 khi vào mô hình/tính chỉ số; dự báo và chỉ số được tính trước khi làm tròn để hiển thị.

| Phạm vi | Tháng | Giao dịch mọi chiều | Debit | Tổng debit quan sát |
|---|---:|---:|---:|---:|
| Toàn workbook theo nhánh đã chọn | 85 | 6567 | 6122 | 511178.92 |
| Biên 2015-07 bị loại | 1 | 16 | 14 | 1485.87 |
| Biên 2022-07 bị loại | 1 | 79 | 71 | 3652.90 |
| **Đoạn dùng: 2015-08–2022-06** | **83** | **6472** | **6037** | **506040.15** |

**Giữ mọi debit trong 83 tháng**, không loại theo số tiền, danh mục, ứng viên trùng hoặc chiều giao dịch khác. 85 debit ở hai tháng biên chỉ bị loại do quy tắc cắt tháng biên đã chốt. Không trừ credit khỏi debit. Giữ đỉnh **2020-03 = 106341.03** trong lịch sử huấn luyện và mọi ảnh hưởng của nó qua các lag.

Kiểm lại từng tháng từ workbook và đối chiếu số giao dịch/debit/tổng tiền với TASK 07A. Đoạn 83 tháng có bản ghi ở mọi tháng lịch; không điền tháng thiếu bằng 0. Nếu thiếu/nhân đôi/sai thứ tự tháng, script dừng thay vì nối các đoạn hoặc nội suy.

Các tệp dẫn xuất cục bộ:

- `monthly-v1.json`: 83 tháng dùng cho thí nghiệm, số tiền dạng chuỗi Decimal, coverage=unknown.
- `all-observed-months-v1.json`: 85 tháng để bảo toàn dấu vết hai biên.
- `debit-lineage.json`: mỗi debit gốc có số hàng Excel, tháng giả định, số tiền và trạng thái giữ/biên. Không có mô tả hoặc địa điểm; vẫn chỉ lưu ngoài Git.
- `schedule.json`: 24 mốc, tháng cuối lịch sử được phép dùng và số mẫu huấn luyện tại từng mốc.

## 3. Thiết kế khóa trước đánh giá

Cấu hình: [experiments/forecast-v1.json](../experiments/forecast-v1.json). Khóa lúc **2026-10-20T12:53:20.404140+00:00**, tức **19:53:20.404140 giờ Việt Nam**.

| Thành phần | SHA-256 |
|---|---|
| Dữ liệu dẫn xuất `monthly-v1.json` | `d60f5982a7a71ed2066d23ad1cb4df422cb5f53a49786ad18c14cae5ccd56b24` |
| Lịch `schedule.json` | `25630a47be026468420e2b28b47fc91ef37b0aaba324ebe1d836452b3e6909c0` |
| `protocol-lock.json` | `5e2428ff095a3fa35fb393fad979650ea1e4baf70d70bbb434eb15c0b911f7e4` |
| Cấu hình `forecast-v1.json` | `15ce55050ac5b85b7189fc8bd976675ad2388f0e40deeca59a869926bbe04a27` |
| Script chạy thí nghiệm | `8911e5cf1eaef47d8bdf4124bb7750e8dd8d8ab0ca71e40b393ee2d41f2a4638` |

Khóa bao gồm hash workbook, cấu hình, script kiểm định/thí nghiệm, helper tương thích Windows, metadata/tài liệu kiểm định, requirements, dữ liệu dẫn xuất, lineage và lịch. Các phase sau từ chối nếu nguồn/cấu hình/dữ liệu/lịch hoặc runtime đã đổi. Metadata chia sẻ tại [forecast-experiment-protocol.json](metadata/forecast-experiment-protocol.json); không chứa dữ liệu giao dịch theo dòng.

| Phần | Tháng lịch | Số tháng | Vai trò |
|---|---|---:|---|
| Lịch sử ban đầu | 2015-08–2020-06 | 59 | Đủ quá khứ trước validation |
| Validation | 2020-07–2021-06 | 12 | Chọn alpha, mở rộng lịch sử sau từng tháng |
| Test | 2021-07–2022-06 | 12 | Giữ alpha cố định, mở rộng bằng thực tế đã quan sát |

Đây là **24 dự báo một bước**, không phải một dự báo 12 bước tạo từ đầu kỳ. Khi dự báo tháng m, được biết thực tế đến hết m−1; sau đó mới đưa thực tế m vào lịch sử cho m+1. Không dùng dự báo thay cho thực tế đã có, không chọn lại alpha theo lỗi test, không chia giao dịch ngẫu nhiên.

## 4. Đặc trưng và quy trình chỉ dùng quá khứ

Thứ tự cố định:

`[Y_(m−1), Y_(m−2), Y_(m−3), Y_(m−12), mean(Y_(m−1), Y_(m−2), Y_(m−3))]`

Không thêm tháng/năm, credit, số dư, danh mục, số giao dịch tháng đích hoặc đặc trưng khác. Trung bình ba tháng có quan hệ tuyến tính với ba lag đầu; vẫn giữ đúng thiết kế yêu cầu, không bỏ/thay sau khi thấy điểm.

Tại mốc m, tập fit gồm các dòng mục tiêu k từ tháng có đủ 12 lag đầu tiên đến m−1. Mỗi dòng k chỉ sử dụng số liệu trước k. `StandardScaler` chỉ fit trên **X_train của các dòng quá khứ**, không fit chung toàn chuỗi hoặc thêm dòng đặc trưng dùng để predict tháng m.

| Mốc | Tháng lịch sử đã biết | Dòng mục tiêu dùng fit sau warmup |
|---|---:|---:|
| Validation đầu: 2020-07 | 59 | 47 |
| Validation cuối: 2021-06 | 70 | 58 |
| Test đầu: 2021-07 | 71 | 59 |
| Test cuối: 2022-06 | 82 | 70 |

12 tháng đầu chỉ cung cấp lag, không được điền lag bằng 0 để tạo thêm nhãn. Dòng mục tiêu huấn luyện đầu tiên là **2016-08**. Mỗi mốc tạo Pipeline mới, fit lại scaler/Ridge trên lịch sử mở rộng; cập nhật này được thiết kế sẵn, khác với chọn lại siêu tham số.

Các phương pháp cố định:

1. **Tháng trước:** `ŷ_m = Y_(m−1)`.
2. **Trung bình ba tháng trước:** trung bình đúng ba tháng lịch liền trước.
3. **Cùng tháng năm trước:** `ŷ_m = Y_(m−12)`.
4. **StandardScaler + Ridge:** scaler có with_mean=True, with_std=True; Ridge fit_intercept=True, solver=`cholesky`, positive=False; alpha ∈ **{0.1, 1, 10}**, seed=20261020. Cholesky được cố định trước khi chạy, phù hợp ma trận nhỏ năm đặc trưng; không thử solver khác theo điểm.

Theo [tài liệu Pipeline/chống rò rỉ của scikit-learn](https://scikit-learn.org/stable/common_pitfalls.html), các thống kê học từ dữ liệu phải fit trên quá khứ thích hợp; [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html) là hồi quy tuyến tính có phạt L2. Không chuẩn hóa y hoặc áp log/winsorize/xóa đỉnh.

**Quy tắc chặn đã khóa:** `predicted = max(0, raw_prediction)` cho **mọi phương pháp**, trước khi tính chỉ số validation hoặc test. Không có chặn trên. Chọn alpha có **MAE validation sau chặn nhỏ nhất**; hòa chính xác thì alpha nhỏ hơn. Không dùng test để phá hòa.

MAE = trung bình |dự báo−thực tế|; median absolute error = trung vị lỗi tuyệt đối; **sai lệch có dấu = trung bình(dự báo−thực tế)**, dương là dự báo cao. Không báo các chỉ số này dưới dạng phần trăm hay VND. Các bảng dưới làm tròn để đọc; chỉ số được tính trên dự báo float64 chưa làm tròn hiển thị.

## 5. Validation và khóa alpha

Mỗi phương pháp đánh giá đủ 12 mốc giống nhau. Mỗi alpha có **12 lần fit quá khứ**, tổng **36 Pipeline**; baseline không cần fit.

| Phương pháp | MAE | Median absolute error | Sai lệch có dấu | Dự báo âm bị chặn |
|---|---:|---:|---:|---:|
| Tháng trước | 2758,6633 | 2146,4050 | −215,0933 | 0 |
| Trung bình ba tháng | 2153,7175 | 1525,2083 | −204,7542 | 0 |
| Cùng tháng năm trước | 11234,0867 | 2641,1400 | +6546,4800 | 0 |
| **Ridge alpha=0,1** | **1916,3584** | **1336,0520** | **−439,4281** | **1** |
| Ridge alpha=1 | 1919,2695 | 1351,5206 | −435,3412 | 1 |
| Ridge alpha=10 | 1930,3268 | 1434,2778 | −418,3837 | 1 |

Chọn **alpha=0,1**, khóa lúc **2026-10-20T12:53:27.927897+00:00** (19:53:27 giờ Việt Nam). Hash `selection.json`:

`ed1ee60312e10dfa3d3f55f47d44facd5366a40ba425a3c38aa4f4c122729aa3`

Ridge tốt hơn ba baseline về MAE ở validation, nhưng đó không là bảo đảm cho test. Chênh MAE giữa ba alpha khá nhỏ; không thử thêm giá trị sau khi đã chọn.

**Tình huống bất ổn được giữ nguyên:** tại 2021-03, Ridge alpha=0,1 dự báo thô **−52055,1846**, chặn thành **0**, trong khi tổng ghi nợ quan sát là **4750,07**. Hai alpha còn lại cũng âm ở cùng mốc và bị chặn theo cùng quy tắc. Lag 12 ở mốc này là đỉnh 2020-03 đã thấy trong kiểm định. Đây là dấu hiệu giới hạn mô hình trên chuỗi có đỉnh lớn; chưa làm thí nghiệm tách yếu tố để kết luận nguyên nhân. Không loại đỉnh hoặc che giấu dự báo âm thô; cả hai được lưu trong kết quả cục bộ.

## 6. Test sau khi chốt cấu hình

Test bắt đầu lúc **2026-10-20T12:53:40.813993+00:00**, sau khóa alpha, hoàn tất lúc **12:53:41.018021 UTC**. Chỉ Ridge alpha=0,1 được fit lại tại 12 mốc test; không có điểm test cho alpha=1 hoặc 10. Mỗi fit dùng thực tế đã biết trước tháng đích, giữ nguyên cùng quy tắc scaler/đặc trưng/chặn.

**Đơn vị: đơn vị gốc chưa xác minh, không phải VND.**

| Phương pháp | Số mốc | MAE | Median absolute error | Sai lệch có dấu | Âm bị chặn |
|---|---:|---:|---:|---:|---:|
| Tháng trước | 12 | 467,5183 | **356,0850** | +209,2617 | 0 |
| **Trung bình ba tháng** | **12** | **383,9950** | 362,8933 | +257,9433 | 0 |
| Cùng tháng năm trước | 12 | 1994,1250 | 1728,3700 | +1279,3650 | 0 |
| **Ridge alpha=0,1** | **12** | **1320,6704** | **1080,2928** | **+1320,6704** | **0** |

Baseline trung bình ba tháng tốt nhất theo MAE test trong bốn phương pháp; tháng trước tốt nhất theo median absolute error. Không thay tiêu chí chọn alpha từ MAE sang median sau khi thấy test.

### 6.1. Thực tế và dự báo từng tháng test

Số trong bảng chỉ làm tròn hiển thị hai chữ số. Dự báo đã áp dụng chặn âm trước khi chấm.

| Tháng | Thực tế quan sát | Tháng trước | TB 3 tháng | Cùng tháng năm trước | Ridge alpha=0,1 |
|---|---:|---:|---:|---:|---:|
| 2021-07 | 5728.23 | 6724.76 | 5925.20 | 9703.17 | 6722.42 |
| 2021-08 | 5987.18 | 5728.23 | 5917.94 | 3233.46 | 6890.57 |
| 2021-09 | 6515.87 | 5987.18 | 6146.72 | 5655.90 | 6752.63 |
| 2021-10 | 6149.22 | 6515.87 | 6077.09 | 8342.68 | 6724.09 |
| 2021-11 | 5606.01 | 6149.22 | 6217.42 | 11677.41 | 6617.77 |
| 2021-12 | 5586.10 | 5606.01 | 6090.37 | 7050.11 | 6694.87 |
| 2022-01 | 5686.67 | 5586.10 | 5780.44 | 5205.25 | 6738.49 |
| 2022-02 | 4627.71 | 5686.67 | 5626.26 | 6620.44 | 6707.00 |
| 2022-03 | 4943.52 | 4627.71 | 5300.16 | 4750.07 | 6718.65 |
| 2022-04 | 4636.03 | 4943.52 | 5085.97 | 5750.01 | 6657.93 |
| 2022-05 | 4981.55 | 4636.03 | 4735.75 | 5300.83 | 6679.96 |
| 2022-06 | 4213.62 | 4981.55 | 4853.70 | 6724.76 | 6605.38 |

### 6.2. Diễn giải, không điều chỉnh theo test

Ridge có MAE khoảng **3,44 lần** baseline TB ba tháng, dự báo cao ở **cả 12/12 tháng test**, nên sai lệch có dấu bằng MAE. Dự báo Ridge khá phẳng quanh 6605–6891, trong khi thực tế test dao động khoảng 4214–6516. Baseline ngắn hạn bám mức ghi nợ gần thời điểm dự báo tốt hơn trong đoạn này.

Lịch sử có các khoản ghi nợ lớn và nhiều loại luồng tiền, còn số mẫu huấn luyện ít. Đây là những giả thuyết có thể liên quan đến độ bất ổn, không phải bằng chứng rằng một loại giao dịch hay một đỉnh cụ thể là lỗi cần xóa. Không chạy ablation, đổi mục tiêu, bỏ tháng, đổi lag, thử alpha mới hoặc sửa dự báo sau khi thấy test.

Kết quả chỉ hỗ trợ kết luận: **trong thí nghiệm thăm dò đã cố định này, Ridge không cải thiện MAE test so với baseline tháng trước/TB ba tháng**. Không tuyên bố mọi ML đều kém, baseline sẽ luôn thắng, hoặc có khả năng tổng quát hóa sang người khác, dữ liệu Việt Nam hay đơn vị VND.

## 7. Runtime, tệp và tái lập

Python **3.13.16**, scikit-learn **1.9.1**, NumPy **2.5.4**, SciPy **1.18.1**, joblib **1.6.0**, threadpoolctl **3.7.0** trong `.venv`; một luồng. Tái sử dụng helper tương thích Unicode đã có từ TASK 06B trong tiến trình, không sửa package hay cấu hình môi trường. Không cài thêm thư viện.

**48 Pipeline được lưu ngoài Git**: 36 cho validation + 12 cho test. Tổng thời gian fit đo được khoảng **0,0575 giây** validation và **0,0182 giây** test, không tính import, đọc workbook, xử lý dữ liệu, ghi/nén tệp. Số đo mô hình nhỏ này không phải thời gian chạy toàn task hay benchmark phần cứng.

| Tệp | Nội dung |
|---|---|
| `scripts/run_forecast_experiment.py` | Các phase prepare/validate/test/verify |
| `scripts/test_forecast_experiment.py` | Kiểm thử lag, tương lai, lịch thiếu, chặn âm, chọn alpha |
| `experiments/forecast-v1.json` | Thiết kế thống kê/ML và các giới hạn được khóa |
| `docs/forecast-experiment.md` | Báo cáo tổng hợp này |
| `docs/metadata/forecast-experiment-protocol.json` | Nguồn, hash, thời điểm khóa, lịch và số đếm tổng hợp |
| `docs/metadata/forecast-experiment-results.json` | Chỉ số validation, dự báo/thực tế test theo tháng, dấu vết fit; không có mô tả giao dịch |
| `data/experiments/forecast/task07b-v1/` | Dữ liệu dẫn xuất, lineage, lịch, receipt, dự báo validation chi tiết, nhật ký và models; ngoài Git |

SHA-256 `results.json` cục bộ:

`7fcaa287c5febfe1e27e4b01e5fb72e1aff471a1b8f38311718484b9605bf1b7`

Hash từng mô hình và mốc lịch sử fit nằm trong các kết quả cục bộ/JSON tổng hợp test. Không tạo mô hình production hoặc dự báo tháng sau ngoài phạm vi test trong task này.

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'

# Xác minh run có sẵn, không fit/predict thêm.
.\.venv\Scripts\python.exe -X utf8 scripts\run_forecast_experiment.py verify
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s scripts -p 'test_forecast_experiment.py' -v

# Tái lập từ đầu khi cần, dùng thư mục mới để giữ run gốc.
.\.venv\Scripts\python.exe -X utf8 scripts\run_forecast_experiment.py prepare --run-dir data/experiments/forecast/task07b-reproduction
.\.venv\Scripts\python.exe -X utf8 scripts\run_forecast_experiment.py validate --run-dir data/experiments/forecast/task07b-reproduction
.\.venv\Scripts\python.exe -X utf8 scripts\run_forecast_experiment.py test --run-dir data/experiments/forecast/task07b-reproduction
.\.venv\Scripts\python.exe -X utf8 scripts\run_forecast_experiment.py verify --run-dir data/experiments/forecast/task07b-reproduction
```

Run tái lập ở thư mục khác chỉ lưu kết quả cục bộ, không ghi đè metadata công bố của run chính. Prepare có khóa rồi chỉ xác minh; validate không chọn lại sau khi test đã mở; test có kết quả rồi chỉ kiểm receipt, không fit/predict lại. Thời gian/timestamp/hash binary mô hình có thể khác khi chạy lại; hash dữ liệu dẫn xuất và lịch phải tái tạo được với cùng nguồn/cấu hình/script.

## 8. Kiểm tra thực tế và giới hạn còn lại

- **10/10 kiểm thử logic đạt**, không đọc workbook hoặc fit mô hình trong unit test. Có kiểm thay target/tương lai không làm đổi đặc trưng/X/y quá khứ; thiếu tháng hoặc số quá khứ không được điền; clip được áp dụng trước scoring.
- Lệnh verify **đạt**: tái tạo từng byte dữ liệu/lịch/lineage; kiểm nguồn/hash/receipt; đối chiếu chỉ số với dự báo lưu. Kiểm **48 scaler/mô hình**: số mẫu, mean và variance scaler khớp đúng X_train quá khứ của từng mốc, alpha khớp, tháng cuối mục tiêu fit luôn trước tháng đích. Không fit hoặc dự báo lại trong verify.
- Không có cảnh báo trong 36 fit validation và 12 fit test. Khóa alpha trước khi bắt đầu test; các receipt bảo vệ thiết kế/kết quả.
- Bản gốc và mọi debit được bảo toàn trong lineage; chỉ bỏ hai tháng biên theo thiết kế. Không có dữ liệu giao dịch cá nhân hoặc mô tả được chép vào báo cáo.
- Đối chiếu độc lập bằng openpyxl chỉ đọc trong runtime công cụ có sẵn, không cài vào `.venv`: khớp cả **85 tổng tháng và 6122 debit trong lineage**, workbook giữ nguyên SHA-256. Đối chiếu MAE/median/bias bằng `math`/`statistics`, 36 dự báo baseline test theo đúng tháng quá khứ và 12 dự báo Ridge bằng đại số hệ số/scaler đều đạt, không fit lại.
- Rà Git **đạt**: **65 tệp run**, trong đó **48 mô hình** (39844 byte), nằm ngoài Git; không có tệp `data/` đã được theo dõi. Có 6 tệp mới có thể chia sẻ cho TASK 07B. Requirements, `.gitignore`, mã website và các báo cáo/script task trước giữ nguyên; không commit/push.

Các điều chưa xác minh vẫn giữ nguyên: giả thuyết ngày chưa được tác giả xác nhận; mã tiền tệ chưa rõ; độ phủ chưa được chứng nhận; số tài khoản không nhận diện chắc từ workbook. Một chuỗi/một khách hàng theo mô tả nguồn và 12 tháng test đã từng được khảo sát không đủ chứng minh mô hình dùng chung hoặc dự báo toàn bộ chi tiêu thực. Không sửa website, SQLite, môi trường hoặc đặt tính năng dự báo cho người dùng ở bước này.
