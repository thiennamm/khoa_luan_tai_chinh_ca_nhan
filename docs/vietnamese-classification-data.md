# TASK 10A — Dữ liệu phân loại mô tả tiếng Việt tự biên soạn

Ngày thực hiện: **21/10/2026**. Phiên bản: **`vi-authored-v1`**. Chưa huấn luyện, thay mô hình đang chạy hoặc sửa website.

**Đây là dữ liệu mô phỏng do dự án biên soạn, không phải giao dịch thật hoặc tập kiểm thử độc lập đại diện người dùng Việt Nam.** Nội dung được trợ lý AI tự biên soạn theo yêu cầu dự án, chưa có người gán nhãn thứ hai/chuyên gia duyệt độc lập. Tên `test` chỉ là tên một phần chia của tập mô phỏng này; không làm nó trở thành bộ kiểm chứng thực tế độc lập.

## 1. Căn cứ và phạm vi

Đã đọc `finance/classification_labels.py`, dịch vụ `finance/classification.py`, báo cáo kiểm định, thí nghiệm và tích hợp phân loại 06A/06B/08A. Giữ nguyên **17 mã nhãn**, gồm cả dấu cách trong `Personal Care`. Quy tắc tiếng Việt dưới đây là định nghĩa vận hành của v1, không khẳng định mọi nhãn trong CSV tiếng Anh đã được tác giả định nghĩa giống hệt.

Không đọc CSV tiếng Anh để dịch/tạo câu, không lấy mô tả từ SQLite/tài khoản, không dùng điểm hoặc dự đoán mô hình để gán nhãn hay chia tập. Chỉ đọc nhãn/chuẩn hóa và báo cáo hiện có. Việc hash các artifact cũ cuối bước này chỉ để kiểm tra chúng không thay đổi.

Nguồn của mọi mẫu là nội dung mới do dự án biên soạn với AI. Không có nguồn tải trên mạng hoặc giấy phép bên thứ ba để kế thừa: **không gán MIT của bộ tiếng Anh cho dữ liệu này**; dự án chưa chỉ định giấy phép phân phối riêng trong bước này. Không tuyên bố dữ liệu đã được thu thập hay duyệt bởi người Việt độc lập.

## 2. Vị trí và phiên bản

Tất cả dữ liệu, script dựng/kiểm định, bản chia và metadata nằm tại thư mục đã được `.gitignore` hiện có loại trừ:

```text
D:\KHÓA LUẬN TỐT NGHIỆP\data\vietnamese\classification\vi-authored-v1\
```

Không sửa `.gitignore`, không stage/commit/push dữ liệu hoặc thay `.venv`/requirements. Báo cáo này chỉ dẫn tới tệp cục bộ, không đính kèm toàn bộ mẫu vào docs/Git.

| Tệp | Nội dung |
|---|---|
| `authored-scenarios.txt` | Nguồn 628 dòng tự biên soạn; tiêu đề lớp chỉ là cấu trúc nguồn, không nối vào văn bản đầu vào |
| `manual-variants.json` | 17 cách diễn đạt lại thủ công, mỗi cách có câu cha xác định |
| `editorial-parents.json` | 14 câu trong nguồn được rà và xác định là cùng kịch bản trước, đổi sang trạng thái biến thể, không tính thêm ý định |
| `dataset.jsonl` | 662 mẫu đủ thông tin theo quy tắc v1, nguồn gốc, nhãn, scenario_id/group_id/split |
| `ambiguity-source.json`, `ambiguous.jsonl` | 48 trường hợp mơ hồ/ngoài phạm vi, lý do, nhãn có thể liên quan; `label=null`, `split=excluded` |
| `label-rules.md` | Định nghĩa, ví dụ và ranh giới phiên bản v1 |
| `grouping-families.json` | Các họ kịch bản được gom bảo thủ ngoài quan hệ cha–con |
| `configuration.json`, `build_and_audit.py` | Seed/quy tắc cố định và script chạy lại bằng thư viện chuẩn; không fit mô hình |
| `split-manifest.json` | Thành viên và tập của từng nhóm, tra từ ID mẫu đến nhóm/tập |
| `near-pairs.json`, `review-decisions.json` | Cạnh gần trùng mạnh, ứng viên yếu và quyết định rà 24 cảnh báo yếu xuyên tập |
| `fixed-rule-review.json` | Mẫu rà quy tắc cố định 3 câu gốc/lớp, 51 câu; cùng tác giả AI rà, không phải đánh giá người thứ hai |
| `audit.json` | Thống kê thực tế, kiểm tra thiếu, trùng, nhóm, giao nhau, kiểu biên soạn |
| `manifest.json`, `manifest.sha256`, `split-lock.json` | Hash nguồn/đầu ra, phiên bản và bản khóa không dựa trên điểm mô hình |

Mỗi mẫu có `id`, `version`, `description`, `label`, `scenario_id`, `group_id`, `split`, `variant_of`, `provenance`. Nguồn gốc ghi loại nguồn, thao tác, tác giả AI và tham chiếu dòng/tệp. Câu cha gốc có `variant_of=null`; câu viết lại/không dấu chỉ đến ID cha và giữ cùng scenario_id. Có nhóm lớn hơn scenario_id khi các kịch bản được gom bảo thủ.

`description` là **trường đầu vào duy nhất** dự kiến cho mô hình về sau; `label` là đích. Không dùng id, scenario_id, group_id, split, nguồn gốc, tên hiển thị nhãn hoặc tiêu đề lớp làm đặc trưng. Không tạo sẵn vector/đặc trưng học được trong bước này.

## 3. Quy tắc nhãn

| Mã chuẩn | Định nghĩa và ví dụ tự đặt | Ranh giới chính |
|---|---|---|
| Education | Học, đào tạo, thi/chứng chỉ và vật dụng nêu rõ cho việc học; ví dụ “Đóng học phí học kỳ đại học” | Khóa học gia hạn vẫn Education; sách mua đọc giải trí Entertainment; máy tính làm việc không tự coi là giáo dục |
| Entertainment | Hoạt động giải trí/nội dung mua lẻ; “Mua vé xem phim tối nay” | Gói nội dung/hội viên định kỳ Subscription; ăn uống Restaurants; dịch vụ chuyến nghỉ Travel |
| Fees | Phí ngân hàng/thanh toán, thủ tục hành chính, công chứng, tiền phạt riêng; “Phí rút tiền tại ATM khác ngân hàng” | Không phân loại bằng chữ “phí” đơn lẻ: học phí, viện phí, bảo hiểm có mục đích riêng; thuế không tự gom vào Fees |
| Groceries | Nguyên liệu, thực phẩm dự trữ/tự dùng, thức ăn thú nuôi, hàng tiêu hao vệ sinh nhà; “Mua rau để nấu cơm” | Món pha/chế biến để ăn ngay Restaurants; đồ bền Shopping; vệ sinh cơ thể Personal Care. Siêu thị không quyết định nhãn |
| Healthcare | Khám, điều trị, xét nghiệm, phòng bệnh và vật tư/thiết bị sức khỏe nêu rõ; “Mua kính thuốc theo đơn bác sĩ” | Kính thời trang Shopping; dưỡng da thường Personal Care; “mua thuốc” thiếu công dụng vẫn có thể mơ hồ |
| Income | Khoản nhận có nguồn rõ: lao động, kinh doanh tự làm, cho thuê tài sản, lãi/cổ tức, trợ cấp/học bổng không hoàn trả; “Nhận lương từ công ty” | Không suy từ tiền vào/credit. Vốn tự chuyển Transfer; hoàn tiền/hoàn ứng/thu hồi cọc không tự là thu nhập |
| Insurance | Đóng/mua/gia hạn phí hợp đồng bảo hiểm; “Đóng phí bảo hiểm sức khỏe” | Bảo hiểm du lịch vẫn Insurance; khoản trợ cấp được chi trả nêu rõ có thể Income; bồi hoàn viện phí không tự coi Income hoặc phí bảo hiểm |
| Mortgage | Trả gốc/lãi nêu rõ vay mua/xây/mở rộng/sửa nhà ở; “Trả gốc và lãi vay mua căn hộ” | Trả góp không rõ mục đích chưa đủ; tiền thuê Rent; phí/phạt riêng Fees; bảo hiểm khoản vay Insurance; gộp khác lớp cần tách |
| Personal Care | Vệ sinh/làm đẹp không điều trị, dụng cụ chuyên chăm sóc cơ thể, chăm sóc bé thường ngày; “Tiền cắt tóc” | Điều trị theo chỉ định Healthcare; vệ sinh nhà Groceries; đồ dùng chung khác Shopping |
| Rent | Thuê không gian ở/làm việc/kho dài hạn/thường xuyên; “Trả tiền thuê phòng trọ tháng này” | Khách sạn kỳ nghỉ Travel; gửi xe Transportation; thuê thiết bị điều trị Healthcare; cọc có thể hoàn không gán Rent |
| Restaurants | Món ăn đã nấu, đồ uống pha sẵn và phục vụ bữa ăn; “Đặt pizza giao về ăn tối” | Nguyên liệu để tự nấu Groceries; giao hàng/đặt online không quyết định nhãn; chỉ “đặt đồ ăn” chưa đủ |
| Shopping | Hàng tiêu dùng/đồ bền, quần áo, phụ kiện, trang trí không có mục đích chuyên biệt ưu tiên; “Mua áo khoác đi làm” | Thiết bị y tế rõ Healthcare; máy cạo râu Personal Care; đồ phục vụ vận hành/an toàn phương tiện Transportation; không suy từ nơi bán |
| Subscription | Quyền sử dụng/hội viên gia hạn cho nội dung, công cụ số, lưu trữ, thành viên không thuộc mục đích ưu tiên; “Gia hạn phần mềm văn phòng theo năm” | Lặp lại không đủ: học phí Education, bảo hiểm Insurance, điện/mạng cơ bản Utilities, tiền thuê Rent; game mua lẻ Entertainment |
| Transfer | Điều chuyển tiền vốn/tài sản nêu rõ cùng chủ hoặc đổi nơi giữ tiền, chưa tiêu dùng; “Chuyển giữa hai tài khoản của tôi” | **Luôn cần xem lại, không tự ánh xạ thu/chi**. CK trả quán ăn vẫn Restaurants; không ép P2P thiếu mục đích/hoàn ứng thành Transfer |
| Transportation | Đi lại thường ngày, cước nội đô, vận hành/sửa chữa/an toàn phương tiện; “Tiền xe buýt đi làm” | Di chuyển trong kỳ nghỉ rõ Travel; “tiền xe” chưa biết mua xe hay cước vẫn mơ hồ |
| Travel | Chuyến nghỉ/du lịch nêu rõ, lưu trú ngắn ngày và dịch vụ cấu thành chuyến đi; “Đặt khách sạn cho chuyến du lịch” | Bảo hiểm riêng Insurance, bữa ăn riêng Restaurants; đi làm nội đô Transportation; gói khác lớp cần tách |
| Utilities | Điện, nước, nhiên liệu bếp, viễn thông cơ bản, vệ sinh/vận hành nơi ở; “Thanh toán tiền điện sinh hoạt” | Internet gia đình không thành Subscription chỉ vì định kỳ; công cụ số Subscription; thuê nhà Rent; quỹ/vốn có thể hoàn cần xem lại |

Thứ tự quyết định: đọc đối tượng/bản chất → ưu tiên mục đích rõ → xác định nguồn thu hoặc điều chuyển vốn nếu có → nếu thiếu thông tin, gộp khác lớp hoặc ngoài bộ nhãn thì **loại khỏi tập nhãn đơn**, ghi lý do, không sửa câu để ép nhãn. Hoàn tiền không được suy là thu nhập chỉ vì tiền vào; v1 giữ các trường hợp đảo khoản/hoàn ứng/quyết toán thẻ ở danh sách ngoài phạm vi.

Ví dụ viết tự nhiên có dấu, không dấu, ghi chú ngắn và CK/TT/TK/NH/cty/PK/BHYT. Bản không dấu tự động: chuẩn hóa NFC/casefold/khoảng trắng như dịch vụ, rồi NFD bỏ dấu tổ hợp, đổi đ→d; thao tác và câu cha được ghi lại, không tính là ý định mới. Các chữ viết tắt chỉ đủ phân loại khi vẫn có mục đích, ví dụ “CK học phí”; “tt ck” bị loại.

## 4. Thống kê thực tế

Nguồn có **628 dòng đã biên soạn**. Rà trước khóa xác định **14 dòng là cách diễn đạt lại cùng kịch bản**, chuyển sang biến thể. Thêm **17 viết lại thủ công + 17 bản không dấu** có quan hệ cha rõ ràng. Kết quả: **614 mô tả gốc + 48 biến thể = 662 mẫu**, thuộc **583 nhóm**. Không coi 662 mẫu là 662 ý định độc lập, cũng không coi mọi nhóm là một merchant.

Không ép đủ 40 mô tả gốc/lớp: Mortgage chỉ còn **22 gốc**, Rent/Transfer **30**, Insurance **31**; cần bổ sung kịch bản thật sự mới và rà độc lập nếu muốn mở rộng. Không lấy biến thể để che phần thiếu so với mục tiêu khoảng 40.

| Nhãn | Gốc | Biến thể | Tổng mẫu | Nhóm | Train | Validation | Test |
|---|---:|---:|---:|---:|---:|---:|---:|
| Education | 40 | 2 | 42 | 40 | 30 | 6 | 6 |
| Entertainment | 40 | 2 | 42 | 40 | 29 | 7 | 6 |
| Fees | 36 | 2 | 38 | 36 | 26 | 6 | 6 |
| Groceries | 40 | 2 | 42 | 40 | 30 | 6 | 6 |
| Healthcare | 40 | 2 | 42 | 40 | 30 | 6 | 6 |
| Income | 39 | 3 | 42 | 39 | 30 | 6 | 6 |
| Insurance | 31 | 3 | 34 | 30 | 23 | 4 | 7 |
| Mortgage | 22 | 4 | 26 | 13 | 19 | 3 | 4 |
| Personal Care | 39 | 3 | 42 | 39 | 30 | 6 | 6 |
| Rent | 30 | 4 | 34 | 23 | 22 | 8 | 4 |
| Restaurants | 40 | 2 | 42 | 40 | 30 | 6 | 6 |
| Shopping | 40 | 2 | 42 | 40 | 30 | 6 | 6 |
| Subscription | 36 | 2 | 38 | 36 | 26 | 6 | 6 |
| Transfer | 30 | 4 | 34 | 17 | 23 | 5 | 6 |
| Transportation | 38 | 4 | 42 | 38 | 30 | 6 | 6 |
| Travel | 38 | 4 | 42 | 38 | 30 | 6 | 6 |
| Utilities | 35 | 3 | 38 | 34 | 26 | 6 | 6 |
| **Tổng** | **614** | **48** | **662** | **583** | **464** | **99** | **99** |

Giữ riêng **48 câu mơ hồ/ngoài phạm vi**, không nằm trong bảng hay train/validation/test: thiếu mục đích (“chuyển khoản”, “thanh toán”, “mua đồ”, “tiền vào”), thiếu công dụng (“mua kính”, “mua kem”), ngoài bộ nhãn (thuế, từ thiện, mua cổ phiếu), hoàn tiền/cọc/quyết toán thẻ và câu gộp nhiều mục tiêu. File riêng ghi đầy đủ từng câu, lý do, loại loại trừ và các nhãn có thể liên quan; danh sách ứng viên **không phải nhãn thật**.

Kiểm tra toàn bộ 662 mẫu: mô tả/nhãn/nguồn gốc không thiếu, không mô tả rỗng/quá 500 ký tự, không mã nhãn lạ. Không phát hiện email hoặc dãy số dài từ 9 chữ số theo regex đã khai báo; đây chỉ là kiểm tra mẫu ký tự, không phải kiểm toán PII toàn diện. Nội dung được tự đặt bằng danh từ chung, không lấy danh tính hoặc bản ghi cá nhân thật.

## 5. Nhóm, chia và khóa

Các quan hệ được xác định **trước khi khóa**:

1. Gốc và mọi variant_of cùng scenario_id, cùng nhóm, gồm bản không dấu/viết tắt/viết lại.
2. Các họ kịch bản gần nghĩa được chỉ định trong `grouping-families.json`: ví dụ điều chuyển vốn cùng chủ, trả vay mua nhà, thuê phòng trọ. Thay loại nhà, kỳ đóng hoặc tài khoản phụ không được coi là bằng chứng độc lập.
3. Cùng khóa nguyên văn/NFC-casefold-khoảng trắng/không dấu/khóa chẩn đoán thì nối nhóm.
4. Cặp gần trùng mạnh được nối bằng thành phần liên thông, kể cả chuỗi nối bắc cầu; giữ ID nhóm theo ID nhỏ nhất trong thành phần, không tách nhóm để khớp tỷ lệ.

Khóa chẩn đoán chỉ phục vụ audit: bỏ dấu, đ→d, che dãy số thành `so`, gộp dấu câu, mở rộng CK/TT/TK/NH/ĐH/PK/cty/BHYT/bus/online theo từ điển cố định. **Không đưa khóa này vào website hoặc thay xử lý đầu vào mô hình hiện có.**

So sánh **mọi 218.791 cặp mẫu**: SequenceMatcher trên khóa chẩn đoán (autojunk=False), và Jaccard tập token. Nối mạnh nếu tỷ lệ chuỗi ≥ **0,86**, hoặc Jaccard ≥ **0,78** với ít nhất 3 token chung. Ứng viên yếu được giữ để rà nếu tỷ lệ chuỗi ≥ **0,74** hoặc Jaccard ≥ **0,60**. Cận trên quick_ratio chỉ giúp bỏ phép tính ratio khi không thể vượt ngưỡng; không fit đặc trưng trên cả tập.

Seed **20261021**; chia nguyên nhóm theo thứ tự SHA-256(seed|group_id), chọn tập làm giảm sai lệch bình phương chuẩn hóa giữa số mẫu/nhãn, tổng mẫu và kiểu nguồn gốc so với tỷ lệ 70/15/15; trọng số cân đối kiểu nguồn **0,25**. Phá hòa theo thứ tự train → validation → test. Không dùng accuracy/F1 hoặc dự đoán để quyết định.

Trong giai đoạn biên tập trước khóa có rà lại biến thể, gom họ kịch bản và thêm cân đối kiểu viết để bản không dấu/viết lại không chỉ tập trung train. Đây là điều chỉnh theo đếm và nguồn gốc dữ liệu, **không thử nhiều seed hay chọn bản chia theo điểm mô hình**. Chỉ bản cuối trong split-lock.json là bản đã khóa của v1.

Kết quả cuối: train **464/662 = 70,09%**, validation **99/662 = 14,95%**, test **99/662 = 14,95%**; số nhóm tương ứng **406/87/90**. Có 17 lớp trong cả ba tập. Phân tầng chỉ gần đúng; ví dụ Rent 22/8/4 vì nhóm không thể tách. Mỗi validation/test có 2 bản không dấu tự động, 2 viết lại thủ công và 2 biến thể nhận diện trong rà biên tập; các biến thể không bị tính như ý định mới.

## 6. Trùng và các giới hạn rò rỉ

| Khóa/quan hệ | Kết quả toàn tập | Giao nhau train–validation / train–test / validation–test |
|---|---|---|
| Nguyên văn | 662 khóa; 0 nhóm trùng | **0 / 0 / 0** |
| Chuẩn hóa giống dịch vụ hiện có | 662 khóa; 0 nhóm trùng | **0 / 0 / 0** |
| Không dấu + chuẩn hóa | 645 khóa; 17 nhóm trùng chủ đích, 17 dòng dư | **0 / 0 / 0** |
| Chẩn đoán số/dấu câu/viết tắt | 645 khóa; 17 nhóm trùng | **0 / 0 / 0** |
| group_id, quan hệ cha–con/họ đã khai báo | 583 nhóm; không nhóm bị tách | **0 / 0 / 0** |
| Cạnh gần trùng mạnh | 11 cạnh, 0 cạnh khác nhãn | **0 cạnh xuyên tập** |

Không có nhóm cùng khóa nhưng xung đột nhãn ở các khóa đã kiểm tra. Không tự xóa các bản không dấu: chúng tồn tại có chủ đích cùng nhóm và nguồn gốc rõ.

**Vẫn còn 24 cảnh báo gần giống mức yếu giữa các tập**, không giấu hoặc tuyên bố là 0. Cùng tác giả AI đã rà toàn bộ và ghi quyết định giữ cảnh báo trong `review-decisions.json`. Có cặp khác đối tượng rõ (phí công chứng/chụp cộng hưởng từ, thức ăn mèo/tủ lạnh); có cặp còn chung họ biểu đạt (thuê nơi ở/thuê văn phòng, mua thuốc cho bệnh khác nhau, chuyển tài khoản phụ/tài khoản ngoại tệ). Các cặp sau vẫn cần người khác xem lại trước khi diễn giải điểm thí nghiệm; không khẳng định đã loại mọi rò rỉ mẫu câu/ngữ nghĩa hoặc tách merchant.

Mẫu rà quy tắc cố định: chọn ba câu gốc/lớp có SHA-256(`review-v1|20261021|id`) thấp nhất, tổng **51 câu**; giữ cả ID và quy tắc tham chiếu trong tệp riêng. Cùng tác giả đọc/đối chiếu, **không phải độ đồng thuận gán nhãn độc lập**. Ví dụ biên rõ đã rà: thuê địa điểm phòng khám vẫn Rent; thuốc bổ có đơn điều trị vẫn Healthcare; lãi tiết kiệm riêng là Income; số dư ví của chính mình là Transfer. Không dùng mô hình để “xác nhận” nhãn.

## 7. Hash và khả năng chạy lại

Các SHA-256 đã khóa:

```text
dataset.jsonl
6b7071f9ad2ae25baccb82920c6f7d7956cb29ac25b34b102f846d551156598a

split-manifest.json
e8bad655404124cff2a801ec2fa4bc79fdceaf21ecfcc632da982579c4e0c04b

manifest.json
64988f9e7893a968374b0c2563e5440f1bdef6fa9c6ed6b7985c81bcbfa6a485
```

Manifest ghi hash/số byte nguồn, script, quy tắc, dataset, danh sách mơ hồ, audit và bản chia. split-lock ghi hash các nguồn và đầu ra, thời điểm khóa, chuẩn hóa/bộ nhãn của website được tham chiếu, seed và xác nhận chưa huấn luyện. Không lưu mô hình hoặc dữ liệu tài khoản.

Từ thư mục dự án trong PowerShell:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 data/vietnamese/classification/vi-authored-v1/build_and_audit.py
```

Script chỉ đọc các nguồn biên soạn cục bộ và import hàm chuẩn hóa/bộ nhãn; không khởi tạo Django ORM, tải mô hình, đọc DB, gọi mạng hoặc chạy thí nghiệm tiếng Anh. Sau khóa, script từ chối nguồn/chuẩn hóa/nhãn thay đổi; với nguồn không đổi, dựng lại rồi đối chiếu toàn bộ hash đầu ra đã khóa. Nếu muốn sửa nguồn/quy tắc/nhóm sau này, tạo **phiên bản mới**, không chỉnh lặng v1 hoặc đổi chia theo điểm mô hình.

Đã chạy lại sau khóa: **9 đầu ra đã khóa giữ nguyên byte/hash**; đối chiếu đủ **15 tệp trong manifest**. Kiểm tra cấu trúc riêng xác nhận cha–con/scenario/group không giao tập, bốn loại khóa không giao tập, đủ 17 lớp ở mỗi tập và toàn bộ 48 câu bị loại không có nhãn ép. Bằng chứng ở `verification.json` cục bộ.

SHA-256 bản khóa `split-lock.json`: `9ec1961b0e81109e1cb2e9fdafc87928adc12cba8ecc7d63c6ef3c4a7cb2083d`.

Đối chiếu **208 tệp được bảo vệ** (artifact/dữ liệu/thí nghiệm tiếng Anh, mã website, requirements, `.gitignore` và SQLite thật): giữ nguyên hash. Git không theo dõi tệp nào dưới thư mục dữ liệu mới, staging trống. Thay đổi tài liệu `docs/milestone-review.md` từ TASK 09C được giữ nguyên; báo cáo mới này chưa commit. Không chạy hồi quy website vì không thay mã website, không cài thư viện hoặc tạo mô hình mới.

## 8. Điều còn thiếu trước khi huấn luyện/triển khai

Đây là tập nền mô phỏng nhỏ, nhiều mô tả có mục đích khá rõ và từ vựng cùng tác giả. Chưa có tần suất giao dịch thực, lỗi gõ tự nhiên đại diện, slang vùng miền phong phú, đối soát luồng tiền hoặc tập độc lập từ người dùng có đồng ý. Một số lớp có ít gốc/nhóm và chỉ 3–4 mẫu validation/test; điểm sau này sẽ biến động mạnh.

Cần rà độc lập quy tắc/nhãn, ưu tiên 24 cặp gần nghĩa còn cảnh báo; bổ sung kịch bản mới có ý nghĩa cho Mortgage/Rent/Transfer/Insurance, và xây một tập đánh giá thực tế có đồng ý, tách nguồn/nhóm trước khi tuyên bố dùng tốt tiếng Việt. Việc có tập `test` ở đây không giải quyết giới hạn đó. Chưa chọn mô hình, ghép dữ liệu tiếng Anh/Việt, hiệu chỉnh độ tin cậy hoặc thay artifact C=10 đang chạy.
