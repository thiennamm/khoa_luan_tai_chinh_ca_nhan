# TASK 06B — Thí nghiệm phân loại đầu tiên

Ngày thực hiện: **20/10/2026**. Thí nghiệm `task06b-v1-final`, chạy bằng Python trong `.venv`, chưa tích hợp website hoặc đặt ngưỡng tự gán danh mục.

**Kết quả:** TF-IDF ký tự + LinearSVC, C=10 được chọn bằng validation. Test đã khóa có **accuracy 0,993086, macro-F1 0,993832, sai 42/6075 mẫu**. Dummy có accuracy 0,097119, macro-F1 0,010414. Đây là kết quả trên bộ tổng hợp tiếng Anh và cách chia nhóm đã mô tả, chưa chứng minh hiệu quả trên giao dịch thật hoặc tiếng Việt.

## 1. Phạm vi và nguồn đã khóa

Đã đọc [báo cáo kiểm định TASK 06A](classification-data-audit.md) và [script kiểm định](../scripts/audit_classification_data.py). Chỉ dùng **DoDataThings v2, dữ liệu tổng hợp tiếng Anh**; không dùng MoneyData, dữ liệu website, giao dịch tiếng Việt, dữ liệu dịch hoặc dữ liệu tự sinh.

- Revision: `3e8d052cb7b362fb1a04b6064d2331982553ea56`.
- CSV SHA-256: `0424aed6e76f74a5b3b1ff61ccec43bc321622e6806da353b910b3b2c8108f6e`.
- [CSV nguồn chính thức tại revision](https://huggingface.co/datasets/DoDataThings/us-bank-transaction-categories-v2/resolve/3e8d052cb7b362fb1a04b6064d2331982553ea56/transactions-synthetic.csv), [card nguồn](https://huggingface.co/datasets/DoDataThings/us-bank-transaction-categories-v2/blob/3e8d052cb7b362fb1a04b6064d2331982553ea56/README.md).
- Giấy phép nguồn khai báo MIT; giữ ghi công/card và các lưu ý về thông báo bản quyền còn thiếu trong TASK 06A. Không phân phối CSV trong Git.
- SHA-256 manifest nhóm gốc 06A: `20140ec9b6775e1ded63c88aea2b4e3bb0c7434c41ead03809bc10fea2c36121`.

Script xác minh CSV, hash script 06A và metadata; dựng lại quan hệ thân mô tả/mẫu/cặp gần giống để **đối chiếu** với thành phần nhóm 06A. Sau đối chiếu, tái sử dụng nguyên `group_id` của manifest gốc, không tạo lại ID từ tập đã lọc. Các số loại/dòng được tự đếm rồi so với bằng chứng kiểm định, không hardcode số 6/38 để ép kết quả.

## 2. Chuẩn bị dữ liệu

1. Gỡ đúng **một tiền tố ở đầu** bằng regex `^\s*\[(debit|credit)\]\s*`, không phân biệt hoa/thường; không xóa từ debit/credit nằm bên trong mô tả.
2. Dùng chính `audit.body`: Unicode NFC → `casefold()` → gộp khoảng trắng Unicode/bỏ khoảng trắng hai đầu, **giữ dấu câu**. Đây cũng là văn bản đầu vào cho hai mô hình. Không dùng khóa mẫu đã che số làm đầu vào mô hình; khóa mẫu chỉ phục vụ nhóm/chống giao nhau.
3. Gom theo thân mô tả chuẩn hóa. Nếu một thân có nhiều nhãn, **cách ly toàn bộ các dòng của thân đó trước khi loại trùng**, không bỏ phiếu nhãn đa số.
4. Với mỗi thân còn lại, giữ bản ghi có **ID CSV nhỏ nhất** (bắt đầu 1, không tính header). Đại diện giữ nhãn gốc và `group_id` gốc. Không gộp nhãn, sửa nhãn, dịch, cân bằng bằng tăng mẫu hoặc sinh dữ liệu.

Kết quả: từ **68.000 dòng / 40.512 thân mô tả**, cách ly **6 nhóm / 38 dòng**, bỏ thêm **27.456 dòng lặp** trong phần không mâu thuẫn, giữ **40.506 mẫu**. Ba lý do trạng thái được lưu riêng cho mọi ID gốc: `quarantined_conflict`, `duplicate_removed`, `retained`. Không cộng trùng dòng đã cách ly vào số loại trùng.

| Nhãn | Dòng gốc | Cách ly mâu thuẫn | Loại trùng sau cách ly | Mẫu giữ lại |
|---|---:|---:|---:|---:|
| Education | 4000 | 0 | 2464 | 1536 |
| Entertainment | 4000 | 0 | 2062 | 1938 |
| Fees | 4000 | 0 | 2762 | 1238 |
| Groceries | 4000 | 0 | 527 | 3473 |
| Healthcare | 4000 | 14 | 1957 | 2029 |
| Income | 4000 | 0 | 1876 | 2124 |
| Insurance | 4000 | 0 | 1062 | 2938 |
| Mortgage | 4000 | 0 | 2598 | 1402 |
| Personal Care | 4000 | 18 | 1878 | 2104 |
| Rent | 4000 | 0 | 2344 | 1656 |
| Restaurants | 4000 | 0 | 432 | 3568 |
| Shopping | 4000 | 6 | 64 | 3930 |
| Subscription | 4000 | 0 | 1949 | 2051 |
| Transfer | 4000 | 0 | 1484 | 2516 |
| Transportation | 4000 | 0 | 1136 | 2864 |
| Travel | 4000 | 0 | 1816 | 2184 |
| Utilities | 4000 | 0 | 1045 | 2955 |
| **Tổng** | **68000** | **38** | **27456** | **40506** |

Sau loại trùng, các lớp **không còn cân bằng**. Số liệu đánh giá áp dụng cho mỗi thân mô tả duy nhất, không đại diện trọng số tần suất giao dịch thật. Nhóm ứng viên nhiều nhãn theo heuristic nhưng **khác thân mô tả** vẫn được giữ nguyên; chúng có thể là va chạm mẫu câu thay vì lỗi nhãn. Chỉ cách ly điều kiện mâu thuẫn cùng thân mà người dùng yêu cầu.

## 3. Chia nhóm, phân tầng và khóa test

Từ 22.243 nhóm gốc, còn **22.239 ID nhóm** có ít nhất một đại diện. Nếu bản ghi từng tạo ID nhóm bị loại, ID đó vẫn được giữ cho thành viên sống sót; không thay bằng hash mới. Các nhóm không bị tách nhỏ để cân bằng lớp.

Seed cố định: **20261020**. Thuật toán đếm nhãn `greedy-group-label-squared-deficit-v2-local-moves`:

- Mỗi nhóm có vector số mẫu của 17 lớp. Mục tiêu mỗi lớp và tổng số mẫu là tỷ lệ **0,70/0,15/0,15**.
- Xếp nhóm khó/lớn trước theo tỷ trọng lớn nhất trong một lớp, rồi kích thước nhóm; phá hòa bằng SHA-256 của `seed|group_id`.
- Phân nhóm bằng mức tăng nhỏ nhất của hàm mất cân bằng: trung bình sai lệch bình phương từng lớp đã chia cho bình phương tổng lớp, cộng sai lệch bình phương kích thước từng tập chia cho bình phương tổng mẫu, trọng số kích thước 1.
- Chạy đúng **3 lượt cải thiện cố định**, chỉ chuyển **nguyên nhóm** khi giảm cùng hàm đếm nhãn trên. Không có đặc trưng học được hoặc điểm mô hình trong thuật toán. Không tìm nhiều seed rồi chọn theo test.

Bản chuẩn bị thử chỉ có bước greedy bị lệch lớp Fees. **Trước mọi lần fit**, bổ sung ba lượt chuyển nguyên nhóm theo số lượng nhãn và tạo bản khóa cuối. Bản thử `data/experiments/classification/task06b-v1/` được giữ với cấu hình, script snapshot và manifest riêng; **không có mô hình hoặc lần mở test**. Chỉ bản `task06b-v1-final` dưới đây được dùng cho thí nghiệm.

| Tập | Mẫu | Tỷ lệ mẫu | ID nhóm |
|---|---:|---:|---:|
| Train | **28356** | **70,0044%** | **11261** |
| Validation | **6075** | **14,9978%** | **5506** |
| Test | **6075** | **14,9978%** | **5472** |

| Nhãn | Train | Validation | Test |
|---|---:|---:|---:|
| Education | 1075 | 231 | 230 |
| Entertainment | 1356 | 291 | 291 |
| Fees | 866 | 186 | 186 |
| Groceries | 2431 | 521 | 521 |
| Healthcare | 1420 | 305 | 304 |
| Income | 1487 | 319 | 318 |
| Insurance | 2057 | 440 | 441 |
| Mortgage | 982 | 210 | 210 |
| Personal Care | 1473 | 316 | 315 |
| Rent | 1161 | 247 | 248 |
| Restaurants | 2498 | 535 | 535 |
| Shopping | 2750 | 590 | 590 |
| Subscription | 1436 | 308 | 307 |
| Transfer | 1761 | 377 | 378 |
| Transportation | 2005 | 429 | 430 |
| Travel | 1529 | 327 | 328 |
| Utilities | 2069 | 443 | 443 |

Thời điểm khóa cuối: **2026-10-20T09:32:19.726732+00:00**, tức **16:32:19.726732 giờ Việt Nam**. Manifest nằm cục bộ, gồm ID đại diện, nhãn, ID nhóm, hash thân mô tả và phân vùng; văn bản nằm ở các tệp dữ liệu cục bộ riêng.

| Đối tượng khóa | SHA-256 |
|---|---|
| `manifest.json` | `49f3153aa4115e5252830c43be5d20dd4cba6d7d404d75245816d86a96ea833f` |
| `split-lock.json` | `cba62d5e22f8fc08979f33dd4c2dd47e8b8812ae06c25705330ed9ff1a429b92` |
| Cấu hình `experiments/classification-v1.json` | `ae7c36b6fae2210164a9277cce2a225cb66e668292a8f593a5e3b5d0ac43f758` |
| Script thí nghiệm đã khóa | `8b869ce54d9d0aff244b8bc16638288a2dace06bfccb3dcc3256c8361b9a8bac` |

`split-lock.json` khóa cả hash CSV, script/metadata 06A, manifest nhóm/cặp gần giống, cấu hình, script thí nghiệm, quyết định loại và ba tệp train/validation/test. Có receipt SHA-256 riêng. Các giai đoạn sau từ chối nếu chúng thay đổi. Thống kê chia và hash có thể chia sẻ ở [classification-experiment-data.json](metadata/classification-experiment-data.json).

**Kiểm tra giao nhau:** bằng 0 theo ID nhóm, mô tả nguyên văn, chuẩn hóa có tiền tố, thân mô tả bỏ tiền tố và khóa mẫu. Kiểm cả các đại diện và dữ liệu gốc được chiếu lên phân vùng của ID nhóm sống sót, để không mất quan hệ khi đại diện/đầu mút đã bị loại. Kiểm đủ **832 cạnh gần giống gốc, 0 cạnh đi qua hai tập**. Đã đối chiếu lại thành phần liên thông với nhóm 06A. Đây **không phải merchant holdout**; không có merchant ID đã xác minh, còn có thể rò rỉ merchant/họ mẫu ngoài heuristic.

## 4. Cấu hình và quy tắc chọn trước khi xem test

Cấu hình máy đọc được: [experiments/classification-v1.json](../experiments/classification-v1.json). Cố định **C ∈ {0.1, 1.0, 10.0}**, đúng 3 giá trị cho mỗi họ, không thử n-gram hoặc seed khác theo kết quả. Không dùng oversampling/class weighting.

| Họ | Đặc trưng | Bộ phân loại | Tham số cố định |
|---|---|---|---|
| Dummy | Bỏ qua nội dung | `DummyClassifier(strategy="most_frequent")` trong Pipeline | Seed 20261020, chỉ học lớp đông nhất train |
| `word_logreg` | TF-IDF từ, n-gram (1,2) | LogisticRegression, L2 mặc định của phiên bản đang dùng | min_df=2, max_features=60000, sublinear_tf=True; solver=lbfgs, max_iter=500, tol=1e-4 |
| `char_linearsvc` | TF-IDF `char_wb`, n-gram (3,5) | LinearSVC | min_df=2, max_features=80000, sublinear_tf=True; dual=auto, max_iter=5000, tol=1e-4 |

Hai TF-IDF dùng norm L2, smooth_idf=True, kiểu số mặc định float64; lowercase=False vì đầu vào đã casefold theo quy tắc chung. Không có tiền tố chiều tiền trong đầu vào. Số float của TF-IDF/chỉ số mô hình là số tính toán ML, không liên quan yêu cầu Decimal cho số tiền website; dữ liệu này không có cột tiền.

Mỗi ứng viên là **Pipeline**, chỉ gọi `fit` bằng train; TF-IDF học từ vựng, tần suất IDF và giới hạn đặc trưng từ train, rồi chỉ `transform/predict` trên validation. Quy trình tuân theo [hướng dẫn tránh rò rỉ của scikit-learn](https://scikit-learn.org/stable/common_pitfalls.html). Dummy dùng Pipeline một bước vì không cần học đặc trưng văn bản.

Chọn **macro-F1 validation cao nhất** giữa các mô hình học. Hòa chính xác thì chọn C nhỏ hơn, tiếp theo thứ tự word_logreg trước char_linearsvc. Dummy là mốc đối chứng, không ứng viên để chọn mô hình học. Accuracy validation được ghi lại để mô tả nhưng **không dùng phá hòa**. Khóa `validation-selection.json` và receipt trước khi `evaluate` được phép đọc/chấm test.

Không refit bằng train+validation sau lựa chọn: mô hình được đánh giá là Pipeline đã fit trên train. Không gọi predict/score test cho các cấu hình thua. `decision_function` không được dùng để chọn ngưỡng hoặc diễn giải là xác suất/độ tin cậy đã hiệu chỉnh; không hiệu chỉnh xác suất trong thí nghiệm này. [Tài liệu LinearSVC](https://scikit-learn.org/stable/modules/generated/sklearn.svm.LinearSVC.html) mô tả phương thức decision_function riêng với nhãn dự đoán.

### 4.1. Runtime và lỗi đường dẫn Windows đã xử lý

Python **3.13.16**, scikit-learn **1.9.1**, NumPy **2.5.4**, SciPy **1.18.1**, joblib **1.6.0**, threadpoolctl **3.7.0** trong `.venv`, Windows x64. Không cài hoặc nâng cấp gói. Giới hạn tính toán **1 luồng**.

Lần khởi động train trực tiếp dừng ở `threadpool_limits` **trước vòng fit ứng viên**: đường DLL trong snapshot Windows bị mất dấu tiếng Việt. Thêm launcher [run_classification_windows.py](../scripts/run_classification_windows.py) xử lý **trong tiến trình**: giữ module handle, bỏ chuỗi đường snapshot và để resolver wide-character `GetModuleFileNameW/GetModuleFileNameExW` sẵn có lấy đúng đường Unicode. Không sửa `site-packages`, môi trường toàn máy, cấu hình mô hình hoặc split đã khóa.

Launcher ghi hash mã tương thích, hash nguồn thư viện và receipt trước lần fit đầu tại [classification-experiment-runtime.json](metadata/classification-experiment-runtime.json); đã xác minh các pool OpenMP/OpenBLAS là 1 luồng trong context giới hạn. Đây là sửa khả năng chạy trên máy, không thay đổi dữ liệu/seed/cách chọn mô hình. Giữ script chính đã khóa không đổi.

## 5. Validation và lựa chọn cuối

| Cấu hình | C | Accuracy validation | Macro-F1 validation | Fit Pipeline, giây |
|---|---:|---:|---:|---:|
| Dummy most_frequent | — | 0,097119 | 0,010414 | 0,126 |
| TF-IDF từ + LogisticRegression | 0,1 | 0,731523 | 0,775235 | 3,061 |
| TF-IDF từ + LogisticRegression | 1 | 0,907490 | 0,917349 | 5,081 |
| TF-IDF từ + LogisticRegression | 10 | 0,949465 | 0,954734 | 5,908 |
| TF-IDF ký tự + LinearSVC | 0,1 | 0,966584 | 0,969465 | 5,654 |
| TF-IDF ký tự + LinearSVC | 1 | 0,984691 | 0,985693 | 6,399 |
| **TF-IDF ký tự + LinearSVC** | **10** | **0,986996** | **0,987756** | **9,635** |

Đã fit **7 Pipeline**: Dummy + đúng 3 C cho mỗi họ. Không có cảnh báo, bao gồm cảnh báo hội tụ. Số vòng lặp LogisticRegression theo C tăng dần là 41/78/95; LinearSVC là 13/44/344. Từ vựng thực học trên train: **8.063 đặc trưng từ**, **66.768 đặc trưng ký tự**. Không thử thêm sau khi xem test.

Tổng thời gian fit: **35,864 giây**, đo bằng `perf_counter`, gồm fit TF-IDF và bộ phân loại ở từng ứng viên, không gồm import, chuẩn bị/chia dữ liệu, dự đoán hoặc nén/lưu mô hình. Đây là số đo trên máy này, một luồng, không là cam kết tốc độ ở máy khác.

Lựa chọn khóa lúc **2026-10-20T09:35:46.887622+00:00** (16:35:46 giờ Việt Nam): `char_linearsvc_C_10p0`. SHA-256 lựa chọn: `e9c05cf8edd323ad80b9beb4d770fbfec407ea33fd8615bea1d43d2e875b508b`.

Test được mở để chấm lúc **2026-10-20T09:37:12.534557+00:00**, sau khóa lựa chọn. Chuẩn bị dùng nhãn toàn nguồn để cách ly/phân tầng như đã công bố; trong chọn cấu hình chỉ parse train/validation, không predict/score test. Kiểm hash test để bảo vệ tính toàn vẹn không phải dùng test chọn mô hình. Nhật ký ghi thứ tự khóa split → 7 fit hoàn tất → khóa lựa chọn → đánh giá test.

## 6. Đánh giá cuối trên test

Chỉ chấm **Dummy** và **mô hình được chọn**. Không có điểm test cho LogisticRegression hoặc các C còn lại. Không refit, thay nhãn, đổi split/config sau khi thấy test.

| Mô hình | Accuracy | Macro-F1 | Đúng / Tổng | Lỗi | Fit, giây | Predict test, giây |
|---|---:|---:|---:|---:|---:|---:|
| Dummy most_frequent | 0,097119 | 0,010414 | 590 / 6075 | 5485 | 0,126 | 0,004 |
| **TF-IDF ký tự + LinearSVC, C=10** | **0,993086** | **0,993832** | **6033 / 6075** | **42** | **9,635** | **0,331** |

Accuracy là tỷ lệ mẫu đúng; macro-F1 là trung bình F1 đủ 17 lớp, mỗi lớp trọng số ngang nhau. Support là số mẫu của lớp trong test đã loại trùng. Số đầy đủ và ma trận nằm ở [classification-experiment-results.json](metadata/classification-experiment-results.json).

### 6.1. Precision/recall/F1 từng lớp — mô hình được chọn

| Nhãn | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Education | 1,000000 | 1,000000 | 1,000000 | 230 |
| Entertainment | 1,000000 | 1,000000 | 1,000000 | 291 |
| Fees | 1,000000 | 1,000000 | 1,000000 | 186 |
| Groceries | 0,990385 | 0,988484 | 0,989433 | 521 |
| Healthcare | 0,983766 | 0,996711 | 0,990196 | 304 |
| Income | 0,996805 | 0,981132 | 0,988906 | 318 |
| Insurance | 0,993243 | 1,000000 | 0,996610 | 441 |
| Mortgage | 1,000000 | 0,971429 | 0,985507 | 210 |
| Personal Care | 1,000000 | 1,000000 | 1,000000 | 315 |
| Rent | 1,000000 | 0,995968 | 0,997980 | 248 |
| Restaurants | 0,983456 | 1,000000 | 0,991659 | 535 |
| Shopping | 0,993031 | 0,966102 | 0,979381 | 590 |
| Subscription | 0,983974 | 1,000000 | 0,991922 | 307 |
| Transfer | 0,986877 | 0,994709 | 0,990777 | 378 |
| Transportation | 0,997680 | 1,000000 | 0,998839 | 430 |
| Travel | 0,987952 | 1,000000 | 0,993939 | 328 |
| Utilities | 1,000000 | 1,000000 | 1,000000 | 443 |

### 6.2. Precision/recall/F1 từng lớp — Dummy

Dummy chỉ dự đoán Shopping, lớp đông nhất train. Dùng `zero_division=0`: precision không xác định ở lớp chưa bao giờ được dự đoán được ghi 0 theo quy ước tính chỉ số.

| Nhãn | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Education | 0 | 0 | 0 | 230 |
| Entertainment | 0 | 0 | 0 | 291 |
| Fees | 0 | 0 | 0 | 186 |
| Groceries | 0 | 0 | 0 | 521 |
| Healthcare | 0 | 0 | 0 | 304 |
| Income | 0 | 0 | 0 | 318 |
| Insurance | 0 | 0 | 0 | 441 |
| Mortgage | 0 | 0 | 0 | 210 |
| Personal Care | 0 | 0 | 0 | 315 |
| Rent | 0 | 0 | 0 | 248 |
| Restaurants | 0 | 0 | 0 | 535 |
| Shopping | 0,097119 | 1,000000 | 0,177044 | 590 |
| Subscription | 0 | 0 | 0 | 307 |
| Transfer | 0 | 0 | 0 | 378 |
| Transportation | 0 | 0 | 0 | 430 |
| Travel | 0 | 0 | 0 | 328 |
| Utilities | 0 | 0 | 0 | 443 |

### 6.3. Ma trận nhầm lẫn

[Hai ma trận đầy đủ 17×17](metadata/classification-test-confusion.md): hàng là nhãn thật, cột là dự đoán, ô là số mẫu. Có bảng mã L01–L17. JSON kết quả cũng chứa cả hai ma trận và thứ tự nhãn; tổng ô mỗi ma trận là 6.075. Không biểu diễn các ô như xác suất.

Một số cặp sai của mô hình được chọn:

| Nhãn thật | Dự đoán | Số mẫu |
|---|---|---:|
| Shopping | Travel | 4 |
| Shopping | Subscription | 4 |
| Shopping | Healthcare | 4 |
| Shopping | Groceries | 4 |
| Mortgage | Transfer | 4 |
| Groceries | Restaurants | 4 |
| Shopping | Restaurants | 3 |

## 7. Phân tích lỗi sau đánh giá — không sửa test

Trong 42 lỗi, xếp theo SHA-256 UTF-8 `task06b-errors-v1|record_id`, lấy **12 lỗi đầu**. Đã đọc cả 12; văn bản đầy đủ chỉ lưu cục bộ `error-sample.json`. Đây là mẫu minh họa, không ước lượng tỷ lệ nguyên nhân. Nhãn thật dưới đây là **nhãn nguồn**, chưa có hóa đơn/chủ giao dịch xác nhận.

| ID CSV | Mô tả tổng hợp rút gọn, giữ tiếng Anh | Nhãn nguồn → Dự đoán | Nhận xét |
|---|---|---|---|
| 1490, 47847 | `walgreens #6696 tampa`; `payment to: walgreens` | Shopping → Healthcare | Tên chồng lấn bán lẻ/y tế. Train có substring walgreens ở 36 mẫu Healthcare và 6 Shopping. Cách ly thân mâu thuẫn không loại hết biến thể khác thân của cùng tên. |
| 65877, 1919, 65842 | `anthropologie...` | Shopping → Subscription | Train không có substring anthropologie, có 10 mẫu anthropic thuộc Subscription. Có thể mô hình ký tự nhầm tên gần nhau; chưa có phân tích đóng góp đặc trưng để xác nhận nguyên nhân. |
| 91 | `etsy payout` | Income → Shopping | Tên nền tảng có vai trò mua hàng và nhận tiền bán hàng. Train có etsy ở 9 mẫu Income, 5 Shopping; ngữ cảnh payout chưa được xử lý đúng ở mẫu này. |
| 4376 | `doordash payout` | Income → Restaurants | Train có doordash ở 12 mẫu Restaurants và 8 Income. Bỏ tiền tố chiều tiền đòi hỏi phân biệt ngữ cảnh, không chỉ tên nền tảng. |
| 26154 | `mtg pmt flagstar bank` | Mortgage → Transfer | Viết tắt/tên ngân hàng xuất hiện trong nhiều luồng tiền; chưa xác định đặc trưng trực tiếp gây sai. |
| 159 | `withdrawal from united wholesale mtg pymt` | Mortgage → Insurance | Wrapper Withdrawal và viết tắt chưa bảo đảm dự đoán đúng; không đổi nhãn theo dự đoán. |
| 533, 341 | `sq *produce market`; `sq *organic farm` | Groceries → Restaurants / Insurance | Wrapper SQ không xác định mục đích. Tên chung ít thông tin; không coi dự đoán là bằng chứng nhãn nguồn sai. |
| 24762 | `american eagle ... philadelphia ...` | Shopping → Groceries | Mô tả nhiều địa chỉ/nhiễu. Chưa thể khẳng định riêng địa chỉ gây lỗi nếu chưa có thí nghiệm tách yếu tố. |

Đếm substring trong train chỉ hỗ trợ mô tả lỗi, **không phải định danh merchant đã xác minh**. Không bổ sung quy tắc, đổi C, thêm tiền tố, sửa nhãn hoặc chia lại test sau phân tích. Muốn thử giả thuyết lỗi cần thí nghiệm mới và chính sách đánh giá độc lập; test hiện tại đã được xem.

## 8. Giới hạn kết luận

- Dữ liệu tổng hợp tiếng Anh theo định dạng Mỹ, taxonomy cố định, không có tiền/ngày/người. Không chứng minh hiệu quả trên ghi chú tiếng Việt, sao kê thật, ngân hàng khác hoặc phân bố lớp thực.
- Đã tuyển chọn benchmark bằng loại trùng/cách ly mâu thuẫn cùng thân; chỉ số không đo khả năng giải quyết các trường hợp bị cách ly trong thực tế.
- Nhóm chỉ kiểm soát quan hệ heuristic 06A, **không bảo đảm tách merchant**. Tên merchant và quy luật bộ sinh có thể còn chung giữa train/test; rò rỉ merchant/mẫu chưa phát hiện có thể làm điểm lạc quan.
- Một seed/một cách chia, chưa có tập thật độc lập, khoảng tin cậy hoặc bằng chứng ổn định qua nhiều tập. Điểm 1,0 ở một số lớp không chứng minh không bao giờ sai.
- Không hiệu chỉnh xác suất, không đặt ngưỡng/tự động gán hoặc đánh giá từ chối. **Decision score không là xác suất hoặc độ tin cậy đã hiệu chỉnh.**
- Transfer vẫn chỉ là nhãn nguồn, không tự coi là chi tiêu hoặc ánh xạ vào danh mục chi của website.

## 9. Tệp và cách chạy lại

Thư mục cục bộ chính: `data/experiments/classification/task06b-v1-final/`. Bản ghi, quyết định loại theo dòng, manifest theo dòng, dự đoán và mô hình đều nằm trong `data/` ngoài Git.

| Tệp | Vai trò |
|---|---|
| `experiments/classification-v1.json` | Cấu hình cố định, có thể chia sẻ |
| `scripts/run_classification_experiment.py` | Chuẩn bị, khóa, train/validation, evaluate, verify |
| `scripts/run_classification_windows.py` | Launcher tương thích Unicode, dùng trên máy hiện tại |
| `scripts/test_classification_experiment.py` | Kiểm thử logic, không fit hoặc đọc website |
| `docs/metadata/classification-experiment-data.json` | Thống kê lọc/chia và hash manifest/lock |
| `docs/metadata/classification-experiment-runtime.json` | Receipt tương thích và giới hạn luồng trước fit |
| `docs/metadata/classification-experiment-results.json` | Validation 7 ứng viên, test đúng 2 mô hình, chỉ số/ma trận |
| `docs/metadata/classification-test-confusion.md` | Hai ma trận đầy đủ |
| Cục bộ `manifest.json`, `row-decisions.json`, `train.json`, `validation.json`, `test.json` | Dữ liệu/ID/quyết định; ngoài Git |
| Cục bộ `split-lock.json`, các receipt `.sha256`, `validation-selection.json`, `test-opened.json`, `events.jsonl` | Khóa và trình tự thực thi |
| Cục bộ `models/*.joblib`, `candidates/*.json` | 7 Pipeline và checkpoint/hash; ngoài Git |
| Cục bộ `test-predictions.json`, `error-sample.json`, `test-results.json` | Dự đoán, mẫu lỗi và kết quả; ngoài Git |

SHA-256 kết quả test cục bộ: `2c785469f424dea9346f7dd2741941f6cc872929c1ff0212f631f41fe2ceb96a`. Hash từng mô hình nằm trong JSON kết quả. Giữ receipt và manifest khi sao lưu thủ công thư mục ngoài Git.

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'

# Kiểm tra run hiện có; không fit hoặc predict test lại.
.\.venv\Scripts\python.exe -X utf8 scripts\run_classification_windows.py verify
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s scripts -p 'test_classification_experiment.py' -v

# Tái lập từ đầu khi cần, trong thư mục MỚI; không sửa run gốc.
.\.venv\Scripts\python.exe -X utf8 scripts\run_classification_windows.py prepare --run-dir data/experiments/classification/task06b-reproduction
.\.venv\Scripts\python.exe -X utf8 scripts\run_classification_windows.py train --run-dir data/experiments/classification/task06b-reproduction
.\.venv\Scripts\python.exe -X utf8 scripts\run_classification_windows.py evaluate --run-dir data/experiments/classification/task06b-reproduction
.\.venv\Scripts\python.exe -X utf8 scripts\run_classification_windows.py verify --run-dir data/experiments/classification/task06b-reproduction
```

Prepare gặp run đã khóa chỉ kiểm tra, không thay split. Train từ chối nếu test đã mở; evaluate đã có kết quả thì không predict lại. Một run mới sẽ xuất metadata tổng hợp tại cùng đường dẫn `docs/metadata/`; cần giữ phiên bản kết quả khi thực hiện thí nghiệm mới. Verify so byte chuẩn bị/manifest/phân vùng, không fit. Timestamp/thời gian/binary mô hình có thể khác khi chạy lại; cùng input/config/script phải tạo được manifest giống nhau.

## 10. Kiểm tra thực tế

- **9/9 kiểm thử logic đạt:** tiền tố, cách ly trước loại trùng, giữ ID, chia nhóm/phân tầng xác định, chọn macro-F1/phá hòa, phát hiện giao nhau và launcher giữ module handle.
- Đối chiếu độc lập từ dự đoán lưu: accuracy, macro-F1, precision/recall/F1/support của hai mô hình khớp phép đếm TP/FP/FN; ma trận khớp support và accuracy.
- Kiểm 12 đặc trưng ký tự chọn xác định: IDF khớp công thức smooth IDF theo số tài liệu/DF **chỉ trên train**, không fit lại.
- Nhật ký có đúng 7 ứng viên fit hoàn tất, không cảnh báo; khóa lựa chọn trước đúng một lần mở test để chấm. Lỗi khởi động trước fit không tính là thử thêm C.
- Lệnh verify **đạt**: dựng lại quan hệ nhóm gốc và chuẩn bị, so từng byte manifest/quyết định/ba phân vùng, kiểm hash input/mô hình/lựa chọn/kết quả; không fit hoặc predict test thêm lần nào.
- Rà Git **đạt**: cả **32 tệp run cục bộ**, gồm 7 mô hình (tổng 18.264.006 byte), bị bỏ qua. Có 9 tệp mới có thể chia sẻ cho TASK 06B: cấu hình, ba script/kiểm thử, báo cáo và bốn metadata/phụ lục. Requirements, mã thư viện cài sẵn, `.gitignore`, tài liệu kiểm định cũ và website giữ nguyên; không commit/push trong task này.
- Giữ mô hình ký tự C=10 làm **ứng viên thí nghiệm**; không tích hợp website, không tự gán danh mục hoặc đặt ngưỡng từ điểm tổng hợp này.
