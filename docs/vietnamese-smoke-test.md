# TASK 10D — Chạy thử 15 mô tả tiếng Việt

Thời điểm chạy thực tế: **2026-10-21T10:58:48+07:00**. Dùng chế độ **Tiếng Việt — thử nghiệm** (`mode=vi`) qua đúng dịch vụ tích hợp `finance.classification_modes.suggest_label`.

**Đây là ví dụ do AI biên soạn, được người dùng cung cấp lại để thử chức năng; không phải tập kiểm tra độc lập hoặc bằng chứng độ chính xác thực tế.** Các dự đoán của chính 15 câu đã được xem ở lượt chạy trước. Lần này chỉ bổ sung kiểm tra trùng và lưu kết quả; không dùng chúng để chỉnh mô hình, chọn ngưỡng hoặc đánh giá mù.

## Mô hình và cách chạy

- Pipeline TF-IDF `char_wb` (3,5), min_df=1 + LinearSVC C=10 đã chốt TASK 10B; giữ nguyên bản fit train, không refit.
- Artifact: `data/experiments/classification-vietnamese/task10b-vi-v1/models/char_linearsvc_C_10.joblib`.
- SHA-256 đã xác minh: `19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55`. Loader đối chiếu với metadata TASK 10B và artifact-manifest, kiểm hash trước giải tuần tự.
- Chỉ truyền mỗi chuỗi `description` vào hàm suy luận; chuẩn hóa đúng dịch vụ: bỏ một tiền tố đầu `[debit]`/`[credit]` nếu có, NFC, casefold, gộp khoảng trắng, giữ dấu. Không gửi cột danh mục, nhãn mong muốn, STT hoặc thông tin trùng vào mô hình.
- Nhãn mong muốn chỉ dùng đối chiếu sau suy luận, quy đổi theo quy tắc TASK 10A. Không thay danh mục/nhãn của người dùng hoặc dữ liệu v1.
- Chạy bằng Python trong `.venv`, trực tiếp qua dịch vụ chế độ VI, không qua trình duyệt hoặc endpoint lưu. Trong tiến trình thử đã chặn `Pipeline.fit` và thao tác SQL execute/executemany để phát hiện gọi nhầm. Không truy cập dữ liệu giao dịch, không ghi SQLite, không sửa mô hình, không chọn ngưỡng và không dùng adapter DLL.

## Kết quả từng câu

| STT | Mô tả | Nhãn mong muốn (mã chuẩn) | Nhãn dự đoán | Khớp/không khớp | Trùng nguyên văn v1 | Trùng sau chuẩn hóa v1 |
|---|---|---|---|---|---|---|
| 1 | Ăn sáng phở bò + cà phê đá | Restaurants | Restaurants | Khớp | Không | Không |
| 2 | Đi chợ mua thịt, cá, rau củ tuần | Groceries | Groceries | Khớp | Không | Không |
| 3 | Đổ xăng xe máy | Transportation | Transportation | Khớp | Không | Không |
| 4 | Tiền điện tháng 10 | Utilities | Subscription | Không khớp | Không | Không |
| 5 | Mua sữa chua & trái cây WinMart | Groceries | Shopping | Không khớp | Không | Không |
| 6 | GrabBike đi công việc | Transportation | Income | Không khớp | Không | Không |
| 7 | Ăn trưa cơm văn phòng với đồng nghiệp | Restaurants | Restaurants | Khớp | Không | Không |
| 8 | Thanh toán tiền Internet FPT | Utilities | Utilities | Khớp | Không | Không |
| 9 | Mua áo phông Uniqlo | Shopping | Shopping | Khớp | Không | Không |
| 10 | Trà sữa Gong Cha chiều | Restaurants | Restaurants | Khớp | Không | Không |
| 11 | Tiền thuốc cảm & C sủi Panadol | Healthcare | Healthcare | Khớp | Không | Không |
| 12 | Xem phim CGV cuối tuần + Bỏng nước | Entertainment | Entertainment | Khớp | Không | Không |
| 13 | Nạp tiền điện thoại Viettel | Utilities | Shopping | Không khớp | Không | Không |
| 14 | Mua kem chống nắng Tiki | Personal Care | Personal Care | Khớp | Không | Không |
| 15 | Đi cưới bạn cấp 3 | Hiếu hỷ / Quà tặng — ngoài 17 mã nhãn | Utilities | Không phù hợp; không chấm nhãn chuẩn | Không | Không |

Đối chiếu định tính: **10 câu khớp, 4 câu không khớp trong 14 câu có mã nhãn mong muốn**, và 1 câu ngoài bộ nhãn. Không quy đổi thành tỷ lệ chính xác thực tế. Không bỏ bất kỳ câu nào khỏi bảng.

Quy ước đối chiếu cần lưu ý:

- Câu 4/8/13: điện, Internet và điện thoại cơ bản thuộc Utilities; không chuyển sang Subscription chỉ vì thanh toán định kỳ.
- Câu 14: danh mục gốc “Mỹ phẩm / Mua sắm” được đối chiếu Personal Care theo mục đích chăm sóc cá nhân không điều trị, không theo nơi bán Tiki.
- Câu 12: dùng Entertainment cho ý chính xem phim kèm bỏng/nước. Đây là câu gộp nhiều hạng mục; kết quả đối chiếu phụ thuộc quy ước này, chưa có nhãn duyệt độc lập.
- Câu 15: danh mục gốc Hiếu hỷ / Quà tặng không có mã tương ứng trong 17 nhãn, mô tả cũng chưa nêu rõ khoản tiền. Utilities không phù hợp; không ép nhãn chuẩn hoặc suy thành Transfer.

## Kiểm tra trùng với v1

- Đọc toàn bộ **662 mô tả** trong dataset.jsonl, gồm train/validation/test (464/99/99). So nguyên văn bằng chuỗi Unicode giữ nguyên hoa/thường/khoảng trắng; so chuẩn hóa bằng chính `normalize_description` dùng trong suy luận. Bảng giữ mọi câu, nếu trùng ghi ID, split và nhãn của bản ghi v1.
- Dataset SHA-256: `6b7071f9ad2ae25baccb82920c6f7d7956cb29ac25b34b102f846d551156598a`.
- Split-manifest SHA-256: `e8bad655404124cff2a801ec2fa4bc79fdceaf21ecfcc632da982579c4e0c04b`.
- Đã xác minh hash dataset, split và danh sách mơ hồ theo manifest v1 trước khi đối chiếu.
- Số câu có trùng nguyên văn trong 662 mẫu: **0/15**; số câu có trùng sau chuẩn hóa: **0/15** (có thể cùng một câu, không cộng hai số).
- Kiểm tra bổ sung riêng với **48 câu mơ hồ/ngoài phạm vi** ở ambiguous.jsonl (không thuộc train/validation/test): nguyên văn **0/15**, sau chuẩn hóa **0/15**.
- Không thực hiện kiểm tra gần trùng/ngữ nghĩa/merchant/bản không dấu. Không có trùng theo hai phép so trên không chứng minh độc lập: cùng tác giả AI, có thể cùng ý định hoặc mẫu câu với tập train. Không dùng kết quả để tuyên bố khả năng tổng quát hóa.

## Transfer và thao tác người dùng

Trong lần chạy này có **0** dự đoán Transfer. Quy tắc được giữ nguyên: **Transfer luôn cần người dùng xem lại, kể cả khi khớp nhãn mong muốn; không tự ánh xạ hoặc áp dụng vào thu/chi.** Không xem kết quả khớp là quyền bỏ qua bước xem lại. Luồng endpoint TASK 10C vẫn trả trạng thái review cho Transfer; lần này không sửa hoặc gọi endpoint để tạo giao dịch.

## Bảo toàn

Đối chiếu trước/sau: **24 tệp** gồm model, metadata/manifest, các tệp dữ liệu v1, requirements, mã chuẩn hóa/bộ nhãn, cấu hình/script thí nghiệm và SQLite thật giữ nguyên SHA-256. Chỉ tạo tài liệu này; không sửa website hoặc dữ liệu, không cần chạy lại hồi quy website vì mã không đổi. Không commit/push hoặc deploy.
