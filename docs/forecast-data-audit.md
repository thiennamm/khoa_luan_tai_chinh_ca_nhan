# TASK 07A — Kiểm định MoneyData V1 cho dự báo

Ngày thực hiện: **20/10/2026**. Đã đọc mục 9, TASK 05B trong [data-survey.md](data-survey.md) trước khi tải. Báo cáo này bổ sung kết quả kiểm tệp, không sửa hồ sơ khảo sát cũ.

## 1. Kết luận và điều kiện sử dụng

**Đã tải và kiểm định đúng workbook V1, nhưng chưa nên khóa dữ liệu để huấn luyện. Phát hiện cách lưu ngày không nhất quán có ảnh hưởng đến toàn bộ tổng theo tháng; cần xác nhận cách diễn giải ngày. Tiền tệ cũng chưa xác minh được.**

- **6.567 giao dịch**, trong đó **6.122 ghi nợ, 445 ghi có**; hai chiều dùng hai cột số dương riêng. Không có dòng thiếu cả hai số tiền hoặc có đồng thời hai số tiền.
- Không có bản ghi trùng hoàn toàn, kể cả khi bỏ Transaction Number. Có **35 nhóm ứng viên giống ngày/loại/mô tả/số tiền**, gồm 83 dòng; không tự xóa vì các trường khác, trong đó có số dư, không giống hoàn toàn.
- Có **3.751 ngày dạng văn bản DD/MM/YYYY** và **2.816 ngày dạng số Excel**. Đọc nguyên trạng cho 01/2015–12/2022. Giả thuyết đảo tháng/ngày **chỉ ở ô số** cho 27/07/2015–25/07/2022, khớp tốt hơn thứ tự dòng và mô tả lịch sử của nguồn. **Giả thuyết chưa được bên công bố xác nhận; không sửa bản gốc.**
- Nhánh giả thuyết có 85 tháng có bản ghi; bỏ hai tháng biên còn **83 tháng ứng viên**. Không có tháng trống trong khoảng đó, nhưng **không có cờ độ phủ để phân biệt không giao dịch với thiếu ghi nhận**.
- Mục tiêu có thể đề xuất là **tổng ghi nợ được ghi nhận qua nguồn tài khoản theo tháng hạch toán**. Chưa đủ thông tin để gọi là toàn bộ chi tiêu tiêu dùng, loại hết chuyển nội bộ/hoàn tiền hoặc suy ra chi tiền mặt.
- Có thể thiết kế **12 mốc validation + 12 mốc test** một bước theo thời gian, **có điều kiện xác nhận ngày và chấp nhận phạm vi quan sát**. Hiện chưa có mốc được phê duyệt là đánh giá trên tháng có độ phủ đầy đủ. Không chạy baseline hoặc mô hình trong task này.

Mức bằng chứng: **D** = tự kiểm trên workbook có SHA-256 cố định; **T** = tài liệu/nhóm công bố mô tả; **Đ** = nhận định, giả thuyết hoặc đề xuất. Không dùng T thay cho thống kê D.

## 2. Nguồn gốc, ghi công và bảo toàn bản gốc

| Thuộc tính | Kết quả |
|---|---|
| Nguồn | [Bank Transactions Dataset — Mendeley Data, Version 1](https://data.mendeley.com/datasets/dnxtg6n4rv/1) |
| DOI | [10.17632/dnxtg6n4rv.1](https://doi.org/10.17632/dnxtg6n4rv.1) |
| Tác giả/người đóng góp của bản phát hành | **Robert Laramee**, University of Nottingham |
| Ngày công bố, phiên bản | **14/01/2026, V1**; không dùng ngày công bố làm ngày giao dịch cuối |
| Metadata tệp chính thức | [API danh sách tệp V1](https://data.mendeley.com/public-api/datasets/dnxtg6n4rv/files?folder_id=root&version=1) |
| Tên tệp | `laramee26openBankTransactionData.xlsx` |
| File ID | `36b3d359-2491-4282-850f-3f03e00fbfe3` |
| URL tải thực tế | [Workbook chính thức theo file ID](https://data.mendeley.com/public-files/datasets/dnxtg6n4rv/files/36b3d359-2491-4282-850f-3f03e00fbfe3/file_downloaded) |
| Kích thước tự đo | **507.389 byte**, khớp API |
| Thời điểm tải, UTC | `2026-10-20T09:08:36.355297+00:00` |
| Cùng thời điểm tại Việt Nam | `2026-10-20T16:08:36.355297+07:00` |
| SHA-256 tự tính, khớp API và TASK 05B | `716eaf9ad4a3cf60dc9c9c8a20ed9a917c545a1b5f139f40ed91d2104faa3ff7` |
| Giấy phép dataset trên trang V1 | **CC BY 4.0** — [điều kiện sử dụng](https://creativecommons.org/licenses/by/4.0/) |
| Bản gốc cục bộ, bị Git bỏ qua | `data/external/moneydata/v1/laramee26openBankTransactionData.xlsx` |

Trích dẫn bản phát hành: **Laramee, Robert (2026), “Bank Transactions Dataset”, Mendeley Data, V1, doi: 10.17632/dnxtg6n4rv.1.** CC BY 4.0 cho phép chia sẻ/thích nghi với ghi công, liên kết giấy phép và nêu thay đổi, không ngụ ý tác giả bảo chứng. Bản gốc được giữ nguyên byte; thống kê trong báo cáo là kết quả xử lý dẫn xuất, gồm hai giả thuyết ngày và làm tròn số để kiểm định như mô tả dưới đây.

Nhóm tác giả nghiên cứu liên quan: **Elif E. Firat, Dharmateja Vytla, Navya Vasudeva Singh, Zhuoqun Jiang, Robert S. Laramee**, [MoneyVis: Open Bank Transaction Data for Visualization and Beyond (2023)](https://diglib.eg.org/items/e5a24478-3ec5-4e33-bab1-e5b27b06c6bd), [DOI bài báo](https://doi.org/10.2312/evs.20231052). Đây là ghi công nghiên cứu, không thay người đóng góp được nêu trên bản phát hành V1.

**T:** nguồn mô tả giao dịch ngân hàng thật đã ẩn danh của một khách hàng, khoảng bảy năm; không phải bộ tổng hợp. Đây vẫn là xác nhận của nhóm công bố, không phải đối chiếu độc lập sao kê gốc. Không tải bản sao GitHub để thay thế workbook V1, không đồng nhất từng dòng giữa các bản phát hành khác nhau.

Metadata có thể chia sẻ: [forecast-source.json](metadata/forecast-source.json). API gốc được lưu trong thư mục dữ liệu bị bỏ qua. Script chỉ đọc OOXML bằng thư viện chuẩn Python; không mở rồi lưu lại Excel, không import vào SQLite và không thực thi macro/công thức.

## 3. Schema, dòng, định danh và đơn vị tiền

### 3.1. Cấu trúc workbook

| Sheet | Dòng XML, gồm định dạng trống | Dòng có nội dung | Cách sử dụng |
|---|---:|---:|---|
| `Anonymized Original with Catego` | 8.315 | 6.568 | 1 header + **6.567 giao dịch** |
| `Description of Categories` | 6.549 | 42 | Ghi công, giải thích danh mục và mã loại; không cộng vào số giao dịch |

Nhiều dòng XML chỉ có định dạng. Không lấy `max_row` hoặc số dòng của sheet giải thích làm số giao dịch. Sheet giao dịch không có ô công thức hoặc ô lỗi Excel. Ngày dùng hệ Excel 1900 (`date1904=false`).

| Cột | Nội dung/kiểu quan sát | Ô thiếu/rỗng |
|---|---|---:|
| A — Transaction Number | Số nguyên thứ tự bản ghi | 0 |
| B — Transaction Date | 3.751 chuỗi ngày, 2.816 số ngày Excel | 0 |
| C — Transaction Type | Mã loại; một số ô trống | 61 |
| D — Transaction Description | Văn bản; chỉ đọc trong bộ nhớ để kiểm tra | 0 |
| E — Debit Amount | Số dương hoặc ô trống khi là credit | 445 |
| F — Credit Amount | Số dương hoặc ô trống khi là debit | 6.122 |
| G — Balance | Số dư dạng số | 0 |
| H — Category | Nhãn có sẵn của nguồn | 24 |
| I — Location City | Văn bản địa điểm | 672 |
| J — Location Country | Văn bản địa điểm | 686 |

**Transaction Number không phải user_id/account_id.** Có 6.567 số khác nhau, liên tục 1–6.567, tăng theo thứ tự sheet. Không có cột mã người/tài khoản/đối tác ổn định hoặc ID liên kết hoàn tiền với giao dịch gốc. Có thể xem đây là một **chuỗi kỹ thuật** theo phạm vi nguồn; số người “một” là T, số tài khoản thật trong workbook **chưa xác minh**. Đối soát số dư hỗ trợ tính nhất quán của một ledger nhưng không chứng minh số chủ tài khoản hoặc tất cả tài khoản của họ đã có mặt.

Category có 30 nhãn khác nhau không rỗng theo nguyên văn, còn 29 sau bỏ khoảng trắng hai đầu; 5 dòng có khoảng trắng thừa. Chỉ tính chẩn đoán, không sửa nhãn hoặc xuất mô tả/địa điểm cá nhân vào tài liệu.

### 3.2. Tiền tệ và độ chính xác số

**Chưa xác minh mã tiền tệ.** Workbook không có cột currency; các ô Debit/Credit/Balance dùng định dạng số chung (`builtin:0`), không chứa định dạng tiền tệ. Trang phát hành V1 đã kiểm không chỉ rõ mã tiền. Không tự gán GBP vì địa điểm/ngân hàng UK, không đổi sang VND. Mọi số tiền dưới đây dùng **đơn vị số gốc chưa được xác nhận**, không dùng ký hiệu £ hoặc ₫.

Script đọc chuỗi số trong XML bằng **Decimal, không dùng float**. Có phần đuôi độ chính xác số do cách lưu Excel: 527 debit, 22 credit và 787 balance khác giá trị làm tròn hai chữ số; độ điều chỉnh lớn nhất tương ứng **4×10⁻¹⁴, 6×10⁻¹², 2×10⁻¹²**. Tổng hợp kiểm định dùng `quantize(0.01, ROUND_HALF_UP)` trên từng ô, công bố rõ đây là quy tắc số học phục vụ kiểm tra, không phải xác nhận tiền tệ có đơn vị nhỏ nhất 0,01. CSV/XLSX gốc không đổi. JSON giữ cả tổng chuỗi số gốc cho debit/credit và mức điều chỉnh.

| Đại lượng D | Kết quả |
|---|---:|
| Giao dịch chỉ có Debit Amount | 6.122 |
| Giao dịch chỉ có Credit Amount | 445 |
| Cả hai số tiền có giá trị / cả hai trống | 0 / 0 |
| Số tiền debit/credit âm / bằng 0 / không đọc được | 0 / 0 / 0 |
| Tổng ghi nợ quan sát, sau làm tròn từng ô | **511178.92** |
| Tổng ghi có quan sát, sau làm tròn từng ô | **503203.29** |
| Ghi nợ trừ ghi có | **7975.63** — không gọi là chi tiêu hoặc thu nhập ròng |

Ô trống ở chiều không hoạt động là cấu trúc biểu diễn tiền ra/vào, không phải một tháng bị thiếu được điền 0. Quy tắc này chỉ được dùng sau khi xác nhận mỗi dòng đúng một chiều. Không cộng các số dư để tạo một “tổng tiền”; số dư là trạng thái tại thời điểm, không phải dòng tiền cộng dồn.

## 4. Vấn đề ngày: hai cách diễn giải phải giữ riêng

### 4.1. Bằng chứng D và giả thuyết Đ

- Toàn bộ 3.751 chuỗi khớp `DD/MM/YYYY` và đều có phần ngày >12. Không có chuỗi mơ hồ giữa DD/MM và MM/DD; đổi toàn bộ cột sang MM/DD sẽ làm cả 3.751 chuỗi không hợp lệ.
- 2.816 ô còn lại là số serial có định dạng ngày. Ngày lịch đọc nguyên trạng của **tất cả 2.816 ô số đều có day ≤12**. Điều này gợi ý khả năng một bước xử lý trước đó đã hiểu các ngày DD/MM có day ≤12 theo MM/DD. Chưa biết lịch sử chỉnh sửa workbook để xác nhận nguyên nhân.
- Riêng các chuỗi văn bản đã cho min/max **27/07/2015–25/07/2022**. Giả thuyết đảo `month` và `day` của ngày serial làm phạm vi toàn tập khớp hai mốc này. Có 195 ô số day=month không đổi; **2.621 dòng** đổi tháng/ngày theo giả thuyết.
- **T, TASK 05B/bài báo:** nguồn mô tả bắt đầu tháng 07/2015 và có quy tắc ngân hàng đưa ghi nhận cuối tuần sang thứ Hai. Sự phù hợp với mô tả này hỗ trợ giả thuyết, **không thay thế xác nhận của tác giả về workbook V1**.

| Chỉ tiêu D | A — đọc lịch lưu nguyên trạng | B — giả thuyết đảo ngày/tháng chỉ ở ô số |
|---|---:|---:|
| Tên nhánh trong script | `stored_calendar` | `swap_numeric_month_day_hypothesis` |
| Ngày đầu | 2015-01-09 | 2015-07-27 |
| Ngày cuối | 2022-12-07 | 2022-07-25 |
| Ngày không hợp lệ về cú pháp/lịch | 0 | 0 |
| Cặp liền nhau phá thứ tự ngày giảm dần trong sheet | 149 | 0 |
| Bản ghi rơi vào thứ Bảy/Chủ nhật | 817 | 0 |
| Ngày khác nhau có bản ghi | 1.660 | 1.660 |
| Tháng lịch có bản ghi | 96 | 85 |
| Tháng trống giữa min/max | 0 | 0 |
| Khoảng dài nhất không có dòng, số ngày lịch nằm giữa hai ngày có ghi nhận | 27 | 6 |

**Không có ngày sai cú pháp không có nghĩa là ngày đúng ngữ nghĩa.** Cả A và B dùng cùng các giao dịch, không phải hai người/tài khoản. Script chưa chọn B làm bản ngày đã sửa, chưa xuất dữ liệu giao dịch đã chuẩn hóa và không đổi ô trong workbook.

### 4.2. Ảnh hưởng tổng theo tháng

Đã xuất **toàn bộ số giao dịch, số dòng debit/credit và tổng tiền mỗi chiều theo từng tháng** cho cả A (96 tháng) và B (85 tháng):

- [Bảng tháng đầy đủ, chỉ thống kê tổng hợp](metadata/forecast-monthly-summary.md).
- [JSON kiểm định và kế hoạch mốc thời gian](metadata/forecast-audit.json), trường `date_branches.*.monthly`.

**Cả 85 tháng chung giữa hai nhánh đều có tổng ghi nợ khác nhau**. Tổng toàn tập và tổng năm giữ nguyên vì hoán đổi không thay đổi năm, nhưng đỉnh theo tháng thay đổi lớn:

| Nhánh | Tháng có tổng ghi nợ lớn nhất | Tổng ghi nợ quan sát |
|---|---|---:|
| A — lịch lưu nguyên trạng | 2020-06 | 85466.43 |
| B — giả thuyết đảo ô số | 2020-03 | 106341.03 |

Không dùng sự chênh lệch này để chọn cách diễn giải có mô hình đẹp hơn. Phải xác nhận ngày trước khi chốt nhãn mục tiêu theo tháng. Chưa có dự báo hay sai số mô hình.

Đối chiếu tổng theo năm, chung cho cả hai nhánh:

| Năm | Giao dịch | Tổng ghi nợ quan sát | Tổng ghi có quan sát |
|---|---:|---:|---:|
| 2015 | 425 | 18048.73 | 21782.21 |
| 2016 | 793 | 41499.74 | 47975.92 |
| 2017 | 753 | 45947.95 | 47566.85 |
| 2018 | 738 | 47925.33 | 46528.59 |
| 2019 | 998 | 77114.21 | 69385.66 |
| 2020 | 897 | 177976.99 | 169352.70 |
| 2021 | 1180 | 69923.97 | 70635.59 |
| 2022 | 783 | 32742.00 | 29975.77 |
| **Toàn tập** | **6.567** | **511178.92** | **503203.29** |

Năm đầu/cuối của lịch sử không mặc định đầy đủ; tổng năm không sửa được sự mơ hồ của tổng tháng.

## 5. Trùng, số dư và độ phủ

### 5.1. Các mức kiểm tra trùng

- So sánh mọi trường nguyên văn, gồm số thứ tự: **0 nhóm trùng**.
- Bỏ Transaction Number, so sánh 9 trường còn lại: **0 nhóm trùng**.
- Khóa ứng viên `(ngày theo từng nhánh, loại chuẩn hóa hoa/thường, mô tả chuẩn hóa khoảng trắng/hoa thường, debit, credit)`, bỏ số dư và nhãn/địa điểm: **35 nhóm, 83 dòng, 48 dòng dư** ở cả hai nhánh. Đây là ứng viên xem lại, không phải 48 lỗi đã được xác nhận. Mua nhiều lần, thanh toán định kỳ hoặc giao dịch cùng giá trị có thể có cùng khóa này. Không tự gộp/xóa và không xuất văn bản vào tài liệu.

Đối soát theo **thứ tự sheet, không sắp lại ngày**: với dòng mới hơn `i` và dòng cũ hơn `i+1`, kiểm `Balance[i] = Balance[i+1] - Debit[i] + Credit[i]`, theo Decimal hai chữ số. **6.566/6.566 cặp khớp, sai lệch lớn nhất 0.00.** Điều này hỗ trợ tính nhất quán tiền tệ/thứ tự ghi sổ trong bản lưu. Không chứng minh độ phủ ngoài bản lưu, mọi tài khoản đều có mặt hoặc không có cặp giao dịch thiếu bù trừ nhau.

### 5.2. Tháng biên, tháng trống và khoảng nghi thiếu

**Theo B, nếu được xác nhận:**

| Tháng biên | Cửa sổ ngày nằm trong khoảng min/max | Giao dịch | Tổng ghi nợ | Tổng ghi có | Xử lý đề xuất |
|---|---|---:|---:|---:|---|
| 2015-07 | 27–31/07 | 16 | 1485.87 | 3545.99 | Bỏ khỏi mục tiêu tháng đầy đủ; không ngoại suy thành cả tháng |
| 2022-07 | 01–25/07 | 79 | 3652.90 | 1150.96 | Bỏ khỏi mục tiêu tháng đầy đủ; chưa có bằng chứng 26–31/07 bằng 0 |

Hai tháng này có nguy cơ cắt biên. Phạm vi min/max chỉ là phạm vi bản lưu, không phải ngày mở/đóng tài khoản đã xác minh. **83 tháng giữa 08/2015–06/2022 có bản ghi ở từng tháng**, nhưng chưa được xác nhận độ phủ đầy đủ. Trong B, không có khoảng giữa hai ngày ghi nhận dài từ 7 ngày trống lịch trở lên; dài nhất 6 ngày. Ngưỡng 7 ngày chỉ là cờ kiểm tra, không là chứng nhận đầy đủ hay không có thiếu dữ liệu.

**Theo A:** biên là 01/2015 và 12/2022, các tháng có ít ngày ghi nhận và các khoảng dài đến 27 ngày không có dòng. Có **19 khoảng từ 7 ngày lịch trống trở lên**, tập trung đầu/cuối phạm vi; chi tiết nằm trong JSON. Chúng có thể chủ yếu phát sinh từ cách diễn giải ngày sai, không được công bố như 19 đợt mất dữ liệu đã xác nhận.

Nguồn không có observation mask, lịch đối soát hoàn chỉnh, ngày hiệu lực sao kê hoặc cờ “tháng đủ dữ liệu”. Không phân biệt chắc được **ngày không phát sinh**, **ngày hạch toán bị dồn**, **ngày thiếu bản ghi**. Script chỉ tạo lịch để chỉ ra tháng không có dòng và giữ `null`/“chưa biết” nếu gặp; **không tự điền tháng thiếu thành 0, không nội suy, không nối hai đoạn bỏ qua tháng lịch thiếu**. Trong tệp này hai nhánh đều không có tháng trống nội bộ; đó là thống kê D, không phải bằng chứng độ phủ.

## 6. Chuyển nội bộ, hoàn tiền, tiền mặt và thanh toán thẻ

Chỉ dùng cột loại, nhãn có sẵn và bảng giải thích của nguồn để nêu bằng chứng. Dấu/chiều tiền chỉ cho biết cột nào hoạt động, không xác nhận mục đích kinh tế. Không gán nhãn mới hoặc tự loại giao dịch khỏi tổng trong task này.

| Vấn đề | Bằng chứng D từ workbook | Kết luận/giới hạn |
|---|---|---|
| Chuyển tiền | Mã TFR: **44 dòng**, 7 debit/37 credit; bảng giải thích gọi TFR là Transfer. Có 1 dòng mang nhãn Account transfer. | Có ứng viên chuyển tiền; **không có chủ tài khoản đối ứng hoặc liên kết hai vế để xác nhận chuyển nội bộ cùng người**. Không coi mọi FPO/BP là chuyển nội bộ, không loại tự động. |
| Tiết kiệm/đầu tư | Nhãn Savings **1.249 dòng**, Investment **151 dòng**, đều debit trong tệp. | Chứng minh tổng debit có các nhóm được nguồn gọi là tiết kiệm/đầu tư. Chưa chứng minh quyền sở hữu đích đến hoặc bản chất từng khoản; không gọi tổng debit là chi tiêu tiêu dùng. |
| Hoàn tiền | Bảng giải thích nói Supplementary Income bao gồm cả tiền nhận từ người khác và refund. Nhãn này có **305 dòng**, 290 credit và **15 debit**. DEB có **36 credit**. | Nhãn gộp, không có cờ refund đầy đủ/khóa nối giao dịch gốc. Không gọi toàn bộ 290 credit hoặc 36 DEB-credit là hoàn tiền. Cũng không coi mọi credit là thu nhập. |
| Nhãn return/reimbursement | Có **3 dòng** thuộc các nhãn mang nghĩa return/reimbursement; 2 debit/1 credit. | Nhãn và chiều tiền không đủ thống nhất để tự xây mục tiêu chi ròng; cần kiểm nguồn/nhãn. Không trích mô tả hoặc số tiền của nhóm nhỏ. |
| Rút tiền mặt | Category Cash: **453 dòng debit**; bảng giải thích nói nhóm này là rút tại máy tiền mặt. Mã CPT có **448 dòng debit**, giao với Cash **441 dòng**. | Có nhãn nguồn cho rút tiền, nhưng không đồng nhất hai tập. Bảng mã dùng `C/P`, trong khi dữ liệu dùng `CPT`; không coi tên mã là khớp nguyên văn. Rút tiền không cho biết lúc nào tiền mặt được chi. |
| Thanh toán bằng thẻ | Mã DEB: **3.268 dòng**, 3.232 debit/36 credit; bảng nguồn mô tả DEB là thanh toán Debit Card. | Hỗ trợ nhận diện loại thanh toán theo nguồn, **không phải cờ trả dư nợ thẻ tín dụng**. Không mặc định tất cả là mua hàng tiêu dùng. |
| Trả dư nợ thẻ tín dụng | Không có cột riêng hoặc liên kết hóa đơn thẻ. Phép tìm từ khóa định trước tìm được **1 dòng ứng viên**, chưa xác nhận. | Không đủ để loại hết thanh toán thẻ hay ngăn tính hai lần nếu sau này ghép thêm sao kê thẻ. Không đưa từ ngữ/mô tả khớp vào tài liệu. |

Các mã còn lại được thống kê đủ theo chiều tiền trong JSON: BP, BGC, CHQ, DD, DEP, FEE, FPI, FPO, PAY, SO và nhóm trống. Có BP/SO/CHQ xuất hiện với credit, vì vậy tên mã cũng không thay thế cột số tiền.

Script có hai phép dò từ khóa trong bộ nhớ: refund/reversal/reimbursement và một danh sách từ liên quan thẻ. Kết quả lần lượt **0 và 1 dòng**. Không tìm thấy từ khóa **không chứng minh không có hoàn tiền/trả thẻ**, đặc biệt dữ liệu đã ẩn danh; khớp cũng chưa chứng minh bản chất khoản tiền. Regex cụ thể nằm trong script; không được dùng các cờ này như nhãn thật. Tổng tiền của nhóm cờ có 1–4 dòng được ẩn trong metadata chia sẻ. Các cờ có thể giao nhau, không cộng số nhóm để tạo tổng giao dịch.

## 7. Định nghĩa mục tiêu dự báo phù hợp

**Đề xuất có điều kiện:**

`Y_m = tổng Debit Amount quan sát trong tháng lịch m theo ngày hạch toán đã được xác nhận, trong phạm vi workbook V1.`

Đơn vị: đơn vị tiền gốc sau khi xác nhận; khoảng dự báo: **một tháng tiếp theo**. Tên trong khóa luận/thí nghiệm phải là **“tổng ghi nợ quan sát qua nguồn tài khoản”**, không rút gọn thành “tổng chi tiêu tiêu dùng”. Dữ liệu không cung cấp ngày giờ mua thực tế hay toàn bộ tiền mặt/tài khoản khác.

Giữ nguyên mọi loại debit ở định nghĩa đầu tiên; công bố rõ có thể chứa chuyển tiền, đầu tư, tiết kiệm, rút tiền mặt và trả thẻ. Không lấy credit trừ debit để tạo “chi ròng” khi chưa nhận diện hoàn tiền. Nếu muốn mục tiêu chi tiêu gần chủ đề khóa luận hơn, cần thêm bảng quyết định nghiệp vụ được kiểm, xác nhận quyền sở hữu đối ứng, cờ hoàn tiền và phạm vi tài khoản; hiện chưa đủ bằng chứng để đưa ra mục tiêu đó một cách đáng tin cậy.

Các đỉnh lớn theo tháng có thể chi phối sai số và do nhiều loại luồng tiền. Không tự cắt đỉnh như ngoại lệ sai dữ liệu hoặc loại khoản chỉ vì số tiền lớn; việc thay đổi định nghĩa mục tiêu phải được ghi phiên bản trước đánh giá.

## 8. Chia theo thời gian, đối chứng và số mốc

### 8.1. Phương án dự kiến nếu B được xác nhận

Sau bỏ hai tháng biên, đoạn tháng có bản ghi là **08/2015–06/2022, 83 tháng lịch liên tiếp**. Chưa gọi đây là 83 tháng quan sát đầy đủ. Nếu chấp nhận nghiên cứu tổng ghi nợ **trong bản lưu** và công bố giả định độ phủ, có thể khóa thiết kế:

| Phần | Tháng lịch | Số tháng | Vai trò |
|---|---|---:|---|
| Train ban đầu | 08/2015–06/2020 | **59** | Lịch sử trước validation |
| Validation | 07/2020–06/2021 | **12** | 12 mốc dự báo một bước; chọn quy trình/tham số |
| Test khóa riêng | 07/2021–06/2022 | **12** | 12 mốc dự báo một bước sau khi chốt quy trình |

Khi dự báo tháng `m`, chỉ dùng thông tin đến hết `m−1`. Có thể mở rộng lịch sử sau mỗi tháng đã thật sự quan sát; trong test không được chọn lại tham số dựa trên lỗi test. Không dùng Balance của tháng đích, tổng credit/debit tháng đích hoặc bất kỳ thông tin tương lai làm đặc trưng. Các bước học/chuẩn hóa sau này chỉ fit trên quá khứ tại từng mốc, không phải toàn bộ 83 tháng.

**Số mốc tính được từ tệp:**

- Thiết kế trên: **24 mốc có điều kiện**, trong đó **12 validation + 12 test**. Đủ lịch sử cho cả lag 1, trung bình 3 tháng và lag 12 tại mọi mốc.
- Nếu quy định tối thiểu 36 tháng ban đầu, toàn đoạn 83 tháng cho tối đa **83−36 = 47 mốc một bước**, từ 08/2018 đến 06/2022. Đây là số mốc tiềm năng, không phải 47 người hoặc 47 test độc lập. Không cộng thêm 24 để thành 71; hai cách đếm giao nhau.
- **0 mốc hiện được xác nhận đủ điều kiện dữ liệu đầy đủ/ngày đúng để khẳng định sẵn sàng huấn luyện.** Chưa có xác nhận sửa ngày hoặc mask độ phủ. Có thể nghiên cứu phạm vi bản lưu với giả định được công bố ở task tiếp theo; không gọi đó là dự báo toàn bộ chi thực.
- Nhánh A tạo được nhiều tháng/mốc hơn về số học, nhưng lịch chưa đáng tin; **không chọn A để tăng số điểm kiểm tra**. JSON lưu cả kế hoạch thăm dò A để truy vết, không phải khuyến nghị sử dụng.

Nếu sau xác minh xuất hiện tháng thiếu, giữ giá trị chưa biết và chia theo các đoạn tháng liên tiếp thực sự đủ điều kiện; đếm lại số mốc có đủ toàn bộ cửa sổ lịch sử. Không bỏ tháng thiếu rồi nối các tháng còn lại hoặc lấy dự báo điền thành nhãn thật. Mục tiêu tháng có bản ghi và mục tiêu tháng đủ quan sát là hai giả định khác nhau.

### 8.2. Baseline đề xuất, chưa chạy

1. **Tháng liền trước:** `ŷ_m = Y_(m−1)`.
2. **Trung bình 3 tháng liền trước:** chỉ dùng ba tháng có quan sát hợp lệ; thiếu một tháng thì không tự lấp 0 hoặc đổi thành “ba tháng có dữ liệu gần nhất” cách xa nhau.
3. **Cùng tháng năm trước:** `ŷ_m = Y_(m−12)`; giữ đúng tháng lịch, kiểm tra tháng đó đủ điều kiện.

Đánh giá trên **cùng các tháng đích đủ điều kiện**, báo MAE, trung bình sai lệch có dấu `dự báo−thực tế`, sai số tuyệt đối từng tháng và số mốc thật sự dùng, bằng đơn vị gốc đã xác nhận. Có thể thêm trung vị sai số tuyệt đối để thấy ảnh hưởng đỉnh lớn. Không dùng MAPE như chỉ tiêu mặc định nếu tháng có thể bằng 0. Không có con số sai số hoặc cam kết ML tốt hơn baseline trong task này.

Đây là một nghiên cứu trường hợp theo thời gian, chưa có bằng chứng tổng quát hóa sang người khác, người Việt hoặc tài khoản khác. Dữ liệu nhiều năm vẫn chỉ tạo vài chục nhãn tháng; số giao dịch 6.567 không phải số mẫu độc lập để dự báo tháng.

## 9. Script và cách chạy lại bằng PowerShell

Script chính [audit_forecast_data.py](../scripts/audit_forecast_data.py) chỉ dùng thư viện chuẩn Python. Không cài thêm gói, không đổi requirements hoặc `.venv`. Đọc XLSX bằng ZIP/XML, dùng giá trị lưu sẵn; có kiểm ô lỗi/công thức, không thực thi chúng. Tệp bản gốc được kiểm SHA-256 trước mỗi lần đọc, từ chối nếu khác nguồn đã khóa. Download đối chiếu metadata V1, file ID, kích thước và mã băm TASK 05B; không ghi đè tệp khác byte.

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'

# Lần đầu: tải đúng V1 và chạy kiểm định.
.\.venv\Scripts\python.exe -X utf8 scripts\audit_forecast_data.py --download

# Chạy lại ngoại tuyến trên bản gốc đã có.
.\.venv\Scripts\python.exe -X utf8 scripts\audit_forecast_data.py

# Chỉ xem schema/kiểu ô/định dạng, không in bản ghi giao dịch.
.\.venv\Scripts\python.exe -X utf8 scripts\audit_forecast_data.py --inspect-schema

# Kiểm thử logic, không truy cập dữ liệu cá nhân/network/website.
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s scripts -p 'test_audit_forecast_data.py' -v

git check-ignore -v -- 'data/external/moneydata/v1/laramee26openBankTransactionData.xlsx'
git status --short --untracked-files=all
```

`--download --download-only` chỉ thu nhận nguồn. Lần tải lại giữ thời điểm thu nhận ban đầu trong metadata. Không có cờ tự sửa ngày/điền thiếu hoặc xuất mô tả giao dịch. Số hiệu dòng dùng trong chẩn đoán cục bộ là số hàng Excel, không phải định danh người.

| Tệp | Chính sách |
|---|---|
| `docs/forecast-data-audit.md` | Báo cáo tổng hợp này |
| `docs/metadata/forecast-source.json` | Nguồn, ghi công, version, giấy phép, timestamp và SHA-256 |
| `docs/metadata/forecast-audit.json` | Thống kê/định nghĩa và các tháng của cả hai nhánh, không có mô tả hay địa điểm cá nhân |
| `docs/metadata/forecast-monthly-summary.md` | Phụ lục bảng tháng đầy đủ, chỉ số đếm/tổng tiền |
| `scripts/audit_forecast_data.py`, `scripts/test_audit_forecast_data.py` | Mã kiểm định/kiểm thử có thể chia sẻ |
| `data/external/moneydata/v1/` | Workbook và API gốc, bị bỏ qua bởi `.gitignore` |
| `data/external/moneydata/v1/audit/row-diagnostics.json` | Chỉ số hàng ứng viên trùng/cờ chứng cứ/lỗi ngày, chỉ lưu cục bộ ngoài Git; không chép vào tài liệu |

Không thay `.gitignore`: `data/` và `*.xlsx` đã đủ. Giữ các tệp TASK 06A đang có trong workspace. Không commit/push bản ghi hoặc tệp nào trong task này; không sửa mã website, SQLite, bí mật cấu hình hoặc môi trường hiện có.

## 10. Kiểm tra thực thi và việc còn thiếu

- Tải thành công V1 từ Mendeley; kích thước và SHA-256 tự tính khớp API/khảo sát. Bản gốc vẫn giữ nguyên byte sau khi phân tích.
- Đã chạy kiểm định toàn bộ dữ liệu, tạo phụ lục tháng cho cả hai nhánh; các dòng trống do định dạng không bị tính như giao dịch.
- **10/10 kiểm thử logic đạt**, gồm lịch Excel 1900/1904, ngày không hợp lệ, nhánh đảo ngày phải bật rõ, Decimal, trùng và kế hoạch thời gian không nối qua tháng thiếu.
- Đối chiếu độc lập bằng **openpyxl chỉ đọc** trong runtime có sẵn của công cụ, không cài vào `.venv`: khớp **6.567 dòng và toàn bộ số đếm/tổng tiền của 96 tháng theo lịch lưu nguyên trạng**. SHA-256 workbook không thay đổi. Script chính không phụ thuộc openpyxl.
- **Chạy lại ngoại tuyến cho kết quả giống từng byte ở 5 tệp**: metadata nguồn, JSON kiểm định, bảng tháng, chẩn đoán hàng cục bộ và snapshot API. Hash script khớp metadata; SHA-256 bản gốc không đổi. Tổng số dòng/debit/credit và tổng tiền của cả hai bảng tháng đối chiếu đúng toàn tập; các tháng vẫn mang trạng thái độ phủ `unknown`.
- **Rà Git đạt:** mọi tệp MoneyData gốc/chẩn đoán hàng đều bị bỏ qua; không có tệp trong `data/` đã được theo dõi. Có 6 tệp mới phục vụ TASK 07A, cùng 5 tệp TASK 06A được giữ lại. Không đổi requirements, `.gitignore`, khảo sát cũ hoặc mã website; không commit/push. Các kiểm tra này không thay thế xác nhận ngày/tiền tệ/độ phủ từ nguồn.

**Bước tiếp theo cần giải quyết:** xác nhận cách lưu ngày V1 và đơn vị tiền từ bên phát hành hoặc tài liệu nguồn rõ ràng; ghi phiên bản quyết định xử lý, xác định phạm vi quan sát được chấp nhận, rồi mới khóa lịch 59/12/12 và chạy đối chứng ở task riêng. Nếu không xác nhận được, báo cáo phải giữ hai diễn giải/giới hạn và chưa công bố kết quả dự báo tháng như đã dùng ngày chuẩn. Không có yêu cầu huấn luyện hoặc liên hệ tác giả trong task hiện tại.
