# TASK 06A — Kiểm định dữ liệu phân loại trước huấn luyện

Ngày thực hiện: **20/10/2026**. Đối tượng: DoDataThings v2 tại revision đã chốt trong [khảo sát](data-survey.md). Không huấn luyện, dịch mô tả, sửa website, đọc SQLite hoặc đưa dữ liệu tải về vào Git.

## 1. Kết luận

**Có thể dùng để thử phương pháp phân loại trên dữ liệu tổng hợp tiếng Anh, sau khi chốt quy tắc nhãn và chia theo nhóm. Chưa đủ để khẳng định hiệu quả trên giao dịch thật hoặc tiếng Việt.**

- Đã đọc toàn bộ CSV: **68.000 dòng, 2 cột, 17 nhãn × 4.000 dòng**; không có ô thiếu/rỗng.
- Chỉ có **45.697 mô tả nguyên văn duy nhất**. Có **22.303 dòng dư do lặp nguyên văn**, tương đương 32,80% số dòng. Sau chuẩn hóa chữ hoa/thường và khoảng trắng, số dòng dư tăng lên **26.526** (39,01%). Những dòng này không phải 68.000 quan sát độc lập.
- **5 nhóm mô tả nguyên văn mang nhiều nhãn**, ảnh hưởng 27 dòng; sau chuẩn hóa có **6 nhóm, 37 dòng**. Không tự chọn nhãn theo số đông.
- Tiền tố là thông tin chiều tiền do bộ dữ liệu cung cấp. Phân bố thực tế khác các tỷ lệ mô tả trong card. Không được báo kết quả đầu vào có tiền tố như kết quả bài toán chỉ dùng mô tả.
- Có nhiều biến thể cùng cấu trúc câu. Phép dò gần giống chỉ là heuristic, có cả kết quả dương tính giả. **Chưa xác minh merchant và chưa có phép chia giữ riêng merchant.**
- Đã xem thủ công **85 mô tả cố định, 5 mô tả khác nhau theo khóa chuẩn hóa ở mỗi lớp**, cộng thêm các trường hợp xung đột và ví dụ gần giống. Đây không phải ước lượng tỷ lệ sai nhãn trên toàn tập.

Ký hiệu trong báo cáo: **D** = tự tính/đọc trên CSV đã khóa mã băm; **T** = tác giả mô tả; **Đ** = đánh giá hoặc đề xuất. Tên thương hiệu có thật không chứng minh bản ghi là giao dịch thật.

## 2. Nguồn, tải và giấy phép

| Thuộc tính | Giá trị đã ghi nhận |
|---|---|
| Nguồn chính thức | [DoDataThings/us-bank-transaction-categories-v2](https://huggingface.co/datasets/DoDataThings/us-bank-transaction-categories-v2) |
| Revision | `3e8d052cb7b362fb1a04b6064d2331982553ea56` |
| URL CSV đã tải | [CSV tại revision cố định](https://huggingface.co/datasets/DoDataThings/us-bank-transaction-categories-v2/resolve/3e8d052cb7b362fb1a04b6064d2331982553ea56/transactions-synthetic.csv) |
| Tài liệu nguồn | [README tại cùng revision](https://huggingface.co/datasets/DoDataThings/us-bank-transaction-categories-v2/blob/3e8d052cb7b362fb1a04b6064d2331982553ea56/README.md) |
| Cây tệp kiểm chứng | [API cây tệp tại revision](https://huggingface.co/api/datasets/DoDataThings/us-bank-transaction-categories-v2/tree/3e8d052cb7b362fb1a04b6064d2331982553ea56) |
| Hoàn tất tải ban đầu, UTC | `2026-10-20T08:57:33.443995+00:00` |
| Cùng thời điểm tại Việt Nam | `2026-10-20T15:57:33.443995+07:00` |
| Kích thước CSV | **3.461.960 byte** |
| SHA-256 CSV | `0424aed6e76f74a5b3b1ff61ccec43bc321622e6806da353b910b3b2c8108f6e` |
| Git blob SHA-1 CSV | `0099db263a31819509c27d24d605f2733608491c` |
| SHA-256 README | `fa90b2937851fae225d0d8acb11b2787852285ebc5fdf24ff7fcb86b89e0a598` |
| Thư mục riêng, bị Git bỏ qua | `data/external/dodatathings-v2/3e8d052cb7b362fb1a04b6064d2331982553ea56/` |

Script tải cả CSV và card theo revision, tính Git blob hash từ byte thực tế (`SHA1("blob " + byte_count + NUL + content)`) và đối chiếu kích thước/blob với cây tệp chính thức. Sau đó lưu SHA-256 để kiểm tra mọi lần chạy ngoại tuyến. SHA-1 dùng đối chiếu đối tượng Git, SHA-256 dùng dấu vân tay tệp. Lần chạy lại không đổi thời điểm thu nhận ban đầu. Metadata máy đọc được: [classification-source.json](metadata/classification-source.json).

**Giấy phép:** card tại revision khai báo `license: mit` và mục License ghi MIT. Cây tệp chỉ có `.gitattributes`, `README.md`, CSV; **không thấy LICENSE riêng hoặc thông báo bản quyền đầy đủ**. [Điều khoản MIT](https://opensource.org/license/mit) yêu cầu giữ thông báo bản quyền và thông báo cho phép khi phân phối bản sao/phần đáng kể; có điều khoản miễn bảo đảm. Giữ card, attribution nguồn và revision; nếu phân phối lại dữ liệu cần làm rõ thông báo bản quyền còn thiếu từ bên phát hành. Không tự tạo thông báo tác giả/năm bản quyền, không gọi dữ liệu là CC0. Đây là kiểm tra khai báo của nguồn, chưa kiểm toán độc lập quyền của từng thành phần.

**Bản chất và phạm vi:** **T:** bộ dữ liệu tổng hợp theo kiểu sao kê ngân hàng Mỹ, có tên merchant và các mã/địa chỉ được biến đổi. **D:** chỉ có chuỗi `description`, `category`; không có người dùng, tài khoản, ngày, số tiền hoặc tiền tệ. Không xác minh được số người/lịch sử vì các trường đó không tồn tại. Không dùng tập này cho dự báo tổng chi; không suy ra mọi dòng là USD hoặc là dữ liệu Việt Nam. **T:** card nói có hơn 500 merchant và tám họ định dạng; báo cáo này không kiểm đếm merchant độc lập hay kiểm toán bộ sinh.

## 3. Kiểm tra toàn bộ CSV

CSV được đọc bằng `csv.DictReader`, UTF-8 (chấp nhận BOM), giữ đúng chuỗi gốc, kiểm tra số trường từng bản ghi. ID trong báo cáo là **thứ tự bản ghi CSV bắt đầu từ 1, không tính header**, không phải số dòng vật lý của trình soạn thảo. CSV gốc được giữ nguyên.

| Kiểm tra D | Kết quả |
|---|---:|
| Bản ghi | 68.000 |
| Cột | 2: `description`, `category` |
| Bản ghi thiếu/thừa trường | 0 |
| Ô rỗng hoặc chỉ chứa khoảng trắng, `description` | 0 |
| Ô rỗng hoặc chỉ chứa khoảng trắng, `category` | 0 |
| Chuỗi giả thiếu `null`, `none`, `nan`, `n/a` (không phân biệt hoa/thường) | 0 ở cả hai cột |
| Nhãn khác nhau | 17 |
| Bản ghi không có tiền tố đầu chuỗi `[debit]`/`[credit]` | 0 |

### 3.1. Số lượng nhãn và chiều tiền

Các số trong bảng là **tự đếm từ tệp**, không sao chép metadata viewer ở `main`.

| Nhãn gốc | Tổng dòng | `[debit]` | `[credit]` | Tỷ lệ credit |
|---|---:|---:|---:|---:|
| Education | 4.000 | 3.803 | 197 | 4,925% |
| Entertainment | 4.000 | 3.770 | 230 | 5,750% |
| Fees | 4.000 | 3.805 | 195 | 4,875% |
| Groceries | 4.000 | 3.892 | 108 | 2,700% |
| Healthcare | 4.000 | 3.834 | 166 | 4,150% |
| Income | 4.000 | 0 | 4.000 | 100,000% |
| Insurance | 4.000 | 3.921 | 79 | 1,975% |
| Mortgage | 4.000 | 3.922 | 78 | 1,950% |
| Personal Care | 4.000 | 3.865 | 135 | 3,375% |
| Rent | 4.000 | 3.863 | 137 | 3,425% |
| Restaurants | 4.000 | 3.889 | 111 | 2,775% |
| Shopping | 4.000 | 3.737 | 263 | 6,575% |
| Subscription | 4.000 | 3.808 | 192 | 4,800% |
| Transfer | 4.000 | 2.550 | 1.450 | 36,250% |
| Transportation | 4.000 | 3.868 | 132 | 3,300% |
| Travel | 4.000 | 3.608 | 392 | 9,800% |
| Utilities | 4.000 | 3.872 | 128 | 3,200% |
| **Tổng** | **68.000** | **60.007** | **7.993** | **11,754%** |

**T so với D:** card nói Income 97% credit, Transfer 50/50, các lớp chi 95% trở lên là debit. CSV này có Income 100% credit, Transfer 63,75% debit/36,25% credit; Entertainment, Shopping, Travel có debit lần lượt 94,25%, 93,425%, 90,2%. Vì vậy tỷ lệ tác giả mô tả không được dùng thay thống kê thực tế. Không thể từ đây xác định nguyên nhân khác biệt trong bộ sinh.

### 3.2. Trùng và xung đột nhãn

Các khóa được tính trên **mọi dòng**:

1. **Nguyên văn:** so sánh chuỗi `description` chính xác, gồm tiền tố.
2. **Chuẩn hóa:** Unicode NFC, `casefold()`, gộp mọi khoảng trắng Unicode thành một dấu cách, bỏ khoảng trắng hai đầu; giữ dấu câu và tiền tố. Không dịch, sửa chính tả, xóa merchant.
3. **Bỏ chiều tiền:** bỏ đúng tiền tố ở đầu bằng regex không phân biệt hoa/thường, rồi chuẩn hóa như trên.
4. **Mẫu câu heuristic:** từ khóa bỏ chiều tiền, che mã sau `PPD ID:`/`WEB ID:`, che token có chữ số ngay sau `*`, che các chuỗi chữ số, gộp dấu câu/khoảng trắng, giữ từ còn lại. Đây là khóa thăm dò rò rỉ, không phải dữ liệu đã làm sạch hoặc merchant ID.

| Khóa | Khóa duy nhất | Nhóm trùng ≥2 dòng | Dòng nằm trong nhóm trùng | Dòng dư N−số khóa | Nhóm nhiều nhãn | Dòng trong nhóm nhiều nhãn |
|---|---:|---:|---:|---:|---:|---:|
| Nguyên văn | 45.697 | 5.177 | 27.480 | 22.303 | 5 | 27 |
| Chuẩn hóa | 41.474 | 4.746 | 31.272 | 26.526 | 6 | 37 |
| Bỏ chiều tiền | 40.512 | 4.700 | 32.188 | 27.488 | 6 | 38 |
| Mẫu câu heuristic | 23.037 | 7.129 | 52.092 | 44.963 | 16 | 117 |

“Dòng dư” không bằng số dòng nằm trong nhóm trùng. Ví dụ nhóm 3 dòng đóng góp 1 nhóm, 3 dòng tham gia, 2 dòng dư. Khi gộp các nhóm nhỏ, số nhóm trùng có thể giảm dù số dòng tham gia tăng. Không cộng chồng các hàng của bảng vì chúng là các phép đo lồng nhau. Chuẩn hóa làm thay đổi chuỗi của 61.680 dòng; số khóa giảm thêm 4.223 so với nguyên văn.

Ví dụ nguyên văn lặp nhiều nhất: `[debit] MORTGAGE PAYMENT` có **445 dòng**. Nhóm lớn nhất theo khóa chuẩn hóa có 607 dòng; bỏ tiền tố có 618 dòng. Mô tả chung như vậy có thể bị ghi nhớ nếu chia từng dòng ngẫu nhiên.

Đã đọc trực tiếp **toàn bộ 5 nhóm xung đột nguyên văn**, không chỉ xem cặp ví dụ:

| Mô tả nguyên văn | Hai nhãn xuất hiện | ID đại diện mỗi nhãn |
|---|---|---|
| `[debit] PYPL *RITE AID` | Shopping / Healthcare | 944 / 34154 |
| `[debit] PP*RITE AID` | Healthcare / Shopping | 8592 / 47829 |
| `[debit] PYPL*WALGREENS` | Healthcare / Shopping | 11626 / 48300 |
| `[debit] BATH & BODY WORKS` | Personal Care / Shopping | 16318 / 29143 |
| `[debit] PYPL*RITE AID` | Healthcare / Shopping | 40783 / 66315 |

Nhóm mới sau chuẩn hóa: `rite aid - philadelphia`, ID 15609 Shopping và 37513 Healthcare, khác chữ hoa/thường. Thêm biến thể chữ hoa/thường vào các nhóm sẵn có làm tổng số dòng xung đột thành 37. Sau bỏ tiền tố, dòng credit 59773 của Bath & Body Works làm tổng tăng thành 38. Các mẫu bán lẻ/dược phẩm này **không đủ thông tin mặt hàng để xác định duy nhất mục đích mua**. Nhãn đang mâu thuẫn theo đầu vào quan sát được; chưa kết luận từng bản ghi phản ánh một giao dịch thật bị gán sai.

### 3.3. Ảnh hưởng tiền tố

- Bỏ tiền tố làm số khóa duy nhất giảm **962**. Có **962 nhóm thân mô tả xuất hiện với nhiều chiều tiền**, bao phủ **13.785 dòng**. Con số dòng này gồm mọi lần lặp của nhóm, không phải số cặp debit/credit độc lập.
- Trong CSV, chiều tiền là tín hiệu mạnh cho Income: mọi Income đều credit, nhưng **3.993 dòng credit còn lại không mang nhãn Income**. Không dùng quy tắc credit = thu nhập hoặc debit = chi tiêu.
- Chẩn đoán thống kê: nếu chọn nhãn đông nhất riêng trong từng nhóm debit/credit trên chính tập này, đúng **7.922/68.000 = 11,65%** (credit chọn Income, debit chọn Mortgage). Đây chỉ là phép tính bảng chéo, **không phải kết quả huấn luyện hoặc độ chính xác test**. Nhãn đơn đông nhất trên toàn tập chỉ chiếm 1/17 ≈ 5,88%.
- Đề xuất bài toán chính sau này dùng **thân mô tả không tiền tố**, để phù hợp yêu cầu phân loại từ mô tả. Nếu chạy thêm cấu hình có chiều tiền, phải gọi rõ là đầu vào “mô tả + chiều tiền”, dùng cùng nhóm/chia và báo riêng. Tiền tố được bỏ chỉ trong bộ nhớ của script kiểm tra; CSV gốc không đổi.
- Không đẩy các biến thể cùng thân nhưng khác chiều tiền sang hai tập khác nhau. Nếu ngữ nghĩa cần chiều tiền mà đầu vào chính không có, giữ trạng thái cần xem lại thay vì hứa phân biệt được chỉ bằng văn bản.

### 3.4. Mẫu câu và các cặp gần giống

Ví dụ đã đối chiếu: ID **2438, 11026, 14849** đều có merchant text LOANDEPOT MORTGAGE nhưng số và mã WEB khác nhau; khóa mẫu `loandepot mortgage <n> web id <ref>` bao phủ **26 dòng**, gồm ID 66218 trong mẫu thủ công. Chia theo nguyên văn sẽ không giữ được toàn bộ họ biến thể này cùng nhau.

Phép dò gần giống chạy trên **23.037 khóa mẫu duy nhất**, theo hai thứ tự sắp xếp: chuỗi xuôi và chuỗi đảo ký tự. Với mỗi khóa lấy hai hàng xóm tiếp theo trong từng thứ tự, gộp cặp không hướng. Lọc tỷ số độ dài ≥0,80, Jaccard tập token ≥0,60, rồi dùng `difflib.SequenceMatcher(autojunk=False)` với tỷ lệ ≥0,92.

**D:** có **92.066 cặp ứng viên**, **11.947** cặp qua bộ lọc để tính SequenceMatcher, **832 cặp khóa mẫu** đạt ngưỡng. **102 cặp** có tổng tập nhãn của hai phía lớn hơn một nhãn. Đây không phải 832 cặp bản ghi gốc hoặc 102 lỗi nhãn đã xác nhận. Không duyệt toàn bộ mọi cặp O(N²), nên vẫn có thể bỏ sót họ mẫu.

Ví dụ xem thủ công:

- ID **2852/36189**: `24 HOUR FITNESS.COM` và `24 HOUR FITNESS CORP`, cùng Personal Care, tỷ lệ 0,926829 trên khóa mẫu. Có dấu hiệu biến thể tên, chưa có merchant ID để chứng minh đồng nhất pháp nhân.
- ID **61015/37087**: AFLAC cùng cấu trúc địa chỉ ở Raleigh, tỷ lệ 0,952381. Đây là biến thể mẫu địa chỉ nhìn thấy trực tiếp.
- ID **39985/64370**: AETNA/NOTION có cấu trúc địa chỉ tương tự, tỷ lệ 0,921348, nhưng nhãn Insurance/Subscription và tên merchant khác nhau. **Đây là dương tính giả nếu dùng độ giống chuỗi để nhận diện cùng merchant.**

Khóa mẫu có thể che cả chữ số có ý nghĩa trong tên thương hiệu, số địa chỉ, mã bưu chính và làm các giao dịch khác nhau va chạm. Nó cũng giữ lại nhiều cách viết merchant/địa chỉ khác nhau nên có thể chia nhỏ cùng một họ. Các họ câu chung như PayPal/ACH có thể xuất hiện ở nhiều lớp; không gom mọi dòng có chữ PayPal thành một merchant hay một nhãn Transfer. **Không có số merchant đã xác minh trong kết quả này.**

## 4. Kiểm tra thủ công mẫu cố định

Chọn mẫu độc lập cho từng nhãn: chuẩn hóa mô tả như mục 3.2; trong mỗi nhãn lấy mỗi khóa một lần, bản ghi đại diện là lần xuất hiện đầu trong CSV. Xếp tăng theo SHA-256 của chuỗi UTF-8 `task06a-manual-v1|category|normalized_description`; lấy 5 khóa đầu, dùng khóa chữ làm tiêu chí phụ. Cố định seed, revision và ID để người khác chọn lại đúng 85 mô tả. Phân biệt nhãn khi lấy mẫu nên một mô tả xung đột có thể xuất hiện ở hai lớp nếu được chọn.

Đã đọc **cả 5 mô tả ở từng dòng bảng dưới đây**. Nhận xét chỉ dựa vào văn bản quan sát được, không có hóa đơn để xác nhận ý nghĩa kinh tế. Danh sách đầy đủ và văn bản gốc nằm cục bộ trong `audit/manual-samples.json` dưới thư mục dữ liệu, không đưa vào Git.

| Nhãn | 5 ID theo thứ tự chọn | Nhận xét thủ công |
|---|---|---|
| Education | 57461, 19952, 16246, 50544, 38657 | Tên nhà xuất bản/dịch vụ học. 16246 là credit PEARSON; có thể là hoàn tiền, chưa xác minh. Không nên biến thành khoản chi dương chỉ từ nhãn. |
| Entertainment | 23108, 56137, 9943, 9139, 61813 | Công viên, rạp phim, hồ bơi, CLIMBING GYM, bảo tàng. Ranh giới hoạt động thể chất với Personal Care cần quy ước. |
| Fees | 65986, 8323, 12096, 25963, 60157 | Mô tả phí. Hậu tố như `61/38`, `96/33` không dùng làm ngày lịch. 60157 là credit LATE PAYMENT FEE: chưa rõ hoàn phí hay nhiễu bộ sinh. |
| Groceries | 60936, 36147, 45059, 50477, 40582 | Tên cửa hàng thực phẩm/bán sỉ, có dạng rút gọn SMARTFINAL. Không có mặt hàng, không xác nhận toàn bộ mua tại đây là thực phẩm. |
| Healthcare | 52444, 11607, 44583, 37969, 1380 | Cơ sở/dịch vụ y tế; có mã WEB và chữ thường. Không thấy xung đột hiển nhiên trong 5 mẫu; không xác minh được dịch vụ đã mua. |
| Income | 12710, 21979, 57984, 34648, 1776 | Có payroll/nền tảng việc làm. 34648 là Zelle payment from một tên người: tiền nhận có thể là hoàn ứng/chuyển khoản, mô tả không đủ chứng minh thu nhập. Tên trong tệp do nguồn tổng hợp cung cấp. |
| Insurance | 58895, 13031, 39409, 45185, 52683 | Tên nhà bảo hiểm và premium/billing. 39409 dính `SHIELDINSURANCE`; định dạng tổng hợp không luôn có khoảng trắng tự nhiên. |
| Mortgage | 66218, 27879, 572, 38524, 57597 | Có từ mortgage và mã khoản thanh toán. 572 dính `LOANSMORTGAGE`, 27879 lặp MORTGAGE. Không đủ số tiền/thông tin để tách gốc/lãi. |
| Personal Care | 18115, 16324, 2296, 6700, 53990 | Tóc, thể hình, sản phẩm chăm sóc. 53990 Bath & Body Works có ranh giới Shopping; đã thấy xung đột cùng thương hiệu ở mục 3.2. |
| Rent | 26858, 30994, 61645, 67880, 60884 | Có rent/rent pmt. 26858 là credit; 30994 có `[credit] Withdrawal from ...`, chiều tiền và từ “Withdrawal” không nhất quán bề mặt. Không tự sửa bằng suy đoán. |
| Restaurants | 3258, 17078, 1446, 22579, 15286 | Tên đồ ăn/quán ăn và wrapper PayPal. 3258 có `INST XFER` nhưng nhãn Restaurants: wrapper chuyển tiền không đủ để gán Transfer. |
| Shopping | 40061, 21242, 63424, 37412, 19755 | Amazon/Walmart/Target. AMZN DIGITAL chưa đủ để phân biệt mua một lần/đăng ký; 19755 credit TARGET chưa rõ hoàn tiền. |
| Subscription | 58710, 37820, 37204, 24207, 40337 | SaaS/dịch vụ và APPLE.COM/BILL. Tên nhà cung cấp không chứng minh tính định kỳ; 24207 là credit. |
| Transfer | 52960, 23676, 23816, 17800, 30149 | PayPal, chuyển từ account, moneylink. Có cả hai chiều. Không biết hai tài khoản có cùng chủ; chuyển cho tên người chưa đủ xác định chi tiêu hay chuyển nội bộ. |
| Transportation | 55830, 65623, 22289, 23223, 35657 | Nhiên liệu/chuyến Lyft; mô tả ngắn có mã. Không có hóa đơn để xác nhận từng mặt hàng tại trạm xăng. |
| Travel | 26995, 64439, 41931, 37329, 59738 | Khách sạn, precheck, đỗ xe sân bay, cruise, nền tảng du lịch. 41931 có thể thuộc Transportation theo cách chia khác; cần quy ước. |
| Utilities | 38136, 46172, 10183, 20911, 27602 | Điện thoại, rác, nước, điện. 20911 dính `SERVICESCOLLECTION`; không đủ thông tin về kỳ hóa đơn. |

Mẫu cố định ưu tiên khả năng kiểm tra lại, **không phải lấy ngẫu nhiên các giao dịch độc lập**, không đại diện tỷ trọng thật. Ngoài mẫu này đã đọc các nhóm xung đột nguyên văn và các ví dụ gần giống nêu trên. Việc kiểm tra nhãn sâu hơn vẫn cần quy tắc phân loại/mặt hàng; không có đánh giá “tỷ lệ đúng thủ công” từ 85 mẫu này.

## 5. Bộ nhãn chuẩn và ánh xạ danh mục cá nhân — đề xuất

Giữ **17 lớp nguồn ở lớp phân loại chung** để truy vết, dùng mã ổn định dưới đây. Đây là đề xuất, **chưa đổi dữ liệu hoặc danh mục website**. Tên danh mục minh họa do người dùng chọn; không dịch mô tả nguồn thành dữ liệu tiếng Việt.

| Nhãn nguồn | Mã nhãn chuẩn | Gợi ý nhóm danh mục cá nhân |
|---|---|---|
| Restaurants | `restaurants` | Ăn uống ngoài |
| Groceries | `groceries` | Thực phẩm/đi chợ |
| Shopping | `shopping` | Mua sắm |
| Transportation | `transportation` | Đi lại |
| Entertainment | `entertainment` | Giải trí |
| Utilities | `utilities` | Điện, nước, viễn thông |
| Subscription | `subscription` | Dịch vụ đăng ký |
| Healthcare | `healthcare` | Y tế |
| Insurance | `insurance` | Bảo hiểm |
| Mortgage | `mortgage` | Thanh toán vay mua nhà |
| Rent | `rent` | Tiền thuê nhà |
| Travel | `travel` | Du lịch |
| Education | `education` | Học tập |
| Personal Care | `personal_care` | Chăm sóc cá nhân |
| Transfer | `transfer` | Luồng chuyển tiền riêng, cần người dùng xác nhận |
| Income | `income` | Thu nhập, cần xác minh nguồn/loại thu |
| Fees | `fees` | Phí |

Quy tắc cần chốt trước huấn luyện:

1. Tách **mục đích/danh mục**, **chiều tiền** và **bản chất luồng tiền**. Nhãn nguồn không quyết định một mình loại thu/chi. Credit ở một lớp chi có thể là hoàn tiền/điều chỉnh; không tự đổi sang Income hoặc ghi thêm một khoản chi. Do không có liên kết giao dịch gốc, đây chỉ là khả năng, chưa xác nhận bản ghi nào là hoàn tiền.
2. **Transfer không tự coi là chi tiêu hoặc thu nhập.** Không đủ dữ liệu để chứng minh chuyển nội bộ cùng chủ. Nhãn gợi ý Transfer phải để riêng/chờ xác nhận. Website hiện chỉ có thu/chi: chưa có chỗ biểu diễn chuyển khoản thì giữ chưa ánh xạ, không ép vào loại chi cho vừa schema. Bước này không sửa schema.
3. `mortgage` biểu thị thanh toán theo dòng tiền trong dữ liệu, không tách được gốc/lãi; cách tính tổng chi sau này phải công bố chính sách. Subscription là taxonomy của nguồn, chưa chứng minh mua định kỳ. Ranh giới gym, đỗ xe sân bay, pharmacy, Bath & Body Works cần quy ước và/hoặc người dùng chọn.
4. Ánh xạ nên có khóa `(user_id, canonical_label, transaction_kind)` tới `category_id` do **chính tài khoản đó** sở hữu và đúng loại. Nhiều nhãn chung có thể cùng một danh mục của người dùng, ví dụ Restaurants/Groceries → Ăn uống nếu họ muốn. Một nhãn chung có nhiều danh mục con thì cần chọn thêm bằng người dùng, không suy đoán ID.
5. Thiếu ánh xạ, đầu vào không đủ rõ hoặc mâu thuẫn chiều tiền: trả trạng thái **cần xem lại/chưa ánh xạ**. Đây là trạng thái xử lý, không thêm nhãn huấn luyện “Other” bằng dữ liệu tự sinh. Không tự tạo danh mục, thay danh mục đã chọn hoặc dùng ánh xạ của người khác. Các kiểm tra sở hữu/loại ở website sau này vẫn phải thực hiện phía máy chủ.
6. Tối thiểu cách ly khỏi đánh giá tự động **6 nhóm thân mô tả mâu thuẫn, 38 dòng** để xét thủ công theo chính sách. Xem thêm 16 nhóm mẫu nhiều nhãn/117 dòng và các cặp gần giống; chúng có thể là va chạm heuristic, không tự đổi hoặc xóa nhãn toàn bộ. Các tập này giao nhau, không cộng thành tổng lỗi.

CSV gốc chưa bị loại dòng/gộp lớp/sửa nhãn. Trước thí nghiệm chính thức cần lưu riêng danh sách quyết định có phiên bản, lý do và người duyệt; báo cả số dòng còn lại từng lớp.

## 6. Chia train/validation/test theo nhóm — đề xuất và thăm dò

**Không có thời gian/người dùng/merchant ID trong schema.** Không thể tạo chia theo người, theo ngày hay bảo đảm merchant holdout từ hai cột này. Không lấy một phần của cùng bộ sinh hoặc v1 cùng nguồn làm tập kiểm chứng độc lập.

### 6.1. Thăm dò đã chạy, chưa là bộ chia cuối cùng

Script tạo đồ thị bằng union-find trên mọi bản ghi: nối các dòng có cùng thân mô tả chuẩn hóa, cùng khóa mẫu, và nối các nhóm của 832 cặp gần giống đạt ngưỡng. Lấy thành phần liên thông làm nhóm, **không dùng nhãn để quyết định có nối hay không**. Cách này giữ cả các biến thể debit/credit cùng nhau, đồng thời có thể gom quá rộng do địa chỉ chung.

**D:** thu được **22.243 nhóm ứng viên**, nhóm lớn nhất **618 dòng**, **90 nhóm có nhiều nhãn**. Nhóm nhiều nhãn không đồng nghĩa sai nhãn: có thể chỉ do chuỗi địa chỉ chung hoặc quy tắc gom quá rộng. Cần xem lại trước khi khóa cách chia.

Để kiểm tra cơ chế nhóm, script phân bổ minh họa bằng hash: đại diện nhóm là thân mô tả nhỏ nhất theo thứ tự chữ; lấy 16 ký tự hex đầu của SHA-256 UTF-8 `task06a-split-v1|representative`, đổi sang số rồi modulo 100; 0–69 train, 70–84 validation, 85–99 test. Không dùng nhãn và không huấn luyện. Danh sách ID theo nhóm/phân vùng chỉ lưu cục bộ ở `audit/candidate-groups.json`.

| Phân vùng minh họa | Dòng | Tỷ lệ |
|---|---:|---:|
| Train | 47.718 | 70,174% |
| Validation | 10.354 | 15,226% |
| Test | 9.928 | 14,600% |

Đã đếm giao nhau giữa các phân vùng: **0 khóa nguyên văn, 0 khóa chuẩn hóa, 0 khóa bỏ chiều tiền và 0 khóa mẫu đã định nghĩa xuất hiện ở nhiều phân vùng**. Mọi cạnh gần giống đã phát hiện được nối chung nhóm. Kết quả này **chỉ chứng minh không giao nhau theo các quy tắc đang dùng**, không chứng minh không còn rò rỉ merchant/mẫu chưa phát hiện.

Đối chứng không huấn luyện: phân từng bản ghi bằng hash `task06a-naive-v1|record_id`, cùng ngưỡng 70/15/15, có **3.385 khóa nguyên văn**, **3.253 khóa chuẩn hóa**, **3.260 khóa bỏ chiều tiền**, **5.105 khóa mẫu** xuất hiện ở nhiều phân vùng. Đây là số khóa bị giao nhau, không phải điểm dự đoán. Nó cho thấy chia theo dòng không xử lý được các mẫu lặp.

Hash theo nhóm chưa phân tầng: Fees có **1.858/1.285/857** dòng train/validation/test, Shopping **2.721/928/351**; tỷ trọng nhãn lệch dù toàn tập gốc cân bằng. Không chuyển dòng lẻ qua tập khác để ép tỷ lệ. [Metadata kiểm định](metadata/classification-audit.json) có bảng đủ 17 lớp cho từng phân vùng.

### 6.2. Quy trình đề xuất trước khi huấn luyện

1. Chốt ngữ nghĩa nhãn/chiều tiền; duyệt các nhóm xung đột, tạo bảng loại/cách ly có lý do và phiên bản. Không giải quyết bằng nhãn của tập test hoặc bằng việc thử mô hình rồi sửa test cho điểm đẹp.
2. Chốt heuristic nhóm sau xem cả trường hợp gom sai (AETNA/NOTION) và bỏ sót; ghi phiên bản/hash script. Hạn chế vừa lựa chọn cách chia vừa nhìn kết quả mô hình trên test.
3. Trên dữ liệu đủ điều kiện, dùng chia **theo toàn nhóm**, mục tiêu khoảng 70/15/15; phân tầng gần đúng theo vector số nhãn của mỗi nhóm (hoặc thuật toán chia nhóm có phân tầng), cố định seed. Kiểm tra từng lớp có đủ nhóm và số lượng ở mỗi tập, báo mức lệch thực tế. Không hứa đạt đúng tỷ lệ khi nhóm lớn hoặc nhiều nhãn.
4. Lưu manifest nhóm/ID và SHA-256 cục bộ; kiểm tra giao nhau bằng cả bốn khóa trên và các cạnh gần giống đã duyệt. Báo số dòng, số khóa độc lập, số nhóm, số nhãn và số bị cách ly. Khóa test một lần; chỉ dùng train/validation để chọn xử lý và tham số sau này.
5. Khi huấn luyện ở task riêng, fit từ vựng/TF-IDF và mọi bước học từ dữ liệu trên train; chỉ transform validation/test. Báo macro-F1, từng lớp và ma trận nhầm lẫn trên cấu hình bỏ tiền tố; cấu hình có chiều tiền phải báo riêng trên cùng phân vùng. Chưa có điểm số trong task này.
6. Nếu muốn phát biểu về merchant chưa gặp, phải có merchant ID đáng tin hoặc bảng chuẩn hóa tên được duyệt để chia riêng và kiểm tra giao nhau. Script hiện **không làm được việc đó**. Muốn đánh giá người Việt cần tập tiếng Việt thật có quyền sử dụng ở bước khác; đổi tiền hoặc dịch bộ tổng hợp không cung cấp bằng chứng đó.

**Chưa khóa tập train/validation/test dùng cho huấn luyện.** Việc phân vùng ở trên chỉ kiểm tra khả năng vận hành của cách gom nhóm trên tệp gốc, còn cả dòng chưa được xét nhãn. Những con số này không phải số lượng sau làm sạch.

## 7. Tái lập bằng PowerShell và các tệp

Không cần cài thêm thư viện. Script dùng thư viện chuẩn Python, không import Django, không gọi database và không fit mô hình. Từ thư mục dự án:

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'

# Lần đầu trên máy chưa có dữ liệu: tải đúng revision và kiểm tra blob/SHA.
.\.venv\Scripts\python.exe -X utf8 scripts\audit_classification_data.py --download

# Các lần sau: ngoại tuyến, kiểm tra SHA trước khi đọc CSV.
.\.venv\Scripts\python.exe -X utf8 scripts\audit_classification_data.py

# Kiểm tra logic chuẩn hóa, nhóm, trùng và lấy mẫu; không gọi website/network.
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s scripts -p 'test_audit_classification_data.py' -v

# Xác nhận dữ liệu tải về bị loại khỏi Git.
git check-ignore -v -- 'data/external/dodatathings-v2/3e8d052cb7b362fb1a04b6064d2331982553ea56/transactions-synthetic.csv'
git status --short --untracked-files=all
```

`--download --download-only` chỉ thu nhận/kiểm chứng nguồn. `--download` khi đã có metadata đối chiếu SHA và giữ thời điểm tải đầu, không âm thầm ghi đè tệp khác nội dung. Không có cờ nhận đường dẫn dữ liệu người dùng hoặc tùy chọn ép bỏ qua mã băm.

| Tệp | Nội dung/chính sách Git |
|---|---|
| `scripts/audit_classification_data.py` | Mã tải/kiểm định chạy lại được, cho phép chia sẻ |
| `scripts/test_audit_classification_data.py` | Kiểm thử logic bằng chuỗi trong bộ nhớ, không tạo tập giao dịch giả |
| `docs/metadata/classification-source.json` | URL, revision, thời điểm, kích thước, hash, khai báo giấy phép; cho phép chia sẻ |
| `docs/metadata/classification-audit.json` | Số đếm tổng hợp, tham số phương pháp, hash script, bảng nhãn và phân vùng minh họa; không chứa mô tả giao dịch |
| `docs/classification-data-audit.md` | Báo cáo này; chỉ trích các ví dụ tổng hợp cần thiết |
| `data/external/dodatathings-v2/<revision>/transactions-synthetic.csv`, `README.md` | Bản gốc và card tải về; nằm ngoài Git |
| `data/external/dodatathings-v2/<revision>/audit/` | Mẫu thủ công có văn bản gốc, ID xung đột, cặp gần giống, manifest nhóm minh họa; nằm ngoài Git |

`.gitignore` hiện có `data/` và `*.csv`, đã đủ; **không sửa hoặc nới quy tắc loại trừ**. Không đưa dữ liệu cá nhân, tệp website, khóa cấu hình hay SQLite vào đầu vào kiểm định hoặc metadata chia sẻ. Giữ nguyên `docs/data-survey.md` để phân biệt khảo sát ban đầu với kiểm định toàn tệp ở bước này.

## 8. Kết quả thực thi và giới hạn

- Tải thành công từ URL chính thức tại revision đã ghi; kích thước và Git blob khớp cây tệp, có SHA-256 CSV/card.
- Đã chạy kiểm định toàn CSV và kiểm tra mẫu thủ công như mục 4; thống kê lưu bằng JSON có thể đối chiếu với báo cáo.
- **9/9 kiểm thử logic đạt**. Chạy lại ngoại tuyến cho kết quả **giống từng byte ở cả 6 tệp JSON** (2 metadata chia sẻ và 4 kết quả cục bộ); hash script khớp trường `script_sha256` trong metadata. SHA-256 JSON tổng hợp tại lần kiểm tra: `2e6f51a4e9bd8908ff4e170b38b8548311f8556226e9322f8a96a8f60d052ff3`.
- Đã đối chiếu độc lập bằng pandas hiện có trong `.venv`: số dòng/nhãn, ô rỗng, 45.697 mô tả nguyên văn duy nhất, 22.303 dòng dư và đúng nhãn/văn bản của toàn bộ 85 ID mẫu đều khớp. pandas chỉ dùng ở bước đối chiếu, script chính không phụ thuộc pandas.
- Rà Git: chỉ có 5 tệp mới là báo cáo, 2 metadata, script và kiểm thử; CSV và kết quả có văn bản gốc bị `data/` loại trừ, không có tệp dữ liệu nào đã được theo dõi. `requirements.txt`, `.gitignore`, khảo sát cũ và mã website không có thay đổi. Chưa commit/push trong task này.
- Các điều còn thiếu trước thí nghiệm chính thức: chính sách nhãn ở vùng chồng lấn, xử lý dòng mâu thuẫn/credit, duyệt heuristic nhóm và phân tầng; chưa có test độc lập từ giao dịch thật/tiếng Việt. Không coi tuyên bố hiệu quả mô hình trong card là kết quả đã tái lập.
