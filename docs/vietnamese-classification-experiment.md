# TASK 10B — Thí nghiệm phân loại tiếng Việt v1

Ngày thực hiện: **21/10/2026**. Run **`task10b-vi-v1`**. Chỉ dùng `vi-authored-v1`, không ghép dữ liệu tiếng Anh, không thay website/mô hình đang chạy.

**Kết quả:** TF-IDF ký tự `char_wb` (3,5) + LinearSVC **C=10** được chọn bằng macro-F1 validation **0,861125**. Test: **accuracy 0,727273**, **macro-F1 0,721186**, đúng **72/99**, sai **27/99**. Dummy đúng **6/99**, sai **93/99**. Không sửa cấu hình sau khi xem test.

**Đây là dữ liệu mô phỏng do dự án biên soạn với AI, không phải giao dịch thật hoặc tập kiểm thử độc lập đại diện người dùng Việt Nam.** Chưa có duyệt nhãn độc lập. Còn nguyên **24 cảnh báo gần giống mức yếu xuyên tập** của TASK 10A; không khẳng định tách hết merchant/mẫu câu/ngữ nghĩa.

## 1. Dữ liệu và bản chia được giữ nguyên

Đã đọc [báo cáo TASK 10A](vietnamese-classification-data.md), bộ nhãn và mã chuẩn hóa hiện có. Nguồn duy nhất là `data/vietnamese/classification/vi-authored-v1/`. Kiểm hash dataset, split, manifest, split-lock, toàn bộ nguồn/đầu ra đã khóa và mã chuẩn hóa/bộ nhãn được tham chiếu.

| Tập | Mẫu | Nhóm |
|---|---:|---:|
| Train | 464 | 406 |
| Validation | 99 | 87 |
| Test | 99 | 90 |
| Tổng | 662 | 583 |

Giữ nguyên nhãn, ID nhóm, quan hệ cha–con và membership từng mẫu so với split-manifest. Kiểm lại không giao nhau theo group_id, scenario_id, nguyên văn, chuẩn hóa, không dấu và khóa chẩn đoán; mọi cạnh gần trùng mạnh ở cùng tập. Đủ 17 nhãn trong cả ba tập. **48 câu mơ hồ/ngoài phạm vi** có `label=null`, `split=excluded`, không vào fit/validation/test. Không chia lại, tăng mẫu hoặc sửa nhãn.

Các khóa bỏ dấu/che số/mở rộng viết tắt chỉ được đọc trong kiểm tra toàn vẹn nhóm, **không dùng làm đặc trưng**. Các cấu trúc/test membership được kiểm trước fit để xác nhận bản chia, không tính dự đoán hoặc điểm test trong lựa chọn. Toàn bộ tập đã được tác giả đọc trong giai đoạn biên soạn 10A, nên không gọi đây là đánh giá mù hoàn toàn.

```text
dataset.jsonl SHA-256
6b7071f9ad2ae25baccb82920c6f7d7956cb29ac25b34b102f846d551156598a

split-manifest.json SHA-256
e8bad655404124cff2a801ec2fa4bc79fdceaf21ecfcc632da982579c4e0c04b

split-lock.json SHA-256
9ec1961b0e81109e1cb2e9fdafc87928adc12cba8ecc7d63c6ef3c4a7cb2083d
```

## 2. Đầu vào và cấu hình khóa trước fit

Chỉ lấy `description` làm X, `label` làm y. Không nối nhãn/tên nhãn, ID, nguồn gốc, scenario_id, group_id hay split vào X. Chuẩn hóa thuần không học bằng `normalize_description`: bỏ một tiền tố debit/credit ở đầu nếu có (dataset này không có), NFC, casefold, gộp khoảng trắng; **giữ dấu tiếng Việt**, không dịch hoặc mở rộng viết tắt trong X.

Cấu hình lưu ở `experiments/vietnamese-classification-v1.json`; script `scripts/run_vietnamese_classification_experiment.py`. Protocol lưu độc quyền trước fit ở thư mục run, gồm hash cấu hình/script/nguồn dữ liệu/adapter/chuẩn hóa, runtime và hash danh sách ID từng tập.

| Thành phần | Cấu hình cố định |
|---|---|
| Dummy | Pipeline chỉ có DummyClassifier(strategy=most_frequent); nhận X mô tả nhưng chỉ học tần suất y |
| Từ | Pipeline TfidfVectorizer(analyzer=word, ngram_range=(1,2)) + LogisticRegression(solver=lbfgs, max_iter=1000, tol=1e-4) |
| Ký tự | Pipeline TfidfVectorizer(analyzer=char_wb, ngram_range=(3,5)) + LinearSVC(dual=auto, max_iter=5000, tol=1e-4) |
| Hai TF-IDF | min_df=1, max_df=1.0, max_features=None, sublinear_tf=True, lowercase=False, strip_accents=None, norm=l2, use_idf=True, smooth_idf=True |
| Word tokenizer | Token pattern mặc định Unicode: từ có ít nhất hai ký tự; không cài bộ tách từ tiếng Việt riêng |
| C | Đúng {0.1, 1, 10} cho mỗi họ; class_weight=None |
| Seed | 20261021 |
| Lựa chọn | Macro-F1 validation trên đủ 17 nhãn, zero_division=0; dùng điểm chưa làm tròn |
| Hòa chính xác | C nhỏ hơn; tiếp theo word_logreg trước char_linearsvc. Dummy không là ứng viên chọn |
| Fit | Mỗi Pipeline chỉ fit 464 train; không fit vocab/IDF/classifier trên validation hoặc test |
| Cuối | Không refit train+validation; chỉ chấm Dummy và Pipeline được chọn trên test |

Có đúng **7 lần fit**: Dummy + 6 ứng viên. Không thêm cấu hình. Validation/test chỉ transform và predict từ Pipeline đã fit train; chuẩn hóa trước Pipeline là hàm thuần, không học dữ liệu.

Runtime: joblib 1.6.0, numpy 2.5.4, python 3.13.16, scikit-learn 1.9.1, scipy 1.18.1, threadpoolctl 3.7.0. Giới hạn một luồng. Dùng lại adapter Unicode Windows đã có của 06B, **chỉ trong tiến trình CLI ngoại tuyến**: giữ module handle để threadpoolctl phân giải đường dẫn Unicode đúng, không sửa package/DLL/mã adapter hoặc đưa vào web server. Receipt runtime được ghi trước fit đầu, mọi fit không có warning.

## 3. Validation và lựa chọn

| Ứng viên | Accuracy | Macro-F1 | Vector rỗng /99 | Thời gian fit (giây) |
|---|---:|---:|---:|---:|
| dummy | 0.060606 | 0.006723 | N/A | 0.084198 |
| word_logreg_C_0p1 | 0.646465 | 0.596825 | 0 | 0.115348 |
| word_logreg_C_1 | 0.848485 | 0.849480 | 0 | 0.275000 |
| word_logreg_C_10 | 0.828283 | 0.832278 | 0 | 0.533512 |
| char_linearsvc_C_0p1 | 0.828283 | 0.829867 | 0 | 0.107818 |
| char_linearsvc_C_1 | 0.858586 | 0.861107 | 0 | 0.127613 |
| char_linearsvc_C_10 | 0.858586 | 0.861125 | 0 | 0.162720 |

C=10 thắng theo điểm **0,8611248228895287**, so với C=1 ký tự **0,8611070878371917**. Hai ứng viên đều accuracy 85/99 nhưng macro-F1 không bằng nhau, nên không áp quy tắc hòa sau làm tròn. Chênh lệch rất nhỏ này không chứng minh ưu thế tổng quát của C=10 ngoài tập validation nhỏ.

Từ điển fit train có **3.285** đặc trưng từ/word-ngram và **4.917** đặc trưng ký tự. Tất cả sáu ứng viên có 0 vector rỗng validation. Dummy không có vectorizer nên số vector rỗng **không áp dụng**, không ghi giả là 0.

Lựa chọn, hash validation và hash mô hình đã được khóa **trước lần dự đoán test đầu tiên**. Thời gian `.fit` gồm học TF-IDF và classifier, không gồm khởi động Python, tải thư viện, ghi model hoặc chấm điểm; tổng 7 lần fit khoảng **1,406209 giây** trên máy hiện tại, không phải benchmark tốc độ giữa môi trường.

## 4. Test cuối — chỉ hai mô hình

| Mô hình | Accuracy | Macro-F1 | Đúng | Sai | Vector rỗng validation/test |
|---|---:|---:|---:|---:|---|
| dummy | 0.060606 | 0.006723 | 6/99 | 93/99 | N/A / N/A |
| char_linearsvc_C_10 | 0.727273 | 0.721186 | 72/99 | 27/99 | 0 / 0 |

Không chấm các ứng viên thua validation trên test. Không tính vector word trên test sau khi word không được chọn. Pipeline ký tự thắng có **0/99 vector toàn 0 ở test**; không có vector rỗng không đồng nghĩa dự đoán đúng. Dummy học lớp có tần suất train cao nhất; khi đồng tần suất, scikit-learn chọn Education theo thứ tự lớp.

### Precision/recall/F1 theo lớp

Mỗi bảng dùng thứ tự mã 01–17 bên dưới. P/R/F1 làm tròn 6 số lẻ; support là số mẫu test, không phải số nhóm độc lập.

**char_linearsvc_C_10**

| Mã | Nhãn | Precision | Recall | F1 | Support |
|---|---|---:|---:|---:|---:|
| 01 | Education | 0.666667 | 1.000000 | 0.800000 | 6 |
| 02 | Entertainment | 1.000000 | 0.666667 | 0.800000 | 6 |
| 03 | Fees | 1.000000 | 0.500000 | 0.666667 | 6 |
| 04 | Groceries | 0.625000 | 0.833333 | 0.714286 | 6 |
| 05 | Healthcare | 0.857143 | 1.000000 | 0.923077 | 6 |
| 06 | Income | 1.000000 | 0.666667 | 0.800000 | 6 |
| 07 | Insurance | 1.000000 | 0.285714 | 0.444444 | 7 |
| 08 | Mortgage | 1.000000 | 1.000000 | 1.000000 | 4 |
| 09 | Personal Care | 1.000000 | 0.500000 | 0.666667 | 6 |
| 10 | Rent | 0.666667 | 1.000000 | 0.800000 | 4 |
| 11 | Restaurants | 0.600000 | 1.000000 | 0.750000 | 6 |
| 12 | Shopping | 0.400000 | 0.333333 | 0.363636 | 6 |
| 13 | Subscription | 0.600000 | 1.000000 | 0.750000 | 6 |
| 14 | Transfer | 0.833333 | 0.833333 | 0.833333 | 6 |
| 15 | Transportation | 0.800000 | 0.666667 | 0.727273 | 6 |
| 16 | Travel | 0.750000 | 1.000000 | 0.857143 | 6 |
| 17 | Utilities | 0.400000 | 0.333333 | 0.363636 | 6 |

**dummy**

| Mã | Nhãn | Precision | Recall | F1 | Support |
|---|---|---:|---:|---:|---:|
| 01 | Education | 0.060606 | 1.000000 | 0.114286 | 6 |
| 02 | Entertainment | 0.000000 | 0.000000 | 0.000000 | 6 |
| 03 | Fees | 0.000000 | 0.000000 | 0.000000 | 6 |
| 04 | Groceries | 0.000000 | 0.000000 | 0.000000 | 6 |
| 05 | Healthcare | 0.000000 | 0.000000 | 0.000000 | 6 |
| 06 | Income | 0.000000 | 0.000000 | 0.000000 | 6 |
| 07 | Insurance | 0.000000 | 0.000000 | 0.000000 | 7 |
| 08 | Mortgage | 0.000000 | 0.000000 | 0.000000 | 4 |
| 09 | Personal Care | 0.000000 | 0.000000 | 0.000000 | 6 |
| 10 | Rent | 0.000000 | 0.000000 | 0.000000 | 4 |
| 11 | Restaurants | 0.000000 | 0.000000 | 0.000000 | 6 |
| 12 | Shopping | 0.000000 | 0.000000 | 0.000000 | 6 |
| 13 | Subscription | 0.000000 | 0.000000 | 0.000000 | 6 |
| 14 | Transfer | 0.000000 | 0.000000 | 0.000000 | 6 |
| 15 | Transportation | 0.000000 | 0.000000 | 0.000000 | 6 |
| 16 | Travel | 0.000000 | 0.000000 | 0.000000 | 6 |
| 17 | Utilities | 0.000000 | 0.000000 | 0.000000 | 6 |

### Ma trận nhầm lẫn

Hàng = nhãn thật, cột = nhãn dự đoán, mã 01–17 theo bảng lớp. Mỗi ma trận có tổng 99; đường chéo lần lượt 72 và 6. Đây là số đếm, không phải xác suất.

**char_linearsvc_C_10**

```text
     01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17
01 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
02 |  0  4  0  0  0  0  0  0  0  0  0  1  1  0  0  0  0
03 |  1  0  3  0  0  0  0  0  0  0  1  0  0  0  0  0  1
04 |  0  0  0  5  0  0  0  0  0  0  1  0  0  0  0  0  0
05 |  0  0  0  0  6  0  0  0  0  0  0  0  0  0  0  0  0
06 |  0  0  0  0  1  4  0  0  0  1  0  0  0  0  0  0  0
07 |  1  0  0  0  0  0  2  0  0  0  0  0  2  0  0  2  0
08 |  0  0  0  0  0  0  0  4  0  0  0  0  0  0  0  0  0
09 |  0  0  0  1  0  0  0  0  3  0  0  1  0  1  0  0  0
10 |  0  0  0  0  0  0  0  0  0  4  0  0  0  0  0  0  0
11 |  0  0  0  0  0  0  0  0  0  0  6  0  0  0  0  0  0
12 |  0  0  0  1  0  0  0  0  0  0  1  2  0  0  1  0  1
13 |  0  0  0  0  0  0  0  0  0  0  0  0  6  0  0  0  0
14 |  0  0  0  0  0  0  0  0  0  0  0  0  0  5  0  0  1
15 |  1  0  0  0  0  0  0  0  0  0  1  0  0  0  4  0  0
16 |  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  6  0
17 |  0  0  0  1  0  0  0  0  0  1  0  1  1  0  0  0  2
```

**dummy**

```text
     01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17
01 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
02 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
03 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
04 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
05 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
06 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
07 |  7  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
08 |  4  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
09 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
10 |  4  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
11 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
12 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
13 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
14 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
15 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
16 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
17 |  6  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
```

## 5. Phân tích 27 lỗi — không sửa test

- **Ưu tiên mục đích dễ nhầm:** Insurance→Travel 2 mẫu về bảo hiểm chuyến đi; Transportation→Education 1 mẫu về vé đi học; Shopping→Transportation 1 mẫu về vật dụng mang đi làm. Mô hình chưa giữ chắc ranh giới mục đích gán nhãn trong các ngữ cảnh này.
- **Chăm sóc cá nhân và hàng hóa:** Personal Care→Shopping/Groceries/Transfer mỗi loại 1. Sản phẩm chăm sóc cơ thể và dụng cụ chuyên dụng còn bị nhầm với hàng thường hoặc điều chuyển. Đây là lỗi, không đổi nhãn theo dự đoán.
- **Nguyên liệu và phủ định:** Groceries→Restaurants 1 mẫu có ý nguyên liệu chưa chế biến; Transfer→Utilities 1 mẫu không dấu nói nạp ví chưa trả hàng hóa. Nhận diện được n-gram không chứng minh hiểu được phủ định hoặc bản chất luồng tiền.
- **Kiểu ghi ngắn/không dấu:** có 23 lỗi ở câu gốc, 2 ở biến thể nhận diện khi biên tập, 1 ở bản bỏ dấu tự động và 1 ở viết lại thủ công. Insurance→Education/Subscription có các cách viết BHYT hoặc bỏ dấu. Không suy mọi lỗi đều do dấu: đa số vẫn là câu gốc.
- **Lớp yếu trong mẫu này:** Insurance recall 2/7; Shopping 2/6; Utilities 2/6. Mortgage đúng 4/4 nhưng support quá nhỏ để kết luận nhận diện tốt trên người dùng thật.

Các nhận định trên là đọc lỗi theo quy tắc nhãn, **không phải phân tích nhân quả hệ số/attribution** của mô hình. Lưu đủ 27 lỗi và dự đoán từng dòng test trong run ngoài Git. Không chép toàn bộ mô tả vào báo cáo/metadata chia sẻ, không sửa test, bổ sung câu, thay nhóm hoặc chạy thêm tham số.

Đánh giá vẫn tính theo mẫu, gồm biến thể cùng nhóm trong test; 99 mẫu thuộc 90 nhóm, không phải 99 quan sát người dùng độc lập. 24 cảnh báo gần giống chưa duyệt độc lập vẫn còn. Không suy từ chênh lệch điểm so với bộ tổng hợp tiếng Anh rằng một mô hình/ngôn ngữ tốt hơn: nguồn, kích thước, phân bố và bản chia khác nhau.

## 6. Hành vi trên 48 câu mơ hồ/ngoài phạm vi

Chỉ chạy sau khi khóa lựa chọn và hoàn tất chấm test. Không dùng các possible_labels làm nhãn thật, không tính accuracy, precision/recall/F1 hoặc chọn ngưỡng từ chối trên nhóm này. Cả 48 câu có vector không rỗng; Pipeline phân loại đóng vẫn đưa ra một trong 17 nhãn. Không xuất hoặc diễn giải decision_function thành xác suất/% chắc chắn.

| Nhãn đầu ra | Số câu |
|---|---:|
| Education | 0 |
| Entertainment | 3 |
| Fees | 4 |
| Groceries | 0 |
| Healthcare | 2 |
| Income | 6 |
| Insurance | 1 |
| Mortgage | 2 |
| Personal Care | 2 |
| Rent | 7 |
| Restaurants | 3 |
| Shopping | 6 |
| Subscription | 2 |
| Transfer | 5 |
| Transportation | 2 |
| Travel | 1 |
| Utilities | 2 |

Ví dụ hành vi (không chấm đúng/sai theo nhãn chuẩn đơn): câu chỉ nói chuyển khoản được Transfer, câu chỉ nói thanh toán được Utilities, câu mua đồ chung chung được Shopping; nhận hoàn ứng hoặc nộp thuế thu nhập lại bị gán Income. Các đầu ra cho hoàn cọc/đặt cọc, quyết toán thẻ, quà/từ thiện hoặc đầu tư cũng chỉ là lựa chọn bắt buộc của bộ nhãn đóng, không đủ căn cứ xác nhận bản chất tài chính.

Kết quả này cho thấy nhu cầu xem lại khi đầu vào thiếu ngữ cảnh/ngoài phạm vi; **không tạo ngưỡng từ chối hay tính năng mới trong task**. Toàn bộ 48 đầu ra có ID, mô tả, nhãn dự đoán và trạng thái vector trong `ambiguous-predictions.json` cục bộ; gold_label luôn null.

## 7. Artifact, hash và chạy lại

Run: `data/experiments/classification-vietnamese/task10b-vi-v1/` (ngoài Git).

- `config.json`, `protocol.json`/`.sha256`: thiết kế và bằng chứng khóa trước fit đầu.
- `runtime-before-first-fit.json`, `events.jsonl`: adapter/giới hạn luồng và thứ tự các pha.
- `validation.json`, `selection.json`/`.sha256`: sáu ứng viên và Dummy, lựa chọn trước test.
- `models/*.joblib`: bảy Pipeline fit train; không refit, không thay model website.
- `test-start.json`, `results.json`/`.sha256`: dấu bắt đầu test đúng hai mô hình và điểm cuối.
- `test-predictions.json`, `test-errors.json`, `ambiguous-predictions.json`: bản ghi từng mẫu chỉ ở cục bộ.
- `error-analysis.json`, `artifact-manifest.json`: phân tích và hash artifact cục bộ.

Kết quả tổng hợp không chứa mô tả/bản ghi cá nhân hoặc từng dòng dữ liệu được lưu riêng ở [metadata kết quả](metadata/vietnamese-classification-experiment-results.json).

```text
protocol.json SHA-256
63a08133a4c2cc11d813321185b2956a2177ecfa3df5a8992e736a7ee6db27b7

selection.json SHA-256
dfe6ce0cc0d33b5cb01fbc7b25b975b423f1222d4814d7b46c14643aef283f30

Mô hình tiếng Việt được chọn SHA-256
19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55

results.json SHA-256
8b628b26e1c95720a63943f5378a2c8a9777df228566cdd6d41ae4155767b139
```

Các lệnh trong PowerShell từ thư mục dự án:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 scripts/run_vietnamese_classification_experiment.py prepare
& '.\.venv\Scripts\python.exe' -X utf8 scripts/run_vietnamese_classification_experiment.py train
& '.\.venv\Scripts\python.exe' -X utf8 scripts/run_vietnamese_classification_experiment.py evaluate
& '.\.venv\Scripts\python.exe' -X utf8 scripts/run_vietnamese_classification_experiment.py verify
```

Ba pha đầu đã chạy cho run này; **không chạy lại trên run đã hoàn tất**. prepare từ chối thư mục đã tồn tại, train từ chối khi đã có model/selection, evaluate từ chối nếu đã bắt đầu test. verify chỉ kiểm hash/quan hệ/thứ tự sự kiện, không fit/predict hoặc chấm lại. Nếu cần tái lập thực sự, dùng `--run-dir data/experiments/classification-vietnamese/<ten-run-moi>` cho cả bốn pha với cùng script/cấu hình/nguồn đã khóa, không thử seed hoặc cấu hình để nâng điểm test.

Kiểm thử protocol không fit mô hình:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -m unittest scripts.test_vietnamese_classification_experiment --verbose
```

**6/6 kiểm thử protocol đạt**: giữ dấu/NFC, ưu tiên hòa chính xác, không tạo hòa do làm tròn, tham số TF-IDF/Pipeline, số mẫu/nhóm/loại câu mơ hồ, và chặn huấn luyện lại/chấm test lần hai trên run hoàn tất. verify xác nhận đúng **7 fit**, hai mô hình được chấm test, không refit và tập test không đổi. Không chạy hồi quy website vì không sửa mã website.

Xác minh cuối: **254 tệp đã có trước task giữ nguyên SHA-256**, gồm dataset/split tiếng Việt v1, artifact/thí nghiệm tiếng Anh, mã website, SQLite thật, requirements, `.gitignore` và nguồn threadpoolctl đã cài. Đối chiếu **23 artifact run** bằng `artifact-manifest.json` thành công; số đếm ma trận/accuracy/lỗi/support khớp. Nhật ký ghi 7 fit, mỗi fit chỉ 464 train, một lượt predict test/mô hình và chỉ đúng hai mô hình. Receipt ở `verification.json` cục bộ.

Website vẫn dùng artifact tiếng Anh trước đó; model tiếng Việt mới không được đưa vào settings hoặc metadata tích hợp hiện có. Các thay đổi tài liệu từ 09C/10A được giữ nguyên. Chưa deploy, ghép tập tiếng Anh, chọn ngưỡng, tích hợp model tiếng Việt hoặc commit/push.
