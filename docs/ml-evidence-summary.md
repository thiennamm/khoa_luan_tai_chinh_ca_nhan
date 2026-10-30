# Tổng hợp bằng chứng học máy

TASK 21B, **30/10/2026**, mã đối chiếu **`c628a642077ccc26db4c6e1ddc1349b67f4c57e9`**. Chỉ đọc báo cáo, cấu hình, JSON kết quả/manifest và hash các tệp ở đường dẫn được hồ sơ dẫn ra. Không quét ổ đĩa, đọc credential/.env, mở database, deserialize model, predict, fit, sửa split hoặc chọn lại tham số.

Phân biệt: **hồ sơ** = kết quả đã lưu của thí nghiệm cũ; **đối chiếu TASK 21B** = JSON/hash/số đếm manifest khớp, không tái thực thi mô hình; **chưa xác minh** = chưa có bằng chứng độc lập hoặc chưa kiểm môi trường hiện tại. Không coi hash đúng là kiểm định nhãn đúng, nguồn thật hay khả năng tổng quát hóa.

## 1. Nguồn bằng chứng và cách tra cứu

Các vị trí dạng `/models/...` dưới đây là **JSON Pointer**, chỉ đúng khóa trong tệp được liên kết; không phải URL endpoint. Chỉ đưa số liệu tổng hợp vào tài liệu, không sao chép bản ghi mô tả/giao dịch.

| Mã nguồn | Tệp | Vị trí chính |
|---|---|---|
| E0 | [classification-source.json](metadata/classification-source.json) | `/revision`, `/files/transactions-synthetic.csv`, `/license` |
| E1 | [classification-experiment-data.json](metadata/classification-experiment-data.json) | `/filtering`, `/split`, `/split_seed`, `/leakage_checks` |
| E2 | [classification-experiment-results.json](metadata/classification-experiment-results.json) | `/selection/candidates`, `/models`, `/test_support`, `/selected_candidate_id` |
| V0 | [vietnamese-classification-v1.json](../experiments/vietnamese-classification-v1.json) | `/samples`, `/groups`, `/seed`, `/dataset_sha256`, `/split_sha256` |
| V1 | [vietnamese-classification-experiment-results.json](metadata/vietnamese-classification-experiment-results.json) | `/validation/candidates`, `/models`, `/ambiguous`, `/known_weak_warnings` |
| F0 | [forecast-source.json](metadata/forecast-source.json) và [kiểm định](forecast-data-audit.md#L45) | metadata version/license/hash; báo cáo mục 3 định danh, ngày/tiền tệ |
| F1 | [forecast-experiment-protocol.json](metadata/forecast-experiment-protocol.json) | `/summary`, `/input_hashes`, `/local_hashes`, các cờ currency/coverage/date hypothesis |
| F2 | [forecast-experiment-results.json](metadata/forecast-experiment-results.json) | `/selected_alpha`, `/validation`, `/test`, `/currency`, `/not_fully_blind_evaluation` |

Báo cáo đầy đủ: [phân loại EN](classification-experiment.md), [phân loại VI](vietnamese-classification-experiment.md), [MoneyData](forecast-experiment.md). Cấu hình trước fit: [EN](../experiments/classification-v1.json), [VI](../experiments/vietnamese-classification-v1.json), [MoneyData](../experiments/forecast-v1.json). Những nguồn công khai được dẫn lại theo hồ sơ tải trước đó; **TASK 21B không truy cập lại nguồn online** hoặc kiểm pháp lý độc lập giấy phép.

## 2. Phân loại tiếng Anh — TASK 06B

| Nội dung | Bằng chứng được tổng hợp | Vị trí tra cứu |
|---|---|---|
| Nguồn | DoDataThings/us-bank-transaction-categories-v2; revision **`3e8d052cb7b362fb1a04b6064d2331982553ea56`**, CSV `transactions-synthetic.csv` | E0 `/dataset`, `/revision`, `/files`; [báo cáo mục 1–2](classification-experiment.md#L7) |
| Tính chất/phạm vi | Tổng hợp tiếng Anh theo mô tả nguồn; CSV chỉ description/category, không user, ngày, tiền. Không dùng làm lịch sử dự báo. Card khai báo MIT; không có LICENSE riêng trong cây tệp, quyền chưa được kiểm độc lập | E0 `/license`; [kiểm định mục 2](classification-data-audit.md#L39) |
| Kích thước gốc/lọc | **68.000 dòng**, 17 nhãn; 40.512 thân chuẩn hóa. Cách ly toàn bộ **6 thân/38 dòng** mâu thuẫn; loại thêm **27.456** bản lặp, giữ **40.506** mẫu | E1 `/filtering/totals`, `/filtering/conflicting_body_groups` |
| Chia tập | Train **28.356 / 11.261 nhóm**, validation **6.075 / 5.506**, test **6.075 / 5.472**. Seed **20261020**, mục tiêu 70/15/15 theo nguyên nhóm từ 06A | E1 `/split`, `/split_seed`; [thuật toán chia](classification-experiment.md#L51) |
| Chống rò rỉ đã kiểm | Không giao group/body/exact/normalized/template theo heuristic; **832 cạnh gần giống đã biết**, 0 cạnh xuyên tập. **Không phải merchant holdout** | E1 `/leakage_checks`, `/merchant_holdout`; không có merchant ID xác minh |
| Đầu vào | Chỉ mô tả; bỏ đúng một tiền tố đầu debit/credit, NFC → casefold → gộp khoảng trắng, giữ dấu câu. Không dùng nhãn/ID/group/khóa chẩn đoán làm đặc trưng | [cấu hình EN](../experiments/classification-v1.json) `/input`; [chuẩn hóa website](../finance/classification.py#L32) |
| Ứng viên | Dummy most_frequent; TF-IDF word(1,2)+LogisticRegression; TF-IDF char_wb(3,5)+LinearSVC. C={0.1,1,10}, min_df=2; max_features từ/ký tự 60.000/80.000 | Cấu hình EN; E2 `/selection/candidates` |
| Chọn trước test | Macro-F1 validation lớn nhất, hòa chính xác ưu tiên C nhỏ rồi word_logreg. Chọn **char_linearsvc_C_10p0**; **không refit train+validation**, chỉ chấm Dummy và bản đã chọn trên test | E2 `/selection/rule`, `/selection/refit_train_validation`, `/selection/test_records_read_for_selection` |

### Chỉ số kết quả

Tất cả tỷ lệ dưới đây là trên **tập thí nghiệm**, không phải phần trăm chắc chắn của giao dịch đang nhập.

| Cấu hình | Accuracy validation | Macro-F1 validation | Accuracy test | Macro-F1 test | Lỗi test | Fit Pipeline (giây) | Nguồn |
|---|---:|---:|---:|---:|---:|---:|---|
| Dummy most_frequent | 0,097119 | 0,010414 | 0,097119 | 0,010414 | 5.485/6.075 | 0,126316 | E2 `/selection/candidates/0`, `/models/dummy` |
| **TF-IDF ký tự + LinearSVC C=10** | **0,986996** | **0,987756** | **0,993086** | **0,993832** | **42/6.075** | **9,634755** | E2 `/selection/candidates/6`, `/models/char_linearsvc_C_10p0` |

Ứng viên từ tốt nhất ở validation là word_logreg C=10, macro-F1 **0,954734**; **chưa có điểm test cho cấu hình này** (E2 `/selection/candidates/3`, `/selection/best_per_family`). Không suy test của mô hình thua từ tên artifact. Fit gồm TF-IDF và classifier trên train, không gồm import/tải/ghi model; không dùng làm benchmark production.

Precision/recall/F1/support từng lớp và ma trận 17×17: E2 `/models/{candidate}/classification_report`, `/confusion_matrix`; [bảng mục 6.1–6.3](classification-experiment.md#L160). Số mẫu đúng bản chọn **6.033/6.075** = support − errors. Accuracy là tỷ lệ đúng; macro-F1 là trung bình F1 ngang trọng số giữa 17 nhãn, không phải điểm quyết định của LinearSVC.

Giới hạn: nguồn tổng hợp, mẫu/merchant chưa phát hiện vẫn có thể rò rỉ; nhãn nguồn chưa đối soát bởi chủ giao dịch; mẫu sau loại trùng không còn phản ánh tần suất thực. Một seed/split, không có tập thật độc lập, chưa đánh giá tiếng Việt ở thí nghiệm này. Điểm cao không chứng minh hiệu quả thật hoặc mô hình/ngôn ngữ tốt hơn thí nghiệm VI khác nguồn.

## 3. Phân loại tiếng Việt — TASK 10B

| Nội dung | Bằng chứng được tổng hợp | Vị trí tra cứu |
|---|---|---|
| Nguồn | **vi-authored-v1**, do dự án biên soạn với AI, không dịch nguyên bộ EN, không lấy dữ liệu tài khoản. Chưa có duyệt nhãn độc lập, chưa chỉ định giấy phép phân phối riêng; không kế thừa MIT của EN | [vietnamese-classification-data.md#L9](vietnamese-classification-data.md#L9), V1 `/independent_human_review` |
| Kích thước | **662 mô tả có nhãn / 583 nhóm**, 17 mã; thêm **48 câu mơ hồ/ngoài phạm vi** tách ngoài ba tập | V0 `/samples`, `/groups`, `/ambiguous_excluded`; [báo cáo mục 1](vietnamese-classification-experiment.md#L9) |
| Chia tập | Train **464 / 406 nhóm**, validation **99 / 87**, test **99 / 90**; seed **20261021**; không đổi membership | V0 `/samples`, `/groups`, `/seed`; [quy tắc chia](vietnamese-classification-data.md#L115) |
| Rò rỉ/độc lập | Gộp biến thể cùng kịch bản; không giao các khóa mạnh đã định nghĩa. **24 cảnh báo gần giống mức yếu xuyên tập còn chưa duyệt độc lập**. Toàn tập từng được xem khi biên soạn, không đánh giá mù hoàn toàn | V1 `/known_weak_warnings`, `/independent_human_review`; báo cáo mục 1/5 |
| Đầu vào | Chỉ description; chuẩn hóa như EN, **giữ dấu tiếng Việt**. Khóa bỏ dấu/che số chỉ chẩn đoán, không là feature. Không ghép EN | V0 `/input_fields`, `/normalization` |
| Ứng viên | Dummy; word(1,2)+LogisticRegression; char_wb(3,5)+LinearSVC; min_df=1, C={0.1,1,10}. Đúng 7 fit; chỉ train 464; không refit | V0; V1 `/validation/candidates`, `/refit_train_validation` |
| Chọn trước test | Macro-F1 validation; hòa C nhỏ rồi word_logreg. Chọn **char_linearsvc_C_10**, macro-F1 chính xác **0,8611248228895287** | V1 `/selected_id`, `/validation/candidates/6`; [mục 3](vietnamese-classification-experiment.md#L61) |

### Chỉ số kết quả

| Cấu hình | Accuracy validation | Macro-F1 validation | Accuracy test | Macro-F1 test | Đúng/sai test | Fit Pipeline (giây) | Nguồn |
|---|---:|---:|---:|---:|---|---:|---|
| Dummy most_frequent | 0,060606 | 0,006723 | 0,060606 | 0,006723 | 6 đúng / 93 sai | 0,084198 | V1 `/validation/candidates/0`, `/models/dummy` |
| **TF-IDF ký tự + LinearSVC C=10** | **0,858586** | **0,861125** | **0,727273** | **0,721186** | **72 đúng / 27 sai** | **0,162720** | V1 `/validation/candidates/6`, `/models/char_linearsvc_C_10` |

C=1 ký tự có macro-F1 validation **0,8611070878371917** (V1 `/validation/candidates/5`), rất gần C=10 nhưng không hòa khi dùng điểm chưa làm tròn. Đây là lý do chọn đã khóa, không phải bằng chứng C=10 luôn tốt hơn. Không thử thêm sau xem test. Test 99 mẫu chỉ thuộc 90 nhóm, không phải 99 người dùng độc lập.

Vector rỗng của model chọn: validation **0/99**, test **0/99** (V1 `/models/char_linearsvc_C_10/validation_zero_vectors`, `/test_zero_vectors`). Dummy không có vectorizer, giá trị này không áp dụng. Trên 48 câu mơ hồ, vẫn có 0 vector rỗng và mô hình đóng trả nhãn, nhưng **không tính accuracy/F1**, không chọn ngưỡng từ chối (V1 `/ambiguous`). Có đặc trưng không đồng nghĩa câu có đủ nghĩa để gán nhãn.

Từng lớp/ma trận: V1 `/models/{candidate}/classification_report`, `/confusion_matrix`; [báo cáo mục 4](vietnamese-classification-experiment.md#L83). Nhận xét lỗi trong mục 5 là phân tích theo quy tắc nhãn, không phải nghiên cứu nhân quả. Dữ liệu nhỏ, tự biên soạn với AI, chưa có đánh giá độc lập đại diện người Việt. Không so 72,73% với 99,31% EN để kết luận ngôn ngữ hoặc mô hình nào tốt hơn.

## 4. Dự báo MoneyData — TASK 07B, khác dự báo website

| Nội dung | Bằng chứng được tổng hợp | Vị trí tra cứu |
|---|---|---|
| Nguồn/giấy phép | Robert Laramee, “Bank Transactions Dataset”, Mendeley Data V1, DOI **10.17632/dnxtg6n4rv.1**, CC BY 4.0 theo hồ sơ nguồn | F0 `/contributor`, `/version`, `/doi`, `/license` |
| Thật hay tổng hợp | Nhóm công bố mô tả ngân hàng thật đã ẩn danh, một khách hàng. **Chưa đối soát độc lập nguồn thật/số người/số tài khoản**; workbook không có user_id/account_id ổn định | [kiểm định mục 2–3](forecast-data-audit.md#L41); không dùng Transaction Number như mã người |
| Mục tiêu/đơn vị | Tổng Debit Amount **quan sát trong workbook** theo tháng hạch toán giả định. **Đơn vị gốc chưa xác minh**; không gán GBP/VND, không đổi tiền | F2 `/target`, `/currency`; [báo cáo mục 1](forecast-experiment.md#L7) |
| Ngày/độ phủ | Nhánh **swap_numeric_month_day_hypothesis**, có bằng chứng nội tại nhưng **chưa được tác giả xác nhận**. Độ phủ chưa được xác nhận đầy đủ; không phân biệt chắc chắn ngày không giao dịch và ngày thiếu ghi nhận | F1/F2 các cờ date_hypothesis_author_confirmed, coverage_fully_confirmed |
| Kích thước | Workbook **6.567 dòng**, 6.122 debit/445 credit, nhánh giả thuyết 85 tháng. Bỏ biên 07/2015 và 07/2022: **83 tháng**, 6.472 giao dịch mọi chiều, **6.037 debit**, tổng **506.040,15 đơn vị gốc** | F1 `/summary`; [mục 2](forecast-experiment.md#L19) |
| Giữ dữ liệu | Giữ mọi debit trong đoạn dùng, cả khoản lớn/ứng viên trùng; không trừ credit. Có thể lẫn chuyển tiền/rút tiền/thanh toán thẻ; không đủ cờ nghiệp vụ để tách chắc chắn các loại này hoặc hoàn tiền, không gọi tất cả là tiêu dùng | [cấu hình](../experiments/forecast-v1.json) `/keep_all_debits`, `/remove_large_amounts`; F1 `/summary`; [giới hạn nhận diện, mục 6](forecast-data-audit.md#L172) |
| Lịch đánh giá | Ban đầu **08/2015–06/2020: 59 tháng**; validation **07/2020–06/2021: 12 mốc**; test **07/2021–06/2022: 12 mốc**. Mở rộng lịch sử, dự báo **một tháng** tại mỗi mốc | Cấu hình `/initial_history`, `/validation`, `/test`; [mục 3–4](forecast-experiment.md#L51) |
| Baseline / model | Tháng trước, TB 3 tháng, cùng tháng năm trước; StandardScaler+Ridge alpha={0.1,1,10}, solver cholesky, seed **20261020**; features lag1/2/3/12 và mean3 | Cấu hình `/baselines`, `/features`, `/alpha_values`, `/seed` |
| Chọn và chống rò rỉ | Chỉ fit quá khứ; clip âm về 0 trước MAE. Chọn **alpha 0.1** theo MAE validation, khóa trước test. 36 fit validation và 12 fit test cho alpha chọn; không đổi theo test | F2 `/validation/candidates`, `/selected_alpha`, `/test/ridge/fits`; báo cáo mục 4–6 |
| Tính độc lập | Toàn chuỗi đã xem trong kiểm định. **Holdout theo thời gian cho thí nghiệm thăm dò**, không mù hoàn toàn. Không tự điền tháng thiếu 0 | F1 `/full_series_previously_seen_in_audit`, `/not_fully_blind_evaluation`, `/summary/missing_months` |

Số fit không phải kích thước dữ liệu hay số người. Đây là 24 dự báo một bước có cập nhật bằng thực tế đã quan sát sau mỗi tháng, không phải một dự báo dài 12 tháng từ đầu test. Số tháng có bản ghi không tự chứng minh coverage đầy đủ.

### Chỉ số — đơn vị gốc chưa xác minh

| Phương pháp | MAE validation | MAE test | Median absolute error test | Bias test = trung bình dự báo − thực tế | Nguồn |
|---|---:|---:|---:|---:|---|
| Tháng trước | 2.758,6633 | 467,5183 | **356,0850** | +209,2617 | F2 `/validation/baselines/previous_month`, `/test/previous_month/scores` |
| **TB 3 tháng** | 2.153,7175 | **383,9950** | 362,8933 | +257,9433 | F2 `/validation/baselines/mean_previous_3`, `/test/mean_previous_3/scores` |
| Cùng tháng năm trước | 11.234,0867 | 1.994,1250 | 1.728,3700 | +1.279,3650 | F2 `/validation/baselines/same_month_previous_year`, `/test/same_month_previous_year/scores` |
| **Ridge alpha=0.1** | **1.916,3584** | **1.320,6704** | **1.080,2928** | **+1.320,6704** | F2 `/validation/candidates/0/scores`, `/test/ridge/scores` |

Mỗi cột validation/test có **12 mốc**; bảng làm tròn 4 chữ số, chọn cấu hình dùng điểm chưa làm tròn. Alpha 1 và 10 có MAE validation 1.919,2695 / 1.930,3268; **không có điểm test cho hai alpha này** (F2 `/validation/candidates/1`, `/2`). Chi tiết actual/prediction từng tháng và dấu vết fit ở F2 `/test/{method}/predictions`, `/fits`; [bảng tháng](forecast-experiment.md#L144).

Ridge thắng validation nhưng **thua TB 3 tháng trên MAE test**, khoảng 3,44 lần; baseline tháng trước tốt hơn về median. Không thay mục tiêu, xóa đỉnh hoặc chỉnh tham số để nâng điểm. Không suy ML luôn thua/thắng, không tuyên bố dùng được cho người khác, toàn bộ tiêu dùng, người Việt hoặc VND. Thí nghiệm đã công bố giả thuyết không biến kết luận “0 mốc đã xác nhận đủ dữ liệu” ở kiểm định 07A thành “24 mốc dữ liệu thật đã xác minh đầy đủ”. Hai phát biểu nói về mức bằng chứng khác nhau, không tự lấp chỗ thiếu bằng số 0.

## 5. Model nào thực sự được tích hợp?

| Thành phần | Mã website đối chiếu | Kết luận có căn cứ |
|---|---|---|
| EN char_linearsvc_C_10p0 | [classification.py#L24](../finance/classification.py#L24), config.local/render và metadata E2 | **Có luồng tích hợp**; constant candidate/hash, kiểm artifact trước deserialize, chỉ predict |
| VI char_linearsvc_C_10 | [classification_modes.py#L18](../finance/classification_modes.py#L18), metadata V1 + artifact-manifest | **Có luồng tích hợp**; chọn mode tường minh, normalization giữ dấu, không fallback EN |
| Dummy / LogisticRegression / C không chọn | Chỉ cấu hình/script thí nghiệm; không phải nhánh inference ở hai loader trên | **Chỉ nghiên cứu/đối chứng**, không coi được triển khai vì file model có tồn tại |
| Các Ridge MoneyData đã lưu theo mốc | [forecasting.py](../finance/forecasting.py), [forecast_math.py](../finance/forecast_math.py) không tải artifact MoneyData | **Không tích hợp các model MoneyData**; đơn vị/mục tiêu thí nghiệm không chuyển sang website |
| Dự báo cá nhân | [forecast_config.py](../finance/forecast_config.py), `calculate`, `snapshot`, `compute_and_store` | Tính riêng từ expense VND của user và coverage. 3–35 tháng dùng mean3; ≥36 so sánh cả 3 baseline + 3 alpha Ridge trên 6 tháng validation; model ở RAM, không tái dùng trọng số MoneyData |
| Demo dự báo | [forecast_demo.py](../finance/forecast_demo.py) | Chuỗi mô phỏng 48 tháng, seed 9048, đích cố định 01/2026; dùng chung thuật toán website, không ghi lịch sử cá nhân |

“Có luồng tích hợp” là kết luận từ code/settings/hash và bằng chứng QA trước đó, **không phải xác nhận model đang tải được trên server online hôm nay**. Điểm `decision_function` của LinearSVC chưa hiệu chỉnh xác suất; website không dùng điểm đó làm phần trăm chắc chắn hoặc ngưỡng tự gán. Xác nhận Apply/Lưu vẫn thuộc người dùng.

### Định danh hai model đã chọn

Các đường dẫn artifact `data/...` dưới đây là **tài liệu tham chiếu local**, tính từ thư mục dự án trên máy đã kiểm. Artifact không được Git theo dõi; đường dẫn ổ `D:\...` tới bằng chứng kiểm tra cũng chỉ có trên máy local. Chúng không phải liên kết tải hoặc nội dung mà người đọc GitHub có thể truy cập. Để tra cứu công khai trong repository, dùng các liên kết báo cáo/metadata ở mục 1; hash định danh phiên bản đã đối chiếu, không thay thế việc cung cấp artifact.

| Mode | Artifact được tài liệu chỉ ra | SHA-256 đối chiếu ngày 30/10/2026 |
|---|---|---|
| EN | `data/experiments/classification/task06b-v1-final/models/char_linearsvc_C_10p0.joblib` | `362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345` |
| VI | `data/experiments/classification-vietnamese/task10b-vi-v1/models/char_linearsvc_C_10.joblib` | `19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55` |

Không copy model vào Git. Gói suy luận chỉ chứa hai artifact và metadata/manifest/requirements, tách dữ liệu nghiên cứu. Cấu hình Render đọc gói build; quyền Release và trạng thái online không được truy cập ở task này.

## 6. Đối chiếu thực sự đã làm và điều còn thiếu

Đã kiểm SHA-256 **16 tệp được dẫn rõ trong hồ sơ**, không duyệt toàn ổ hoặc đọc dữ liệu tài khoản:

- EN: CSV revision, manifest, split-lock, model chọn, test-results. Đếm lại manifest: 28.356/6.075/6.075 mẫu và 11.261/5.506/5.472 nhóm khớp E1; JSON test-results khớp toàn bộ E2.
- VI: dataset.jsonl, split-manifest, split-lock, model chọn, protocol, results; mục model chọn trong artifact-manifest khớp hash/kích thước và models trong V1 khớp results cục bộ. **Không đọc lại từng câu để duyệt nhãn hoặc tính lại độ gần giống.**
- MoneyData: hash workbook gốc, monthly-v1, schedule, protocol-lock và results; JSON results cục bộ khớp F2. **Không mở sheet/mô tả để kiểm lại ngày, tiền tệ hoặc số chủ tài khoản.**

Kết quả: không gặp file thiếu hoặc mâu thuẫn trong tập đối chiếu này. Bằng chứng ngoài Git: `D:\POSTGRESQL QA\task21b-docs-20261030\artifact-evidence-check.json`. Hash results cục bộ để tra đúng phiên bản: EN **`2c785469f424dea9346f7dd2741941f6cc872929c1ff0212f631f41fe2ceb96a`**; VI **`8b628b26e1c95720a63943f5378a2c8a9777df228566cdd6d41ae4155767b139`**; MoneyData **`7fcaa287c5febfe1e27e4b01e5fb72e1aff471a1b8f38311718484b9605bf1b7`**. Đây là kiểm artifact đã lưu, không phải lượt tái lập fit/predict mới.

| Điểm còn thiếu | Trạng thái và cách diễn đạt |
|---|---|
| Giao dịch thật độc lập/nhãn người dùng được kiểm định | **Chưa xác minh** hiệu quả thực tế; feedback chỉ là lựa chọn, không tự dùng làm test/train |
| Nhãn VI được duyệt độc lập và 24 cảnh báo | **Chưa xác minh**; giữ cảnh báo, không gọi test đại diện người Việt hoặc loại cảnh báo sau xem điểm |
| Merchant/ngữ nghĩa ngoài heuristic EN/VI | **Chưa xác minh** tách hoàn toàn; không gọi merchant holdout |
| MoneyData: giả thuyết ngày, currency, độ phủ, số tài khoản | **Chưa xác minh**; giữ đơn vị gốc không rõ và mục tiêu tổng debit quan sát |
| Linux/Render/thiết bị thật/tải lớn | Không kiểm ở TASK 21B; không suy từ hash/code hoặc Deploy Live |
| Khảo sát người dùng | [TASK 21A](user-journey-qa.md) là kiểm thử bằng QA mô phỏng, [hướng dẫn dùng thử](user-trial-guide.md) mới chuẩn bị; **chưa có bằng chứng đã tổ chức khảo sát hoặc thu phản hồi thật** |

Không chạy lại toàn bộ kiểm thử/thí nghiệm vì chỉ tổng hợp tài liệu. Bốn tài liệu TASK 21B và README là đầu ra; dataset, model, workbook, prediction theo dòng, database và bằng chứng riêng giữ ngoài Git.
