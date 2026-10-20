# TASK 05 — Khảo sát dữ liệu cho hai bài toán học máy

Ngày kiểm tra: **20/10/2026**, theo múi giờ Việt Nam.

Phạm vi: khảo sát nguồn công khai, tài liệu, giấy phép, metadata và mẫu tổng hợp nhỏ. Không sửa website, cài thư viện, đọc cơ sở dữ liệu người dùng, thu thập dữ liệu riêng tư, sinh dữ liệu mới hoặc huấn luyện mô hình.

## 1. Kết luận và lựa chọn

| Bài toán | Nguồn chính đề xuất | Phương án dự phòng | Giới hạn của quyết định |
|---|---|---|---|
| **A. Phân loại danh mục từ mô tả** | **DoDataThings v2**, để thử phương pháp trên dữ liệu tổng hợp tiếng Anh | **DoDataThings v1**, nhỏ hơn, không có tiền tố chiều tiền | Chưa có tập giao dịch tiếng Việt thật đã xác minh để đánh giá khả năng dùng cho người Việt. Hai phiên bản cùng nguồn, không phải hai tập kiểm chứng độc lập. |
| **B. Dự báo tổng chi theo lịch sử từng người** | **Lịch sử thật do người tham gia tự nguyện cung cấp**, ưu tiên lịch sử có sẵn và đủ dài; đây là kế hoạch thu thập, **chưa có dữ liệu được bàn giao/kiểm tra** | **Bộ sinh mbazouz**, chỉ để thử quy trình trên chuỗi tổng hợp, với điều kiện sử dụng nêu bên dưới | **Chưa chốt được nguồn thật công khai đáp ứng đồng thời lịch sử cá nhân, quyền sử dụng và khả năng áp dụng cho Việt Nam.** Không được báo kết quả trên dữ liệu tổng hợp như hiệu quả dự báo chi tiêu thật. |

IBM TabFormer và MoneyData/MoneyVis là ứng viên bổ sung có điều kiện, chưa nên dùng ngay. Bộ mitulshah có trở ngại truy cập và nguồn gốc thành phần dữ liệu. UCI Online Retail không đại diện cho toàn bộ chi tiêu cá nhân.

Đây là kết luận trong phạm vi tìm kiếm của bước này, **không phải khẳng định rằng không tồn tại dữ liệu phù hợp trên Internet**.

## 2. Cách đọc mức độ kiểm chứng

| Ký hiệu | Ý nghĩa |
|---|---|
| **D — dữ liệu mẫu** | Đã kiểm tra trực tiếp các dòng của mẫu tổng hợp nhỏ; chỉ kết luận trong mẫu đó. |
| **M — metadata** | Đã đọc phản hồi API, schema, thống kê của nền tảng hoặc metadata tệp. Không đồng nghĩa đã tự đếm toàn bộ dữ liệu gốc. |
| **T — tác giả** | Tác giả/đơn vị công bố viết trong dataset card, README hoặc bài báo; chưa xác minh độc lập bằng toàn bộ dữ liệu. |
| **C — mã nguồn** | Đã đọc cấu hình hoặc mã xử lý, chưa thực thi bộ sinh/thí nghiệm. |
| **Đ — đánh giá** | Nhận định áp dụng cho khóa luận, dựa trên các bằng chứng đã nêu. |

Số dòng không tự động là số giao dịch độc lập; mã tài khoản không tự động là một người; khoảng thời gian toàn bộ tệp không tự động là lịch sử của từng người. Không suy đoán tiền tệ chỉ từ quốc gia hoặc ký hiệu `$`.

## 3. Nguồn cho A — phân loại mô tả

### A1. DoDataThings/us-bank-transaction-categories-v2 — nguồn chính thử phương pháp

**Nguồn gốc và quyền sử dụng:** [dataset](https://huggingface.co/datasets/DoDataThings/us-bank-transaction-categories-v2), [card tại revision đã ghi nhận](https://huggingface.co/datasets/DoDataThings/us-bank-transaction-categories-v2/blob/3e8d052cb7b362fb1a04b6064d2331982553ea56/README.md), [API kho](https://huggingface.co/api/datasets/DoDataThings/us-bank-transaction-categories-v2). Card và metadata khai báo **MIT**; cây tệp API chỉ liệt kê card, CSV và `.gitattributes`, chưa thấy tệp LICENSE riêng. Khi sử dụng cần giữ thông báo tác giả/giấy phép theo [điều khoản MIT](https://opensource.org/license/mit), không tự đổi thành CC0. Đây là giấy phép do bên phát hành khai báo, không phải một cuộc kiểm toán quyền sở hữu toàn bộ thành phần.

| Nội dung | Kết quả |
|---|---|
| Thật/tổng hợp | **T:** tác giả công bố là tổng hợp theo định dạng sao kê Mỹ; tên thương hiệu thật không biến bản ghi thành giao dịch thật. |
| Ngôn ngữ, tiền tệ | **M/T:** tiếng Anh. **M/D:** không có cột tiền tệ hoặc số tiền; không thể khẳng định mọi dòng là USD, càng không phải VND. |
| Schema | **M/D:** đúng hai cột chuỗi `description`, `category`; đã xem 3 dòng tổng hợp qua API. Mẫu có tiền tố `[debit]`. Card mô tả thêm `[credit]`. |
| Quy mô | **M:** dịch vụ size/statistics báo **68.000 dòng**, **17 nhãn**, mỗi nhãn **4.000 dòng**, `partial=false`; chưa tự đếm CSV. |
| Người và lịch sử | Không có `user_id`, ngày hay số tiền trong schema; số người và lịch sử mỗi người **không xác định/không áp dụng**. Không dùng làm B. |

**Danh sách nhãn:** Restaurants, Groceries, Shopping, Transportation, Entertainment, Utilities, Subscription, Healthcare, Insurance, Mortgage, Rent, Travel, Education, Personal Care, Transfer, Income, Fees. Danh sách và tần suất trên đã đối chiếu [API statistics](https://datasets-server.huggingface.co/statistics?dataset=DoDataThings%2Fus-bank-transaction-categories-v2&config=default&split=train); [API size](https://datasets-server.huggingface.co/size?dataset=DoDataThings%2Fus-bank-transaction-categories-v2) báo tệp gốc **3.461.960 byte**. [API 3 dòng](https://datasets-server.huggingface.co/rows?dataset=DoDataThings%2Fus-bank-transaction-categories-v2&config=default&split=train&offset=0&length=3) dùng để kiểm tra schema/mẫu, không suy ra chất lượng toàn tập.

**Tải và tái lập:** API kho trả HTTP 200, `private=false`, `gated=false`; tệp `transactions-synthetic.csv` được liệt kê. Chưa tải toàn bộ, chưa xác minh đầu cuối đường tải CSV. Revision: `3e8d052cb7b362fb1a04b6064d2331982553ea56`. Khi làm thí nghiệm phải tải theo revision, ghi SHA-256 của CSV, đếm lại nhãn và kiểm tra trùng. API viewer/statistics đã gọi ở `main`, không phải bằng chứng kiểm đếm mật mã gắn với revision đó.

**Hạn chế cho Việt Nam — Đ:** khác ngôn ngữ, merchant, kiểu sao kê và cách người dùng tự ghi chú. `[debit]/[credit]` làm đầu vào khác bài toán chỉ dùng mô tả: phải công bố rõ có thêm loại thu/chi hay loại bỏ tiền tố và đánh giá lại. `Transfer` không đồng nghĩa chi tiêu; tiền vào cũng không luôn là thu nhập. Nhãn cân bằng nhân tạo không phản ánh tần suất thực. Chưa kiểm tra trùng hoặc rò rỉ mẫu merchant giữa train/test; không chấp nhận chỉ số tốt chỉ từ chia ngẫu nhiên.

### A2. DoDataThings/us-bank-transaction-categories v1 — dự phòng

**Nguồn:** [dataset v1](https://huggingface.co/datasets/DoDataThings/us-bank-transaction-categories), [card cố định revision](https://huggingface.co/datasets/DoDataThings/us-bank-transaction-categories/blob/52c743e136de9fe7749183541c8e1260786c6df7/README.md), [API kho](https://huggingface.co/api/datasets/DoDataThings/us-bank-transaction-categories). Card/metadata khai báo **MIT**, cùng lưu ý về thông báo bản quyền như A1; không suy giấy phép dataset từ giấy phép mô hình DistilBERT đi kèm.

| Nội dung | Kết quả |
|---|---|
| Bản chất, ngôn ngữ | **T/M:** tổng hợp, tiếng Anh, mô phỏng định dạng ngân hàng Mỹ. |
| Cột và tiền tệ | **M/D:** `description`, `category`; 3 mẫu đã xem không có tiền tố chiều tiền như v2. Không có amount/currency/date/user_id; tiền tệ và lịch sử mỗi người không xác định. |
| Quy mô | **M:** [size](https://datasets-server.huggingface.co/size?dataset=DoDataThings%2Fus-bank-transaction-categories) báo **16.000 dòng**, tệp gốc **672.211 byte**; [statistics](https://datasets-server.huggingface.co/statistics?dataset=DoDataThings%2Fus-bank-transaction-categories&config=default&split=train) báo **16 nhãn × 1.000 dòng**, `partial=false`. Chưa tự đếm toàn CSV. |
| Nhãn | Restaurants, Groceries, Shopping, Transportation, Entertainment, Utilities, Subscription, Healthcare, Insurance, **Housing**, Travel, Education, Personal Care, Transfer, Income, Fees. |
| Truy cập/tái lập | API HTTP 200, `gated=false`; có CSV; chưa tải đầy đủ. Revision `52c743e136de9fe7749183541c8e1260786c6df7`. |

**Đ:** nhỏ, tiện cho thử nghiệm ban đầu; vẫn không giải quyết thiếu dữ liệu tiếng Việt thật hoặc dữ liệu B. Không gộp v1 vào v2 rồi dùng một bản làm test độc lập vì cùng bộ sinh/merchant và có thể giao nhau. `Housing` không khớp trực tiếp với `Rent`/`Mortgage` của v2.

**Sai khác tài liệu đã phát hiện:** phần thông báo cập nhật của card v1 gọi v2 là 24.000 mẫu/16 nhãn; card v2 hiện ghi 68.000/17 và metadata viewer cũng báo 68.000/17. Vì vậy báo cáo phải ghi đúng phiên bản, không sao chép con số từ thông báo cũ.

### A3. mitulshah/transaction-categorization — chưa chốt làm dự phòng

Nguồn: [card](https://huggingface.co/datasets/mitulshah/transaction-categorization/blob/main/README.md), [API](https://huggingface.co/api/datasets/mitulshah/transaction-categorization). Revision ghi nhận: `8597493f0aaa44c540c16458b18b17e4ada2f5cc`.

- **T:** 4.501.043 dòng, 10 nhãn, tổng hợp trộn nguồn giao dịch thật bên ngoài; tỷ lệ và quyền của từng nguồn thật chưa xác minh. Không gọi toàn bộ là dữ liệu thật hoặc tổng hợp thuần.
- **T:** tiếng Anh; USD, GBP, CAD, AUD, INR. Schema công bố: `transaction_description`, `category`, `country`, `currency`; không có người/ngày/amount để làm B.
- **T:** nhãn: Food & Dining; Transportation; Shopping & Retail; Entertainment & Recreation; Healthcare & Medical; Utilities & Services; Financial Services; Income; Government & Legal; Charity & Donations. Chưa kiểm nhãn bằng dữ liệu.
- **M:** card/API khai báo MIT; API trả `gated="auto"`. Đọc `dataset_info.json` tại revision qua đường raw trả **HTTP 401** trong phiên này. Chưa chấp nhận điều khoản, dùng token hoặc tải Parquet khoảng 71 MB mà card nêu.
- **Đ:** cần giải quyết quyền truy cập, chuỗi nguồn gốc/giấy phép thành phần thật, kiểm trùng và khác biệt tiếng Việt trước khi dùng. Số dòng và nội dung schema ở trên là tác giả công bố, không phải kết quả tự kiểm tệp.

## 4. Nguồn cho B — dự báo theo lịch sử cá nhân

### B1. mbazouz/synthetic-bank-dataset — dự phòng mô phỏng có kiểm soát

**Nguồn:** [kho gốc](https://github.com/mbazouz/synthetic-bank-dataset), [README cố định](https://github.com/mbazouz/synthetic-bank-dataset/blob/7418fa18ebc261c81a0133ead633d63e84a03cf9/README.md), [LICENSE](https://github.com/mbazouz/synthetic-bank-dataset/blob/7418fa18ebc261c81a0133ead633d63e84a03cf9/LICENSE), [NOTICE](https://github.com/mbazouz/synthetic-bank-dataset/blob/7418fa18ebc261c81a0133ead633d63e84a03cf9/NOTICE).

**Quyền sử dụng — M/T:** phần mềm công bố **PolyForm Noncommercial 1.0.0**, cho mục đích phi thương mại, bao gồm nghiên cứu/giáo dục; sử dụng thương mại cần giấy phép riêng. Khi phân phối phần mềm phải giữ điều khoản và thông báo yêu cầu. README/NOTICE nói đầu ra hoàn toàn tổng hợp, nhưng chưa thấy giấy phép dữ liệu đầu ra riêng: **không tự gán MIT, CC0 hoặc quyền thương mại cho CSV/mô hình được tạo**. Đề xuất dùng bộ sinh cho nghiên cứu cục bộ phi thương mại; làm rõ quyền đầu ra trước khi phát hành dữ liệu hoặc mô hình ra ngoài.

**Bản chất — T:** toàn bộ được sinh; không coi tên người, số tài khoản hoặc dòng ví dụ là giao dịch của người thật. Không tải mẫu customers/accounts chứa thông tin định danh tổng hợp vì không cần cho khảo sát.

Đã đọc [mẫu transactions.csv](https://github.com/mbazouz/synthetic-bank-dataset/blob/7418fa18ebc261c81a0133ead633d63e84a03cf9/samples/transactions.csv), **62.804 byte**, và xử lý trong bộ nhớ, không lưu bản sao.

| Thuộc tính | D — kiểm trực tiếp mẫu nhỏ |
|---|---|
| Quy mô | **300 dòng**, **2 customer_id**, **3 account_id**; là mẫu cắt, không phải quy mô cả bộ sinh. |
| Khách hàng thứ nhất | 205 dòng; 01/01/2024–31/03/2024; 3 tháng có giao dịch. |
| Khách hàng thứ hai | 95 dòng; 01/01/2024–29/01/2024; 1 tháng có giao dịch. |
| Ngôn ngữ/tiền | Mẫu hiển thị nhãn tiếng Anh và `currency=USD`; không có VND. Không chứng minh cả bộ sinh chỉ có USD. |
| Nhãn category trong mẫu | `dining`, `finance`, `groceries`, `health`, `housing`, `income`, `shopping`, `subscriptions`, `telecom`, `transport`, `travel`, `utilities` — **12 nhãn quan sát**, không khẳng định là toàn bộ taxonomy. |

**Schema mẫu đã kiểm:** `transaction_id`, `account_id`, `customer_id`, `timestamp`, `amount`, `currency`, `merchant_name`, `merchant_category`, `merchant_mcc`, `transaction_type`, `payment_channel`, `city`, `country`, `counterparty_iban`, `label`, `category`, `subcategory`, `is_subscription`, `is_salary`, `is_transfer`, `is_cash_withdrawal`, `balance_after_transaction`.

Không nhầm schema mẫu/raw này với schema `delivery` của README dùng cột `date`. [Taxonomy JSON](https://github.com/mbazouz/synthetic-bank-dataset/blob/7418fa18ebc261c81a0133ead633d63e84a03cf9/categories.json) trong kho còn có token tiếng Pháp; phải đối chiếu locale đầu ra, không áp nguyên danh sách đó cho mẫu Mỹ.

**Khả năng tạo lịch sử — C/T:** [CLI](https://github.com/mbazouz/synthetic-bank-dataset/blob/7418fa18ebc261c81a0133ead633d63e84a03cf9/bank_gen/main.py) có `--customers`, `--start`, `--end`, `--seed`. [Config](https://github.com/mbazouz/synthetic-bank-dataset/blob/7418fa18ebc261c81a0133ead633d63e84a03cf9/bank_gen/config.py) đặt mặc định cuối kỳ là `date.today()`, đầu kỳ lùi `365*3` ngày. README mô tả locale US/UK/FR với USD/GBP/EUR, tính mùa vụ và khoản định kỳ. Chưa chạy nên **chưa xác minh** số giao dịch, số khách thực sinh hay lịch sử tối thiểu của mỗi người. Mẫu hiện có quá ngắn để đánh giá dự báo tháng đáng tin cậy.

**Tái lập — Đ:** cố định commit `7418fa18ebc261c81a0133ead633d63e84a03cf9`, dependency của công cụ, locale, số khách, ngày bắt đầu/kết thúc và seed. Không dùng mặc định “hôm nay”. README lưu ý UUID giao dịch vẫn ngẫu nhiên, nên cùng seed chưa bảo đảm CSV giống từng byte; cần kiểm hash cột nghiệp vụ sau sắp xếp. Chưa kiểm tra tương thích bộ sinh với Python 3.13; không cài dependency bộ sinh vào `.venv` của website ở bước này.

**Hạn chế Việt Nam — Đ:** mùa vụ, tiền tệ, hồ sơ và merchant đều do quy tắc sinh đặt ra. Đổi đơn vị sang VND không biến thành hành vi người Việt. Cần loại chuyển tiền nội bộ, rút ATM và tài khoản kinh doanh theo định nghĩa mục tiêu; không cộng mọi dòng âm thành chi tiêu cá nhân. Kết quả tốt có thể chỉ là mô hình học lại quy luật bộ sinh.

### B2. IBM TabFormer — ứng viên lớn, chưa ưu tiên

Nguồn: [kho IBM](https://github.com/IBM/TabFormer), [README](https://github.com/IBM/TabFormer/blob/ebb7cd68ee1897599568107740bc452104bbbaf8/README.md), [mã đọc dữ liệu](https://github.com/IBM/TabFormer/blob/ebb7cd68ee1897599568107740bc452104bbbaf8/dataset/card.py), [LICENSE](https://github.com/IBM/TabFormer/blob/ebb7cd68ee1897599568107740bc452104bbbaf8/LICENSE).

- **T:** dữ liệu thẻ tổng hợp, README nêu khoảng **24 triệu bản ghi**. Chưa kiểm đếm; số người và lịch sử mỗi người **chưa xác minh**. Không đưa con số từ bản sao Kaggle vào làm số liệu gốc.
- **C:** bộ đọc tham chiếu `User`, `Card`, `Year`, `Month`, `Day`, `Time`, `Amount`, `Use Chip`, `Merchant Name`, `Merchant City`, `Merchant State`, `Zip`, `MCC`, `Errors?`, `Is Fraud?`. README nêu 12 trường nhưng mã chọn 12 trường **sau xử lý thời gian**, không đủ để kết luận CSV gốc có đúng 12 cột.
- **C/T:** tên cột tiếng Anh; xử lý amount bỏ ký tự đầu. Chưa xem tệp gốc để kiểm đơn vị tiền; **không mặc định USD từ ký hiệu tiền**. `MCC` là mã ngành merchant, `Is Fraud?` là nhãn gian lận, không phải bộ nhãn danh mục cá nhân đã được kiểm chứng.
- **M:** kho có Apache-2.0. README thư mục dữ liệu chỉ chỉ sang [Box của IBM](https://ibm.box.com/v/tabformer-data); chưa thấy thông báo riêng áp dụng rõ cho archive. Không tự kết luận giấy phép mã nguồn bao phủ toàn bộ dữ liệu tải từ Box.
- **M:** chỉ đọc [con trỏ Git LFS](https://raw.githubusercontent.com/IBM/TabFormer/ebb7cd68ee1897599568107740bc452104bbbaf8/data/credit_card/transactions.tgz), 134 byte; nó khai báo archive **278.576.638 byte**, SHA-256 `e9f589a0958f40d60f81b1a2e8428db86e00c05755caf44fb055827976c0efa2`. Không tải archive; chưa kiểm truy cập/tải hoàn tất trên LFS hoặc Box.
- **Đ:** chỉ cân nhắc sau khi rõ quyền archive, schema, lịch sử từng User và lấy được lát cắt toàn lịch sử của một số người. Giới hạn dữ liệu thẻ và khác biệt thị trường khiến nó không đại diện tổng chi VND; không thích hợp A từ mô tả tự do theo schema đã thấy.

### B3. MoneyData/MoneyVis — nguồn thật được mô tả, quyền tái sử dụng còn thiếu

Nguồn: [bài báo của nhóm nghiên cứu](https://people.cs.nott.ac.uk/blaramee/research/financeVis/firat23moneyVis.pdf), [trang xuất bản](https://diglib.eg.org/items/e5a24478-3ec5-4e33-bab1-e5b27b06c6bd), [kho nhóm tác giả](https://github.com/thevisgroup/MoneyVis), [API giấy phép kho](https://api.github.com/repos/thevisgroup/MoneyVis).

| Nội dung | Kết quả |
|---|---|
| Bản chất/quy mô | **T:** dữ liệu ngân hàng thật đã ẩn danh của một khách hàng, hơn 6.500 giao dịch, khoảng 7 năm từ 07/2015. Chưa kiểm tệp để xác nhận số người/tài khoản, số dòng hay độ đầy đủ. |
| Cột/nhãn | **T:** ngày, loại giao dịch, mô tả, debit/credit amount, balance; có phân loại thủ công và dựa trên quy tắc. Ví dụ nhóm Shopping, Groceries, Utility Bills; loại ngân hàng gồm BGC, BP, DEB, TFR. Chưa xác nhận schema và toàn bộ nhãn trong CSV. |
| Ngôn ngữ/tiền | Bài báo và ví dụ dùng tiếng Anh/ngân hàng UK; mã tiền tệ của tệp chưa được kiểm, không mặc định GBP chỉ từ UK. |
| Quyền và tải | Bài báo có điều khoản CC Attribution cho **bài báo**, không tự áp cho dataset. API kho báo `license=null`; API thư mục liệt kê `data.csv` 420.184 byte. Không tải CSV hoặc mở bảng dữ liệu thật qua liên kết rút gọn trong paper. Quyền dùng/phát hành dữ liệu còn cần làm rõ. |

**Đ:** có tiềm năng thử một chuỗi cá nhân dài nếu quyền sử dụng được xác nhận; một khách hàng không chứng minh tổng quát cho nhiều người Việt. Paper còn nêu ngày cuối tuần được ngân hàng hạch toán sang thứ Hai; cần phân biệt ngày chi thực với ngày ghi sổ. Chưa chốt làm nguồn chính hoặc dự phòng sẵn dùng.

**Tái lập:** hiện chưa có revision/hash của tệp giao dịch được cấp quyền sử dụng hoặc thống kê đếm lại, nên chưa thể cam kết tái lập thí nghiệm từ nguồn này. Nếu giải quyết được quyền dùng, cần cố định bản dữ liệu và bộ quy tắc gán nhãn, không chỉ dẫn tên bài báo.

## 5. Nguồn loại khỏi lựa chọn chính: UCI Online Retail

Nguồn gốc: [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail), DOI `10.24432/C5BW33`.

**T:** bán hàng thật tại một nhà bán lẻ trực tuyến UK, nhiều khách bán buôn; 541.909 dòng, khoảng 01/12/2010–09/12/2011. Đây không phải 541.909 giao dịch ngân hàng độc lập. Cột công bố: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`; `Description` là tên sản phẩm tiếng Anh, `UnitPrice` tính bằng sterling, không phải VND. Không có nhãn danh mục chi tiêu cá nhân. Số người và lịch sử từng người chưa kiểm chứng.

**Quyền/tải — T/M:** trang UCI ghi CC BY 4.0, cần ghi công, liên kết giấy phép và chỉ rõ chỉnh sửa; tệp XLSX được niêm yết khoảng 22,6 MB. Chưa tải/đọc workbook hoặc kiểm đường tải hoàn tất.

**Đ:** có thể nghiên cứu doanh số/mua hàng ở nhà bán lẻ này, không suy ra tổng chi của một người ở các cửa hàng, tiền nhà, đi lại, y tế… Một invoice có nhiều dòng, hoàn/hủy đơn cần xử lý riêng. Không chọn cho A hoặc B của đề tài hiện tại.

**Tái lập:** DOI giúp định danh nguồn; nếu dùng cho một bài toán bán lẻ khác, vẫn cần lưu hash workbook và quy tắc ghép invoice/hoàn hủy. Chưa chạy thí nghiệm trên nguồn này.

## 6. Nguồn thật Việt Nam còn thiếu và phương án thu thập

Đã tìm các cụm từ về Vietnamese/Vietnam transaction categorization, mô tả giao dịch, personal expense histories và nguồn ngân hàng tổng hợp. Trong các kết quả đã kiểm, chưa xác minh được bộ công khai tiếng Việt thật có nhãn chi tiêu, quyền dùng rõ và lịch sử cá nhân đủ dài. Không dùng SMS spam/scam, dữ liệu marketing ngân hàng hay nhóm chuyển tiền làm nhãn nhu cầu chi tiêu.

**Nguồn chính đích cho B** là lịch sử của chính người tham gia qua [website cục bộ](http://127.0.0.1:8001/) hoặc dữ liệu họ có quyền cung cấp. Đây là kế hoạch, không phải bộ dữ liệu đang có; không truy vấn dữ liệu website trong TASK 05.

| Nội dung cần chuẩn bị | Đề xuất cho bước sau — chưa thực hiện |
|---|---|
| Quyền sử dụng | Có sự đồng ý rõ cho nghiên cứu, phạm vi sử dụng, lưu giữ và chia sẻ kết quả; không coi tài khoản website là đồng ý dùng dữ liệu huấn luyện. Không có giấy phép mở mặc định cho dữ liệu cá nhân. |
| Cột cho A | `description`, nhãn chuẩn đã kiểm thủ công, loại thu/chi nếu dùng làm đầu vào; bỏ tên, số tài khoản, số điện thoại và mã tham chiếu không cần thiết. |
| Cột cho B | Mã người giả danh ổn định, ngày, amount Decimal, currency VND, kind và dấu cờ chuyển nội bộ/hoàn tiền nếu có; biết khoảng thời gian quan sát và mức đầy đủ. |
| Số lượng | Chưa có số giao dịch/người được xác minh; không điền con số giả. Đề xuất nhắm lịch sử có sẵn **12–24 tháng/người** nếu dự báo theo tháng, chỉ là mục tiêu thiết kế, không phải ngưỡng bảo đảm mô hình tốt. |
| Hạn chế thời gian | Sáu tuần không tạo ra lịch sử nhiều tháng mới. Nếu không có lịch sử cũ được phép dùng, phải giới hạn kết luận vào mô phỏng hoặc hoãn đánh giá dự báo thật. |
| Tái lập và riêng tư | Ghi phiên bản schema, mốc thời gian, hash dữ liệu đã khử định danh, quy tắc lọc và tập chia; dữ liệu gốc giữ riêng. Chia sẻ quy trình và thống kê phù hợp, không công bố bản ghi riêng tư theo mặc định. |

Đối với A, vẫn cần tập kiểm thử tiếng Việt thật do người tham gia tự ghi và gán nhãn, kể cả khi thử phương pháp bằng nguồn tiếng Anh. Dữ liệu tự viết theo kịch bản hoặc dịch máy phải gắn nhãn **tổng hợp/dịch**, để riêng, không được gọi là giao dịch tiếng Việt thật. Dịch mô tả hoặc quy đổi tiền không làm nguồn nước ngoài trở thành dữ liệu Việt Nam.

## 7. Thiết kế thí nghiệm đề xuất cho bước sau

Các mục sau chỉ là thiết kế, chưa chạy và chưa có chỉ số kết quả.

### A — định nghĩa nhãn và tránh rò rỉ

1. Chốt bộ nhãn chuẩn trước, ghi bảng ánh xạ nhãn nguồn sang nhãn đề tài; không đồng nhất ID danh mục riêng của từng người. Danh mục người dùng tự đặt có thể không suy ra được từ mô tả.
2. Chốt đầu vào là mô tả thuần hay mô tả + loại thu/chi; công bố rõ xử lý `[debit]/[credit]`. Không trộn Transfer vào chi tiêu hoặc biến mọi credit thành Income.
3. Kiểm trùng chính xác/gần trùng và nhóm mẫu cùng merchant/template trước khi chia dữ liệu; các biến thể của cùng mô tả không nên rơi vào cả train và test.
4. Có thể thử baseline TF-IDF ký tự/từ + bộ phân loại tuyến tính. Chỉ fit tiền xử lý trên train. Báo macro-F1, theo từng lớp, ma trận nhầm lẫn và các trường hợp không đủ thông tin; kết quả trên tiếng Anh tổng hợp phải mang đúng tên đó.
5. Đánh giá tiếng Việt thật bằng tập độc lập, không dịch tập test từ chính dữ liệu train. Các ghi chú như “CK” có thể không đủ thông tin để xác định mục đích chi tiêu.

### B — định nghĩa tổng chi và đánh giá theo thời gian

1. Ưu tiên mục tiêu một tháng tiếp theo để khớp trang tổng quan hiện có. Tổng hợp riêng theo người và tháng, dùng Decimal cho tiền VND; không gộp nhiều người thành một chuỗi rồi gọi là cá nhân hóa.
2. Thống nhất cách tính chuyển nội bộ, rút tiền mặt, hoàn tiền, trả nợ thẻ và khoản kinh doanh để tránh đếm đôi. Chỉ có dữ liệu một thẻ/tài khoản thì mục tiêu là chi được quan sát ở nguồn đó, chưa phải toàn bộ chi tiêu của người đó.
3. Khoảng quan sát không đầy đủ hoặc tháng mất dữ liệu không được tự điền 0; tháng thật sự không chi mới là 0. Không dùng tháng hiện tại chưa kết thúc làm tháng đủ.
4. Chia theo thời gian và đánh giá cuốn chiếu: dự báo tại một mốc chỉ dùng dữ liệu trước mốc đó. Giữ các tháng cuối để kiểm thử, không chia ngẫu nhiên giao dịch. Báo riêng người đã có lịch sử và người mới nếu dùng mô hình chung.
5. So sánh trước với chi tháng trước và trung bình các tháng gần nhất; chỉ xét ML khi có đủ điểm thời gian. Báo MAE theo đơn vị tiền gốc và sai lệch; tránh MAPE ở tháng tổng chi bằng 0. Không so sánh MAE USD trực tiếp với MAE VND.
6. Với bộ sinh, cố định lịch sử dài và kiểm độ phủ từng người sau khi sinh; không lấy 300 dòng mẫu B1 làm benchmark dự báo tháng. Mô phỏng tốt không chứng minh khả năng dự báo trên người dùng thật.

## 8. Nhật ký kiểm tra và khả năng tái lập khảo sát

### Đã làm trong bước này

- Đọc trang gốc, card, giấy phép, paper và API công khai; không đăng nhập hoặc chấp nhận thêm điều khoản thay người dùng.
- Đọc API size/statistics và đúng **3 dòng mẫu tổng hợp cho mỗi DoDataThings v1/v2**. Không tải hai CSV đầy đủ. Thống kê 16.000/68.000 là kết quả dịch vụ metadata, không phải đếm cục bộ.
- Đọc một CSV mẫu tổng hợp B1 **62.804 byte/300 dòng** trong bộ nhớ, đếm customer/account và lấy min/max timestamp theo customer. Không lưu các dòng mẫu vào tài liệu.
- Đọc con trỏ LFS IBM **134 byte**, không tải archive khoảng 278,6 MB; không tải CSV MoneyVis, Parquet mitulshah hoặc XLSX UCI.
- Đọc mã nguồn bộ sinh/cấu hình dưới dạng văn bản; không clone kho lớn, cài dependency hoặc thực thi bộ sinh.
- Chỉ tạo tài liệu này trong workspace. Không sửa mã website, `requirements.txt`, `.venv` hoặc dữ liệu SQLite.

### Các điểm chưa xác minh

- Chất lượng toàn tập, số mẫu mô tả độc nhất, tỷ lệ trùng/gán nhãn sai, phân bố merchant của A1/A2.
- Tải đầy đủ và hash nội dung A1/A2 theo revision đã ghi; thống kê API `main` có thể thay đổi sau ngày khảo sát.
- Lịch sử đủ dài mỗi người, số dòng sau lọc chi tiêu thực và quyền phát hành dữ liệu đầu ra của B1; tính tái lập khi thực chạy và Python 3.13.
- Quyền archive, số người, độ dài lịch sử, đơn vị tiền và nội dung thực của IBM; quyền tái sử dụng dataset và dữ liệu thực của MoneyVis.
- Tập giao dịch tiếng Việt thật được phép dùng cho A và lịch sử chi tiêu VND cá nhân đủ dài cho B.

### Mốc phiên bản đã ghi nhận từ API

| Nguồn | Revision |
|---|---|
| DoDataThings v2 | `3e8d052cb7b362fb1a04b6064d2331982553ea56` |
| DoDataThings v1 | `52c743e136de9fe7749183541c8e1260786c6df7` |
| mitulshah | `8597493f0aaa44c540c16458b18b17e4ada2f5cc` |
| mbazouz generator | `7418fa18ebc261c81a0133ead633d63e84a03cf9` |
| IBM TabFormer | `ebb7cd68ee1897599568107740bc452104bbbaf8` |

Những endpoint metadata đã dùng được dẫn ngay tại từng nguồn. Khi triển khai bước sau, cần lưu response metadata, thời điểm truy cập, giấy phép và hash tệp trong hồ sơ thí nghiệm; khảo sát này không lưu bản sao dữ liệu giao dịch. Chưa có lý do để sửa chức năng website hoặc huấn luyện ở TASK 05.

## 9. TASK 05B — Khả thi dự báo khi mở rộng ra quốc tế

Ngày bổ sung: **20/10/2026**. Phần 1–8 được giữ nguyên như hồ sơ TASK 05. Phần này cập nhật kết luận về B khi **không bắt buộc tiếng Việt hoặc VND**; các kết luận về thiếu dữ liệu tiếng Việt ở trên không phải lý do để loại nguồn quốc tế.

### 9.1. Kết luận mới và mức độ sẵn sàng

**Ứng viên chính: MoneyData — bản phát hành Bank Transactions Dataset trên Mendeley Data.** Đã xác minh được nguồn do thành viên nhóm nghiên cứu công bố, giấy phép **của dataset** và metadata tệp tải. Nhận định “quyền tái sử dụng còn thiếu” tại B3 được cập nhật cho **bản phát hành Mendeley cụ thể này**, không tự áp giấy phép đó cho mọi bản sao GitHub hoặc bản đã chỉnh sửa khác.

Nguồn này có triển vọng cho **nghiên cứu trường hợp một khách hàng**, dự báo theo tháng trên dòng tiền được ghi nhận qua nguồn tài khoản này. Chưa có bằng chứng để gọi đó là toàn bộ chi tiêu cá nhân, chuỗi được quan sát đầy đủ mọi ngày, hoặc benchmark nhiều người. Chưa tải workbook để kiểm toán nội dung nên quyết định hiện tại là **chọn nguồn để kiểm tra dữ liệu tiếp**, chưa xác nhận dữ liệu đã sẵn sàng huấn luyện.

| Mục tiêu | Đánh giá khả thi ở thời điểm khảo sát |
|---|---|
| Dự báo tổng ghi nợ hạch toán của nguồn tài khoản này trong tháng tiếp theo | **Có triển vọng, có điều kiện:** phải kiểm ngày/số tiền, lịch sử và các tháng quan sát của workbook. Tên mục tiêu phải là “ghi nợ quan sát”, không tự đổi thành “tổng chi tiêu”. |
| Dự báo chi tiêu đã ghi nhận sau loại trừ các dòng không phải chi tiêu | **Có điều kiện bổ sung:** phải có quy tắc/kiểm nhãn chuyển khoản, rút tiền, đầu tư, thu nhập và hoàn tiền. |
| Dự báo toàn bộ chi tiêu thực của một người, kể cả tiền mặt/tài khoản ngoài dữ liệu | **Chưa được nguồn chứng minh.** |
| Đánh giá mô hình tổng quát cho nhiều người dùng hoặc người Việt | **Không thể kết luận từ một khách hàng.** Cần dữ liệu nhiều người độc lập; không nhân bản một chuỗi để tạo người dùng giả. |

Đề xuất dự phòng: giữ bộ sinh B1 cho kiểm thử phương pháp tổng hợp; Berka/PKDD là ứng viên thật nhiều tài khoản cần làm rõ điều kiện dùng và độ phủ; Salad Money có nguồn gốc rõ nhưng yêu cầu môi trường nghiên cứu an toàn nên chưa phù hợp chạy trên máy cá nhân trong kế hoạch hiện tại.

### 9.2. Các nguồn quốc tế được đối chiếu thêm

| Nguồn gốc | Thật/tổng hợp; định danh và thời gian | Điều kiện sử dụng, truy cập | Kết luận khảo sát |
|---|---|---|---|
| [MoneyData / Mendeley, V1](https://data.mendeley.com/datasets/dnxtg6n4rv/1), DOI `10.17632/dnxtg6n4rv.1` | **T:** ngân hàng thật đã ẩn danh, một khách hàng, khoảng 7 năm; có ngày, ghi nợ/ghi có. Số tài khoản và ID trong workbook chưa kiểm. | **M:** trang phát hành ghi CC BY 4.0; API tệp và HEAD công khai thành công. Tệp khoảng 0,51 MB. | **Ưu tiên kiểm tra tiếp**, phù hợp quy mô khóa luận như một nghiên cứu trường hợp; phân tích chi tiết ở 9.3–9.6. |
| [Berka/PKDD'99 qua CTU Financial](https://relational.fel.cvut.cz/dataset/Financial); CTU dẫn về [trang ban tổ chức lưu trữ](https://web.archive.org/web/20180506061559/http://lisp.vse.cz/pkdd99/Challenge/chall.htm) | **M:** CTU ghi loại dữ liệu Real, có bảng `trans` và trường thời gian. Trang hiện có 8 bảng, tổng 1.090.086 hàng **toàn cơ sở dữ liệu**, không phải số giao dịch. Số người và phân bố lịch sử từng người chưa xác minh từ nguồn gốc trong bước này. | **M:** CTU hướng dẫn truy cập MariaDB công khai, nhưng trang kiểm được chưa nêu giấy phép dataset rõ. Trang gốc cũ không truy cập được; không suy giấy phép từ các mirror. Không kết nối hoặc tải bảng giao dịch. | Tiềm năng nếu cần nhiều tài khoản; **chưa chốt** vì thiếu điều kiện dùng và xác nhận độ phủ. Không lấy khoảng năm toàn bộ dữ liệu làm số năm của mỗi người. |
| [Salad Money — GeoDS](https://data.geods.ac.uk/dataset/salad-money-open-banking-transaction-data) | **T:** dữ liệu thực lấy qua Open Banking của người xin vay tại UK, GBP, có tổng số giao dịch và số tiền theo ngày/loại/danh mục/người; khi có nhiều tài khoản được cộng theo người. Nguồn ghi thời kỳ từ 04/2020, hơn 200 triệu hàng, **không công bố ở trang này số người hoặc lịch sử từng người**. | **M/T:** `Other (Not Open)`, mức Secure; dữ liệu nền chỉ dùng trong Trusted Research Environment, đối tượng nghiên cứu tại cơ sở UK và/hoặc email `ac.uk`, cần đề xuất và xét quyền. Không đăng ký, yêu cầu quyền hoặc tải dữ liệu. | Nguồn phù hợp về cấu trúc hơn dữ liệu bán lẻ, nhưng **chưa phải dữ liệu tải về dùng ngay trên máy**. Tập daily volumes/values tổng hợp được liên kết không thay thế chuỗi từng người. |
| [Zia Data Labs — FreeFinancialTransactions50M](https://huggingface.co/datasets/ziadatalabs/FreeFinancialTransactions50M) | **T:** 50 triệu giao dịch hoàn toàn tổng hợp; có `account_id`, timestamp, amount, currency, transaction_type, status. Card không nêu số account hoặc độ dài/độ liên tục từng account. | **M/T:** card/API ghi CC BY-NC 4.0, `gated=false`; tệp Parquet được mô tả khoảng 1,5 GB. Chỉ đọc card/API, không tải Parquet hay mẫu giao dịch. | Có tên nhãn refund/transfer nhưng **chưa chứng minh** có chuỗi chi tiêu đủ dài hoặc mask quan sát; không ưu tiên chỉ vì nhiều dòng. |

Các số CTU, Salad và Zia ở bảng trên là thông tin trang nguồn/metadata, không phải kết quả tự đếm dữ liệu. CTU trả HTTP 200 qua yêu cầu HTTP tại máy dù công cụ đọc web bị timeout; API CKAN Salad timeout nhưng trang giới thiệu chính thức đọc được. Không coi lỗi công cụ là bằng chứng dataset bị xóa.

Với Zia, API tại ngày kiểm ghi revision `98cf38f9b2f1a9994930f52a4d490cb2b5777acc`; card còn dùng tên `FreeSyntheticFinancialTransactions50M` trong ví dụ `load_dataset`, khác ID kho đã kiểm. Chưa chạy ví dụ; đây là thêm một điểm cần sửa/kiểm nếu chọn nguồn sau này. Nguồn: [API metadata](https://huggingface.co/api/datasets/ziadatalabs/FreeFinancialTransactions50M), [card theo revision](https://huggingface.co/datasets/ziadatalabs/FreeFinancialTransactions50M/blob/98cf38f9b2f1a9994930f52a4d490cb2b5777acc/README.md).

Không đưa UCI Online Retail trở lại lựa chọn B: dữ liệu của một nhà bán lẻ vẫn không quan sát được tổng chi của người mua ở nơi khác. Không quy đổi các nguồn trên sang VND để gọi là dữ liệu Việt Nam.

### 9.3. MoneyData: nguồn gốc, giấy phép và tệp cụ thể

**Bằng chứng về phát hành — M:** [trang Mendeley V1](https://data.mendeley.com/datasets/dnxtg6n4rv/1) ghi người đóng góp **Robert Laramee**, University of Nottingham, ngày công bố **14/01/2026**, DOI `10.17632/dnxtg6n4rv.1`, liên hệ trực tiếp với bài báo MoneyVis 2023. Trang này ghi **CC BY 4.0 cho dataset**, thay vì chỉ giấy phép bài báo.

Theo [điều khoản CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), khi sử dụng/phân phối bản thích nghi cần ghi công, dẫn nguồn/giấy phép và nêu thay đổi, không ngụ ý tác giả bảo chứng. Việc có giấy phép không phải bằng chứng mọi rủi ro riêng tư đã được kiểm toán; ở bước khảo sát không lấy bản ghi tài chính thật về máy.

[API danh sách tệp V1](https://data.mendeley.com/public-api/datasets/dnxtg6n4rv/files?folder_id=root&version=1) trả HTTP 200 và liệt kê một workbook:

| Trường metadata | Giá trị đã kiểm |
|---|---|
| Tên tệp | `laramee26openBankTransactionData.xlsx` |
| File ID | `36b3d359-2491-4282-850f-3f03e00fbfe3` |
| Dung lượng | **507.389 byte**, theo API; chưa tự tải để đo lại |
| Trạng thái | `COMPLETED` |
| SHA-256 do kho công bố | `716eaf9ad4a3cf60dc9c9c8a20ed9a917c545a1b5f139f40ed91d2104faa3ff7` |
| Đường tải do API cung cấp | [file_downloaded](https://data.mendeley.com/public-files/datasets/dnxtg6n4rv/files/36b3d359-2491-4282-850f-3f03e00fbfe3/file_downloaded) |
| Kiểm khả năng tải | Gửi **HEAD** tới đường tải trả **HTTP 200**, Content-Type của XLSX. Không gửi GET nội dung workbook; HEAD không phải kiểm tải đủ/hash cục bộ. |

DOI, version, file ID và hash công bố giúp cố định nguồn cho thí nghiệm sau. Chưa xác minh tên sheet, số dòng, các ID, mã tiền tệ, ngày đầu/cuối hoặc độ đầy đủ **trong chính workbook phát hành năm 2026**. Không mặc định workbook mới giống từng dòng với `data.csv` của kho MoneyVis năm 2023.

### 9.4. MoneyData: trả lời năm câu hỏi về tính khả thi

#### (1) Giao dịch thực hay tổng hợp?

**T:** trang Mendeley và [bài báo MoneyVis](https://people.cs.nott.ac.uk/blaramee/research/financeVis/firat23moneyVis.pdf) mô tả giao dịch ngân hàng **thực tế đã ẩn danh**; không phải dữ liệu do bộ sinh tạo. Paper cho biết tên và thông tin nhận diện được loại hoặc thay tên giả. Đây là xác nhận theo nhóm công bố, **chưa phải kiểm chứng độc lập hồ sơ giao dịch thật**. Bước 05B không tải dòng giao dịch để đối chiếu.

#### (2) Có bao nhiêu người, mỗi người có bao lâu lịch sử?

**T:** paper trình bày dữ liệu của **một khách hàng**; trang Mendeley mô tả **hơn 6.500 giao dịch**, lịch sử **khoảng 7 năm bắt đầu từ tháng 07/2015**. Không diễn giải năm phát hành 2026 là ngày giao dịch cuối. Chưa xác minh số dòng chính xác, số tháng đầy đủ, các khoảng thiếu và số tài khoản trong workbook hiện tại.

Paper nói thông tin nhận diện tài khoản đã được bỏ. Vì vậy chưa xác minh có `user_id/account_id` ổn định trong XLSX; đây **không phải tập nhiều người có ID đã kiểm**. Nếu tài liệu/tệp xác nhận là một chuỗi, có thể đặt một mã chuỗi kỹ thuật khi tiền xử lý ở bước sau; mã đó chỉ định danh chuỗi, không tạo thêm người và không khôi phục ID thật.

#### (3) Có tách ngày không chi tiêu với ngày thiếu ghi nhận không?

**Chưa xác minh được.** Không thấy tài liệu nêu bảng độ phủ, cờ mất dữ liệu, ngày bắt đầu/kết thúc hiệu lực của nguồn ghi nhận hoặc lịch đối soát xác nhận mọi ngày đều đầy đủ. Khoảng bảy năm không chứng minh quan sát liên tục từng ngày/tháng.

**T, paper mục Data Idiosyncrasies:** giao dịch thứ Bảy/Chủ nhật được ngân hàng ghi sang thứ Hai, dữ liệu không có giờ giao dịch. Do đó ngày cuối tuần không có dòng **không chứng minh không phát sinh chi tiêu**. Ngày ghi sổ và ngày chi thực không được đồng nhất; cuối tuần ở ranh giới tháng cũng có thể làm lệch tổng giữa hai tháng.

**Đ, cách xử lý:** không reindex rồi tự điền mọi ngày/tháng trống bằng 0. Tách ba trạng thái: có bản ghi; không có bản ghi nhưng độ phủ đã được xác nhận; chưa biết độ phủ. Chỉ trạng thái thứ hai mới có cơ sở gán 0 cho **dòng tiền ghi nhận theo ngày hạch toán**, không phải toàn bộ chi thực của người đó. Số dư có thể hỗ trợ đối soát nếu thứ tự và phạm vi tài khoản rõ, nhưng tự nó không chứng minh không thiếu dữ liệu.

#### (4) Có nhận diện chuyển nội bộ, hoàn tiền và khoản thu không?

| Thành phần | Bằng chứng từ tài liệu/mã nguồn | Mức kết luận cho dữ liệu thực |
|---|---|---|
| Chiều tiền | **T:** có Debit/Credit Amount; paper tách Credit/Debit. **C:** mã nguồn MoneyVis tham chiếu hai cột này. | Có cơ sở phân biệt tiền ra/vào ở mức schema mô tả; chưa kiểm trong workbook. Tiền vào không mặc định là thu nhập. |
| Khoản thu | **T/C:** có loại như BGC, FPI và nhãn Paycheck/Interest/Income; mã phân loại dùng quy tắc. | Nhận diện được một số ứng viên thu; chưa kiểm chất lượng nhãn. FPI cũng có thể là tiền chuyển đến, hoàn tiền hoặc khoản vay, không nhất thiết thu nhập. |
| Chuyển tiền | **T/C:** có TFR, FPO và nhãn transfer/money_transfer_debit/credit. | Có nhận diện **chuyển tiền**, nhưng chưa có liên kết chủ sở hữu tài khoản đối ứng để phân biệt chắc **chuyển nội bộ của cùng người**. Không loại mọi FPO như chuyển nội bộ: tiền chuyển ra cũng có thể thanh toán một khoản chi. |
| Hoàn tiền | **C:** code có quy tắc `online_shoping_refund` cho một số dòng DEB có tiền ghi có và mô tả bắt đầu bằng `ama`. | Có heuristic cho **một số** hoàn tiền; chưa thấy bằng chứng cờ refund đầy đủ hoặc khóa nối hoàn tiền–giao dịch gốc trong XLSX. Không coi toàn bộ credit là refund hoặc toàn bộ refund đã nhận diện. |
| Rút tiền/đầu tư/tiết kiệm | **T/C:** có nhóm cash, savings, investment và loại rút ATM. | Cần quyết định mục tiêu riêng; rút ATM là đổi hình thức giữ tiền, không cho biết tiền mặt được chi khi nào. |

Nguồn code đã đọc: [dataCategory.py tại commit `9fdd14e397ea309f0f52c5ff9d0a99c7ab4ff124`](https://github.com/thevisgroup/MoneyVis/blob/9fdd14e397ea309f0f52c5ff9d0a99c7ab4ff124/dataCategory.py). **Chỉ đọc, không chạy**. Đây là code của bản MoneyVis, không phải chứng minh các nhãn tương ứng có sẵn hoặc chính xác trong workbook Mendeley. Lệnh `fillna(0)` của code cho cột debit/credit cũng không phải bằng chứng ngày trống là ngày không chi.

#### (5) Đủ cho mục tiêu dự báo nào và kiểm tra thời gian ra sao?

**Đ:** lịch sử nhiều năm mà tác giả mô tả đủ hấp dẫn để kiểm toán cho một nghiên cứu trường hợp dự báo **một tháng kế tiếp**. Chưa thể khẳng định đủ dữ liệu sử dụng chỉ từ con số “hơn 6.500 giao dịch”: số điểm huấn luyện sau tổng hợp là **số tháng hợp lệ**, không phải số giao dịch.

Mục tiêu nên chốt theo hai mức, sau khi kiểm tệp:

1. **Mức có định nghĩa đơn giản:** tổng Debit Amount quan sát theo tháng hạch toán của chuỗi. Giữ tên “tổng ghi nợ quan sát”; tổng này có thể chứa chuyển khoản/ATM/đầu tư, nên chưa phải chi tiêu tiêu dùng.
2. **Mức đúng gần hơn với khóa luận:** tổng khoản chi qua nguồn tài khoản đã chọn theo một bảng quy tắc nghiệp vụ được kiểm, loại các khoản không phải chi tiêu; báo riêng khoản hoàn tiền đã nhận diện. Nếu dùng chi ròng, hoàn tiền được ghi theo tháng hạch toán thực nhận, không tự hồi tố về tháng mua khi chưa có khóa nối. Các khoản chưa phân biệt giữ trạng thái chưa xác định, không gán nhãn chắc chắn.

Ở cả hai mức, không suy ra chi bằng tiền mặt hoặc từ tài khoản khác. Giữ đơn vị tiền gốc; mã tiền tệ chính xác của workbook còn cần xác minh, **không tự gán GBP chỉ vì ngân hàng UK**, không đổi sang VND để gọi là dữ liệu Việt Nam. Không chọn dự báo chi theo ngày trong giai đoạn đầu vì lệch ngày hạch toán đã được tài liệu nêu rõ.

### 9.5. Kế hoạch kiểm tra theo thời gian — chưa thực hiện

Các bước dưới đây là thiết kế cho giai đoạn sau, không phải kết quả thí nghiệm:

1. **Kiểm toán tệp trước:** tải bản DOI V1 khi chuyển sang bước xử lý dữ liệu; kiểm SHA-256 so với metadata, đọc đúng sheet, xác minh schema, tiền tệ, số chuỗi và nhãn. Tính min/max ngày, số tháng và các tháng trống của từng chuỗi; không suy số tháng từ tên tệp hoặc ngày công bố.
2. **Kiểm tra quan sát:** xác định tháng đầu/cuối có đầy đủ không; rà khoảng thiếu và giao dịch trùng. Không ép mọi tháng nằm giữa min/max thành tháng đầy đủ. Nếu không có bằng chứng độ phủ, ghi rõ giả định chỉ dự báo các khoản được ghi nhận trong bản lưu; không tuyên bố tổng chi thật. Nếu khoảng thiếu khiến không tạo được chuỗi tháng có ý nghĩa, dừng bài toán chuỗi liên tục thay vì nội suy để làm đẹp kết quả.
3. **Chốt mục tiêu trước khi chia:** quy tắc debit/credit, chuyển tiền, ATM và refund phải được lưu phiên bản, kiểm thủ công ở mức cần thiết; nhãn còn mơ hồ phải được báo. Tránh dùng số dư cuối tháng cần dự báo hoặc tổng thực tế tháng tương lai làm đặc trưng.
4. **Chia theo thời gian:** dùng một đoạn tháng lịch liên tục đã qua kiểm tra độ phủ; không xóa tháng thiếu rồi nối hai đoạn như các tháng liền nhau. Nếu đoạn đó có ít nhất 60 tháng hợp lệ, một phương án thiết kế là giữ 12 tháng cuối làm test, 12 tháng ngay trước làm validation, các tháng còn lại làm train (ít nhất 36 tháng). Đây là lựa chọn thiết kế, **không khẳng định workbook đã có 60 tháng hợp lệ**. Nếu ngắn hơn, phải điều chỉnh và nêu giới hạn; không chia ngẫu nhiên các giao dịch thành train/test.
5. **Dự báo cuốn chiếu một bước:** khi dự báo tháng `m`, chỉ dùng dữ liệu đến hết `m-1`. Chọn siêu tham số bằng validation trước khi mở test; trong test có thể mở rộng lịch sử bằng các tháng đã thật sự quan sát trước từng mốc, theo quy trình đã cố định. Không dùng nhãn hoặc thông tin của tháng tương lai để chuẩn hóa/điền thiếu.
6. **So sánh baseline trước:** tháng vừa qua, trung bình ba tháng gần nhất; thêm cùng tháng năm trước nếu đủ lịch sử. Báo MAE và sai lệch bằng đơn vị tiền gốc, số tháng thực sự đánh giá và lỗi từng tháng. Không dùng MAPE khi tháng bằng 0; không hứa ML sẽ tốt hơn baseline trên chuỗi ngắn.
7. **Giới hạn kết luận:** đây là đánh giá theo thời gian trên một khách hàng, không phải kiểm thử độc lập trên nhiều người. Muốn tuyên bố mô hình dùng chung cần nguồn nhiều người và tập người dùng được giữ riêng bên cạnh kiểm thử thời gian.

### 9.6. Quyết định triển khai sau khảo sát

**Đủ cơ sở để chọn MoneyData Mendeley V1 cho bước kiểm tra dữ liệu tiếp theo**, vì nguồn phát hành, giấy phép dataset và tệp cụ thể đã rõ hơn B3. Không cần yêu cầu tiếng Việt/VND để thực hiện một thí nghiệm phương pháp dự báo trên nguồn này.

**Chưa đủ cơ sở để cam kết huấn luyện hoặc dự báo tổng chi tiêu thật ngay:** vẫn thiếu kiểm nội dung workbook, độ phủ từng tháng, xác định tiền tệ và quy tắc nhận diện đầy đủ chuyển nội bộ/hoàn tiền. Đây là các điều kiện về chất lượng/ý nghĩa mục tiêu, không còn là chỉ một trở ngại ngôn ngữ.

Nếu không giải quyết được các điều kiện đó, có thể báo cáo một thí nghiệm minh bạch về **dự báo tổng ghi nợ được quan sát**; phải nêu đây là mục tiêu hẹp hơn yêu cầu tổng chi tiêu. Phương án B1 vẫn chỉ là mô phỏng. Không thay thế âm thầm bằng dữ liệu doanh số của cửa hàng, không lấy số lượng giao dịch lớn làm bằng chứng đủ lịch sử cá nhân.

### 9.7. Dấu vết kiểm tra và phần chưa xác minh của TASK 05B

- Đã đọc lại tài liệu TASK 05; tìm thêm nguồn quốc tế không giới hạn ngôn ngữ hoặc tiền tệ.
- Đã đọc trang Mendeley, API danh sách tệp, thực hiện HEAD tệp; đọc tài liệu/code MoneyVis về hạch toán và phân loại. Không tải workbook hoặc bản ghi tài chính thật, không xác nhận hash cục bộ của workbook.
- Đã đọc trang CTU Financial và các liên kết nguồn gốc mà CTU cung cấp; chưa xác minh được giấy phép gốc hoặc thống kê theo từng người của Berka. Không dùng số liệu từ dự án thứ ba như số liệu tự đếm.
- Đã đọc trang GeoDS về Salad và điều kiện Secure; chưa xác minh số người, độ dài lịch sử từng người, mask quan sát hoặc quy tắc chuyển nội bộ/refund; không xin quyền truy cập.
- Đã đọc card/API của Zia; không tải tệp lớn, chưa xác minh độ phủ mỗi account. Số dòng trong card là tác giả mô tả, không đếm lại.
- Không cài thư viện, sửa website, đọc/ghi SQLite, sinh dữ liệu hay huấn luyện mô hình. Chỉ nối thêm phần 9 vào tài liệu này.

Các nhãn **T/M/C/Đ** vẫn theo quy ước phần 2. Không có số liệu **D** mới từ giao dịch trong TASK 05B: các xác minh ở trên dựa trên tài liệu nguồn, metadata và mã nguồn, không phải kiểm kê dữ liệu thô.
