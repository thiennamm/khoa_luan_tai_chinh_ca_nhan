# Kịch bản bảo vệ Sổ Thu Chi — 7–10 phút

TASK 21B, **30/10/2026**, dựa trên main `c628a642077ccc26db4c6e1ddc1349b67f4c57e9`. Đây là hướng dẫn chuẩn bị/trình bày, **không phải biên bản đã bảo vệ, khảo sát người dùng hoặc kiểm online**. TASK này không tạo tài khoản, dữ liệu, server hoặc kết quả suy luận mới.

## 1. Chuẩn bị trước buổi trình diễn

- Chủ dự án chọn **bản QA riêng** đã kiểm đúng database, đường dẫn model và cổng trước mọi thao tác. Không dùng SQLite thật hoặc database Render để tập dượt. Theo quy trình đã có trong [user-journey-qa.md](user-journey-qa.md), [hướng dẫn dùng thử](user-trial-guide.md) và [restore-rehearsal.md](restore-rehearsal.md); không chạy nguyên lệnh chứa đường dẫn/cổng cũ nếu chưa xác minh lại đích.
- Người trình diễn tự đăng ký tài khoản thử với mật khẩu riêng trong QA; đăng ký xong phải đăng nhập. Không ghi credential vào slide, tài liệu, URL hoặc ảnh. Có thể chuẩn bị tài khoản QA thứ hai để minh họa tách dữ liệu; không mở tài khoản người dùng đã phục hồi từ backup.
- Qua giao diện, chủ động thêm danh mục mẫu cần dùng: **Lương** và **Giáo dục**. Kiểm ánh xạ hiện có; danh mục không có nhãn phù hợp được để Chưa ánh xạ. Danh mục mẫu chỉ là cấu hình, không chứa giao dịch hoặc tiền.
- Chuẩn bị vài giao dịch **giả, ghi rõ mô phỏng** bằng form/CSV hiện có, theo quy ước [csv-import.md](csv-import.md). Không tạo seeder, sửa ngày hệ thống hoặc dùng dữ liệu thật. Nếu làm mới toàn bộ theo kịch bản dưới thì dùng tài khoản QA trống; nếu đã có dữ liệu phải đối chiếu tổng trước và sau.
- Xác minh hai artifact được cấu hình sẵn theo [vietnamese-classification-integration.md](vietnamese-classification-integration.md) và [ml-evidence-summary.md](ml-evidence-summary.md). Không huấn luyện/refit để chuẩn bị buổi demo. Nếu thiếu model, dùng luồng nhập tay và nói rõ giới hạn.
- Với dự báo, tài khoản mới thiếu lịch sử là tình huống hợp lệ. Dùng **Demo dự báo** có sẵn theo [demo-guide.md](demo-guide.md) để minh họa so sánh baseline/Ridge. Nếu dùng tài khoản QA đã chuẩn bị lịch sử ở task trước, kiểm đó là dữ liệu mô phỏng và coverage được giả định/xác nhận trong QA; không xác nhận thiếu dữ liệu thật để mở tính năng.
- Chuẩn bị sẵn bốn tài liệu TASK 21B và ảnh QA đã lưu được dẫn trong biên bản cũ. Ảnh phải ghi ngày/môi trường, che thông tin riêng tư; không giới thiệu ảnh lịch sử như bằng chứng hệ thống đang chạy hôm nay. Không cần mạng cho CSS/JS/icon hoặc suy luận local khi artifact đã có.

TASK 21B chỉ đọc hồ sơ để viết kịch bản; chưa xác nhận server QA, artifact runtime hoặc tài khoản trình diễn hiện đang sẵn sàng. Trước buổi bảo vệ cần chạy lại các bước chuẩn bị bằng quy trình QA được cho phép, không tự kết nối production.

## 2. Trình tự chính khoảng 9 phút

| Mốc | Thao tác trên bản QA / lời trình bày | Bằng chứng và điều cần tránh |
|---|---|---|
| 0:00–0:45 | Giới thiệu: “Sổ Thu Chi giúp ghi nhận thu–chi, theo dõi kế hoạch và hỗ trợ gợi ý danh mục, ước tính tổng chi đã ghi trong website.” Nói rõ đang dùng dữ liệu giả | Không gọi chênh lệch thu–chi là số dư ngân hàng; website không giữ hộ tiền |
| 0:45–1:30 | Mở sơ đồ [kiến trúc](system-architecture.md): trình duyệt → Django templates/form/service → database; hai Pipeline phân loại riêng; dự báo dùng lịch sử của từng tài khoản | Nêu SQLite local/QA hoặc PostgreSQL tùy profile đã xác minh. Không suy trạng thái online từ sơ đồ |
| 1:30–2:15 | Tại Tổng quan tài khoản QA trống, chỉ trạng thái bắt đầu. Mở Danh mục, chủ động thêm Lương và Giáo dục; giải thích liên kết nhãn mô hình là tùy chọn | Không tự thêm dữ liệu khi mở trang/đăng ký. Không hứa có danh mục mẫu thì mô hình luôn đúng |
| 2:15–3:00 | Thêm khoản Thu nhập giả: **5.000.000 VND**, ngày hôm nay, Lương, mô tả `Lương giả để minh họa`. Kiểm form rồi bấm Lưu | Chỉ sau POST thành công mới có giao dịch. Không dùng mật khẩu, sao kê hay thông tin thật |
| 3:00–4:30 | Mở Thêm giao dịch. Nhập nhanh `Chi: Đóng học phí 45k hôm nay`, bấm **Điền vào biểu mẫu**; chỉ “Đã điền, chưa lưu”. Chọn **VI — Tiếng Việt**, bấm **Gợi ý danh mục**, đọc nhãn và nhắc người dùng kiểm tra | Parser là quy tắc tiền/ngày/loại, ML chỉ gợi ý danh mục. Đây là câu minh họa đã có trong hướng dẫn, không phải mẫu đánh giá độc lập |
| 4:30–5:15 | Chỉ nếu kết quả và danh mục phù hợp: chọn rồi bấm **Áp dụng danh mục đã chọn**, sau đó **Lưu giao dịch**. Nếu gợi ý sai, chưa ánh xạ hoặc Transfer thì xem lại và chọn thủ công; không ép kết quả khớp | Gợi ý không tự ghi đè danh mục hoặc tự lưu. Có thể đổi EN để minh họa lựa chọn chủ động nhưng không cần thử cả hai trong 9 phút; không có tự nhận diện ngôn ngữ |
| 5:15–6:00 | Mở Phản hồi phân loại: phân biệt “bấm Áp dụng” và “danh mục cuối cùng cùng/khác nhãn”. Nếu chưa có phản hồi, giải thích điều kiện hợp lệ thay vì tạo kết quả giả | Feedback chỉ xuất hiện khi lưu thành công với receipt còn hiệu lực và danh mục cuối có ánh xạ so sánh được. Không gọi cùng nhãn là nhãn đúng đã kiểm định |
| 6:00–6:45 | Mở Tổng quan → Báo cáo tháng, giữ tháng vừa nhập. Nếu tài khoản ban đầu trống và chỉ lưu đúng hai khoản: thu **5.000.000 VND**, chi **45.000 VND**, chênh lệch **4.955.000 VND**, 2 giao dịch. Chỉ nút **In / Lưu PDF** nếu còn thời gian | Dùng tổng thực tế trên QA nếu đã sửa/thêm khoản. Báo cáo là dữ liệu hiện có, không phải chứng từ hoặc snapshot bất biến; không cần lưu PDF cá nhân để trình diễn |
| 6:45–8:15 | Mở Dự báo cá nhân. Tài khoản mới phải báo thiếu lịch sử. Chỉ các tháng cần xác nhận; không bấm xác nhận tháng chưa ghi đủ. Mở **Demo dự báo**, đọc nhãn “Dữ liệu mô phỏng — chỉ để minh họa”, rồi bấm nút tính demo | Demo có 48 tháng 01/2022–12/2025, tháng đích cố định **01/2026**, không phải tháng hiện tại. Các tháng giả định đầy đủ. Kết quả chỉ tính khi POST, không thêm lịch sử cá nhân |
| 8:15–9:00 | Chỉ bảng MAE validation và phương pháp được chọn thực tế; nhấn mạnh baseline có thể thắng. Kết thúc bằng giới hạn dữ liệu và hướng nghiên cứu cần dữ liệu độc lập, không hứa độ chính xác thực tế | MAE validation dùng chọn phương pháp, không phải sai số test hay cam kết tương lai. Không lấy điểm MoneyData/EN/VI thay kết quả demo đang chạy |

Nếu chỉ có 7 phút: chuẩn bị danh mục và khoản thu giả từ trước, rút phần báo cáo/in, giữ trọn luồng **gợi ý → chủ động Áp dụng → Lưu → feedback** và giải thích thiếu lịch sử/demo. Nếu có 10 phút: mở form **Tạo giao dịch tương tự**, cho thấy điền trước với ngày hôm nay nhưng **chưa bấm Lưu**, rồi trở về; không lấy ML/receipt của nguồn làm phản hồi mới. Ngân sách, định kỳ, tiết kiệm, CSV và lịch có thể chỉ giới thiệu ngắn qua menu/tài liệu, không cần diễn hết trong thời lượng này.

## 3. Giải thích dự báo đúng theo dữ liệu

1. **Dưới 3 tháng:** thiếu lịch sử liên tiếp đã kết thúc, được xác nhận đầy đủ và kết thúc đúng tháng trước. Không nối qua tháng chưa biết, không tự thay chưa xác nhận bằng 0.
2. **3–35 tháng:** “Ước tính theo trung bình 3 tháng”, không gọi là ML. Nếu có dữ liệu QA loại này thì chỉ minh họa đúng phương pháp này.
3. **Từ 36 tháng:** sáu tháng cuối làm validation cuốn chiếu một bước; so sánh tháng trước, TB 3 tháng, cùng tháng năm trước và StandardScaler + Ridge alpha 0.1/1/10. Chỉ fit quá khứ, chặn dự báo âm về 0, chọn MAE thấp nhất. Hòa ưu tiên baseline theo thứ tự đã khóa. Không cần tạo 36 tháng qua form ngay trong buổi demo.
4. **Tháng đích cá nhân:** tháng hiện tại theo giờ Việt Nam, chỉ dùng lịch sử đến hết tháng trước. Không dùng giao dịch tháng hiện tại làm feature. Sửa lịch sử/hủy coverage làm kết quả cũ không còn được hiển thị như hiện hành; snapshot vẫn ở Lịch sử dự báo.
5. **Đối chiếu thực tế:** tháng đích đã kết thúc, coverage đầy đủ mới có actual; đủ coverage nhưng không có chi mới là 0. Chọn bản đầu tiên hợp lệ được lập trong tháng, một bản/tháng để tính MAE. Tài khoản mới có lịch sử trống là đúng, không tạo lịch sử giả để trình bày.

Nguồn: [forecast_config.py](../finance/forecast_config.py), [forecast_math.py](../finance/forecast_math.py), [forecasting.py](../finance/forecasting.py), [forecast_history.py](../finance/forecast_history.py), [forecast-integration.md](forecast-integration.md), [forecast-history.md](forecast-history.md). Demo dùng cùng `calculate`, dữ liệu độc lập, không làm thay coverage hoặc kết quả cá nhân.

## 4. Câu hỏi dự kiến và trả lời ngắn

| Câu hỏi | Trả lời có căn cứ |
|---|---|
| Vì sao chọn mô hình phân loại này? | Đã khóa hai họ TF-IDF từ + LogisticRegression và TF-IDF char_wb + LinearSVC, mỗi họ chỉ 3 giá trị C. Chọn bằng macro-F1 validation trước test; cả EN/VI chọn char C=10. Với VI, C=10 và C=1 rất gần nhau, không khẳng định lựa chọn này luôn tối ưu. Cấu hình gọn, phù hợp suy luận local; kết luận chất lượng chỉ giới hạn trong thiết kế đã thử. Xem [bảng EN/VI](ml-evidence-summary.md) và protocol được dẫn ở đó |
| Baseline là gì? | Mốc đối chứng đơn giản để xem phương pháp phức tạp có mang lại lợi ích trong cùng phép đánh giá. Phân loại dùng Dummy most_frequent; dự báo dùng tháng trước, TB 3 tháng và cùng tháng năm trước. Website không ép Ridge thắng |
| Vì sao Ridge có thể không được chọn? | Ridge không đảm bảo MAE thấp hơn baseline trên sáu tháng validation; khi hòa cũng ưu tiên baseline. MoneyData là ví dụ cụ thể: Ridge alpha 0.1 được chọn trong các alpha, nhưng MAE test **1.320,6704** thua TB 3 tháng **383,9950** theo đơn vị gốc chưa xác minh. Đây là thí nghiệm thăm dò, không phải số VND của người dùng |
| Dữ liệu tiếng Việt có giới hạn gì? | 662 câu/583 nhóm do dự án biên soạn với AI; split 464/99/99, còn 24 cảnh báo gần giống chưa duyệt độc lập. Có 48 câu mơ hồ riêng, không tính accuracy/F1. Không có tập thật độc lập đại diện người Việt; không dùng điểm test làm xác suất cho một giao dịch |
| Hệ thống ngăn hai tài khoản xem dữ liệu nhau thế nào? | Django auth/session yêu cầu đăng nhập; queryset/chi tiết/service theo request.user, category form chỉ của chủ và đúng loại; POST kiểm CSRF. Receipt gợi ý gắn chủ/đầu vào/model/thời hạn, transaction và ràng buộc chống ghi trùng ở các luồng có receipt. Không nhận user_id để thao tác tài khoản khác. Đây là bảo vệ tầng ứng dụng đã có kiểm thử QA, không tuyên bố mọi raw SQL có RLS hoặc hệ thống an toàn tuyệt đối |
| Bấm Áp dụng có phải nhãn đúng để tự học? | Không. Feedback lưu lựa chọn tại thời điểm lưu, tách cờ Áp dụng khỏi cùng/khác nhãn. Không tự huấn luyện hoặc thêm phản hồi vào train/test. Xem [classification-feedback.md](classification-feedback.md) |
| Có thể kết luận đã được người dùng thực tế đánh giá không? | Chưa có bằng chứng đã tổ chức khảo sát. TASK 21A là kiểm hành trình trên QA với dữ liệu mô phỏng, và mới có [hướng dẫn dùng thử](user-trial-guide.md). Không gọi số kiểm thử tự động hoặc ví dụ AI là phản hồi người dùng thật |

Các số liệu chính xác, hash và vị trí tra cứu nằm trong [ml-evidence-summary.md](ml-evidence-summary.md). Cách gắn receipt/snapshot, vô hiệu hóa kết quả và phân quyền nằm ở [ml-data-flows.md](ml-data-flows.md) và [system-architecture.md](system-architecture.md); không sao chép mã dài vào phần thuyết trình.

## 5. Phương án khi gặp sự cố và giới hạn

- **ML không tải được:** nói chức năng tạm không sẵn sàng; tiếp tục nhập tay. Không đổi artifact/hash, gọi lại liên tục hoặc nói baseline là ML để che lỗi.
- **Thiếu lịch sử:** chỉ trạng thái thiếu dữ liệu rồi dùng demo riêng. Không tự xác nhận coverage thật hoặc dùng MoneyData như lịch sử tài khoản.
- **Mạng/online chậm:** dùng bản QA local đã chuẩn bị và kiểm đúng đích, hoặc ảnh/video QA được ghi rõ thời điểm. Không tạo tài khoản/giao dịch online để chữa cháy, không dùng ảnh cũ như bằng chứng online mới.
- **Request thay đổi dữ liệu bị gián đoạn:** kiểm danh sách/trạng thái trước khi gửi lại, không tự retry POST. Không tuyên bố thao tác thất bại nếu server có thể đã ghi.
- **Không có môi trường chạy sẵn:** trình bày sơ đồ và bằng chứng đã lưu, nói rõ chưa trình diễn runtime tại buổi đó. Không bịa kết quả hoặc sửa đồng hồ/dữ liệu để làm đủ điều kiện.

Đây là kịch bản, chưa được bấm thử lại ở TASK 21B; không xác nhận thiết bị vật lý, trình duyệt khác, trạng thái online hoặc thời lượng thực đo. Trước buổi bảo vệ cần tập dượt trên QA riêng; giữ hồ sơ về phần đã/chưa chạy và không đưa credential, PDF/dữ liệu cá nhân hoặc artifact vào Git.
