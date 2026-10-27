# Sổ Thu Chi — website tài chính cá nhân

Bản chạy trên máy, dùng Python 3.13, Django 5.2, SQLite và Django templates; có gợi ý phân loại thử nghiệm, nhập CSV có xem trước, xác nhận lịch sử tháng và ước tính tổng chi theo từng tài khoản. Chưa triển khai lên Internet.

## Chạy bằng PowerShell

Mở PowerShell tại thư mục dự án. Không cần kích hoạt môi trường ảo hoặc đổi Execution Policy; gọi trực tiếp Python trong `.venv`:

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate
& '.\.venv\Scripts\python.exe' -X utf8 manage.py runserver 127.0.0.1:8001
```

Truy cập <http://127.0.0.1:8001/>. Trong phiên chuẩn bị này, máy chủ đã được mở tại cổng 8001, bạn có thể truy cập ngay. Dừng máy chủ chạy trong PowerShell bằng **Ctrl+C**. Nếu cổng 8001 đang được sử dụng khi tự chạy lại, đổi thành `127.0.0.1:8002` và truy cập cổng tương ứng. Máy chủ chỉ nghe trên máy hiện tại; bố cục hỗ trợ màn hình điện thoại khi thu nhỏ trình duyệt.

Môi trường `.venv` và `requirements.txt` hiện có được giữ nguyên. Nếu cần tạo lại môi trường sau này:

```powershell
py -3.13 -m venv .venv
& '.\.venv\Scripts\python.exe' -X utf8 -m pip install -r requirements.txt
```

## Sử dụng lần đầu

1. Chọn **Đăng ký** và tự đặt tên đăng nhập, mật khẩu. Sau khi tạo tài khoản thành công, website chuyển tới **Đăng nhập**; bạn cần đăng nhập bằng tài khoản vừa tạo để tiếp tục. Đăng ký không tự đăng nhập. Không có tài khoản hoặc mật khẩu mặc định.
2. Mở **Danh mục**, tạo danh mục thu nhập hoặc chi tiêu của riêng bạn.
3. Chọn **Thêm giao dịch**, nhập loại, số tiền, ngày, danh mục và mô tả nếu cần.
4. Mở **Tổng quan** và chọn tháng để xem tổng thu, tổng chi, chênh lệch. Trang **Giao dịch** tìm trong mô tả, lọc theo loại/danh mục và chọn tháng hoặc khoảng ngày; phân trang 20 dòng.
5. Nhấn **Xem** để xem chi tiết, sửa hoặc xác nhận xóa giao dịch. Đăng xuất bằng nút ở đầu trang.

Số tiền là **VND nguyên đồng**, từ `1` đến `999999999999999`. Trường tiền của giao dịch, ngân sách và định kỳ nhận `50000` hoặc `50.000`, hiển thị `50.000` với nhãn **VND** bên cạnh. Dấu chấm chỉ hợp lệ khi phân nhóm đúng ba chữ số; `50.00`, `50,000`, dấu âm/dương, phần lẻ và ký hiệu tiền bị từ chối ở server. Khi JavaScript tắt vẫn nhập và lưu số nguyên được. CSV tiếp tục dùng số nguyên **không dấu phân cách**.

Tiền trên trang được hiển thị thống nhất như `0 VND`, `50.000 VND`, `1.250.000 VND`, `-50.000 VND`; giá trị chưa biết không được đổi thành 0. Biểu đồ có thể dùng đơn vị rút gọn đã ghi rõ. Chi tiết, các tệp thay đổi và bằng chứng QA TASK 17C: [docs/money-formatting.md](docs/money-formatting.md).

Nhập/lưu giao dịch, cộng tổng thu/chi và ước tính trung bình dùng `Decimal`. Tổng được cộng theo từng dòng Decimal để tránh làm tròn khi tổng lớn trên SQLite. Riêng đại số ML của Ridge chuyển tổng tháng sang float64 tại ranh giới mô hình; không dùng float để lưu giao dịch hoặc cộng tổng tài chính. TASK 17C giữ nguyên phép tính và quy tắc làm tròn hiển thị.

Chênh lệch là **tổng thu trừ tổng chi của phạm vi đang xem**, có thể âm: Tổng quan dùng tháng được chọn, danh sách Giao dịch dùng toàn bộ kết quả lọc. Đây không phải số dư tài khoản ngân hàng hay số dư tích lũy của ví. Ngôn ngữ: tiếng Việt; múi giờ: `Asia/Ho_Chi_Minh`.

## Hướng dẫn bắt đầu và danh mục mẫu — TASK 18B

Trên Tổng quan, mở **Bắt đầu với Sổ Thu Chi** để xem: thiết lập danh mục → ghi giao dịch đầu tiên → đặt ngân sách nếu muốn. Khối mặc định thu gọn, không chặn dùng website; hai bước chính dựa trên dữ liệu của chính tài khoản, ngân sách là tùy chọn và không cần xác nhận tháng đầy đủ.

Trong **Danh mục → Thêm danh mục mẫu**, xem loại/phạm vi/ánh xạ và chọn từng mục rồi bấm **Xác nhận thêm mục đã chọn**. Chỉ tạo cấu hình danh mục, không tạo giao dịch/tiền demo khi đăng ký, mở trang hoặc thêm mẫu. Mục đã có theo loại + tên chuẩn hóa được bỏ qua, giữ nguyên tên, ID và ánh xạ. Có thể tự tạo/sửa danh mục theo nhu cầu như trước.

11 mẫu gồm 7 ánh xạ rõ; **Ăn uống, Nhà ở, Hóa đơn, Thu nhập khác** để chưa ánh xạ vì phạm vi rộng. Không có Transfer. Thêm mẫu không bảo đảm mô hình gợi ý đúng; vẫn phải kiểm tra và chủ động Áp dụng/Lưu. Không cần migration mới. Quy tắc chuẩn hóa/khóa đồng thời, PostgreSQL QA, kiểm thử và ảnh: [docs/getting-started.md](docs/getting-started.md).

## Nhập nhanh và gợi ý gọn — TASK 17B

Trong **Thêm giao dịch**, ô **Nhập nhanh** nhận một câu như `Ăn trưa 45k hôm nay`. Bấm **Điền vào biểu mẫu** mới phân tích theo quy tắc; không dùng chatbot/ML để đọc câu và không tự lưu hoặc yêu cầu gợi ý danh mục.

Tiền cần đơn vị rõ: `45k`, `45 nghìn`, `1,5 triệu`, `45000đ` (cũng nhận `₫`, `VND`); ngày nhận `hôm nay`, `hôm qua`, `dd/mm/yyyy`. Thiếu ngày dùng hôm nay theo giờ Việt Nam và ghi rõ trong kết quả. Chỉ tiền tố `Thu:`, `Thu nhập:`, `Chi:`, `Chi tiêu:` mới điền loại; nếu không phải tự chọn. Không đoán danh mục. Tiền được chuyển bằng Decimal thành số nguyên VND trong giới hạn hiện có. Parser nhập nhanh giữ nguyên cách hiểu `1,5 triệu`; sau phân tích, tóm tắt hiện `1.500.000 VND` và trường tiền hiện `1.500.000`. Cú pháp nhập nhanh khác với trường Số tiền: trường này chỉ nhận số nguyên hoặc dấu chấm phân nhóm hợp lệ, không nhận ký hiệu tiền.

Kết quả hiện mô tả sau xử lý và phần cần kiểm tra. Nhiều tiền/ngày, tiền âm/zero/quá lớn hoặc định dạng không hỗ trợ sẽ báo lỗi, giữ nguyên dữ liệu biểu mẫu. Nếu form đã có dữ liệu, phải bấm **Xác nhận thay thế biểu mẫu** hoặc **Giữ dữ liệu hiện tại**. Khi áp dụng nhập nhanh, danh mục được để trống để bạn chọn lại. Cuối cùng vẫn phải kiểm tra và bấm **Lưu giao dịch**. Nhập nhanh chỉ có trên trang Thêm; biểu mẫu thường vẫn dùng được khi JavaScript tắt.

Ô nhập nhanh dùng một dòng. Sau khi điền, tóm tắt gọn tiền–ngày–loại và thông báo **Đã điền, chưa lưu** luôn thấy; lỗi/các trường cần bổ sung không bị giấu. Bảng nhận diện và giải thích đầy đủ mở tại **Xem chi tiết**.

Ngay dưới Mô tả là chọn **VI — Tiếng Việt / EN — Tiếng Anh** và nút **Gợi ý danh mục**; giữ nhãn thử nghiệm, cảnh báo và nút **Áp dụng** riêng. Chi tiết mô hình/phản hồi nằm trong mục mở rộng. Thay mô tả/loại qua nhập nhanh cũng hủy gợi ý cũ; backend vẫn xác minh receipt khi lưu. Xem định dạng, giới hạn, QA, kiểm thử và bàn giao mã tại [docs/quick-transaction-entry.md](docs/quick-transaction-entry.md).

## Lịch sử dự báo — TASK 15C

Từ **Dự báo → Lịch sử dự báo**, xem các phiên bản dự báo cá nhân và đối chiếu với tổng khoản chi đã ghi trong website. Chỉ tháng đã kết thúc theo giờ Việt Nam, được xác nhận ghi chép đầy đủ mới có số thực tế; tháng không có chi chỉ bằng 0 sau xác nhận. Mỗi tháng dùng bản đầu tiên hợp lệ được lập **trong tháng** để tính MAE, các phiên bản sau chỉ xem lịch sử. MAE đối chiếu thực tế tách riêng MAE validation và không phải chỉ số riêng của Ridge.

Snapshot dự báo được giữ khi kết quả hiện hành lỗi thời. Tính lại cùng fingerprint/cấu hình/tháng không tạo bản lịch sử mới; demo không vào lịch sử cá nhân. Kết quả cũ trước chức năng được đánh dấu thiếu bằng chứng đánh giá. Không tự tính khi mở trang.

Migration `0012_forecast_history` đã áp dụng trên SQLite QA và local thật sau backup API, kiểm integrity/khóa ngoại/hash; dữ liệu nghiệp vụ cũ giữ nguyên, không để lại dữ liệu hoặc thời gian QA. Máy khác cần sao lưu rồi migrate theo [docs/forecast-history.md](docs/forecast-history.md). Chưa truy cập production; PostgreSQL mới rà/compile offline, chưa thử database thật.

## Giao dịch định kỳ — TASK 15B

Vào **Giao dịch định kỳ** để tạo khoản thu/chi lặp hàng tháng với số tiền **dự kiến**, danh mục và ngày đến hạn 1–31. Tháng ngắn dùng ngày cuối tháng. Chọn **Ghi nhận**, kiểm tra ngày/tiền/danh mục/mô tả thực tế rồi xác nhận mới tạo giao dịch; **Bỏ qua** không tạo giao dịch. Không có scheduler, gửi email hoặc tự cộng khoản dự kiến vào thống kê/ngân sách/dự báo.

Sửa thông tin quy tắc có hiệu lực từ tháng sau. Tạm dừng các kỳ chưa từng xử lý từ tháng hiện tại; kích hoạt lại từ tháng sau, không tạo bù. Snapshot các kỳ đã xử lý giữ nguyên. Xóa giao dịch liên kết không tự tạo lại; phải xác nhận mở lại kỳ. Trang Tổng quan nhắc các khoản đến hạn/quá hạn trong cửa sổ 12 tháng và sắp đến hạn trong 7 ngày.

TASK 15B đã sao lưu SQLite local bằng backup API, kiểm integrity/hash rồi áp dụng migration `0011`; dữ liệu nghiệp vụ cũ giữ nguyên, không để lại dữ liệu QA. Máy khác cần sao lưu và migrate theo [docs/recurring-transactions.md](docs/recurring-transactions.md), không chạy mã mới với schema cũ. Chưa truy cập database production; tương thích PostgreSQL mới rà/compile offline, chưa thử trên PostgreSQL thật.

## Phản hồi phân loại — TASK 15A

Trong **Thêm/Sửa giao dịch**, yêu cầu gợi ý VI/EN, tùy chọn bấm **Áp dụng**, rồi tự bấm **Lưu giao dịch**. Nếu gợi ý còn hiệu lực và danh mục cuối có ánh xạ nhãn chuẩn, hệ thống ghi nhận nhãn đề xuất và lựa chọn khi lưu. Trang **Phản hồi phân loại** chỉ hiển thị phản hồi của bạn, phân biệt cùng/khác nhãn với việc có bấm Áp dụng. Transfer vẫn cần xem lại và không áp dụng tự động.

**Phản hồi phản ánh lựa chọn của người dùng, không phải nhãn đúng đã được kiểm định.** Không tự huấn luyện, không chuyển phản hồi vào tập nghiên cứu. Không có gợi ý hoặc danh mục chưa ánh xạ vẫn lưu giao dịch thủ công được. Gợi ý hết hạn sau 15 phút; nếu gửi một gợi ý cũ không hợp lệ, yêu cầu gợi ý lại hoặc kiểm tra danh mục rồi bấm Lưu lần nữa để lưu thủ công.

Migration `0010_classificationsuggestion_classificationfeedback` cần được áp dụng **sau khi sao lưu**, trước khi dùng trang phản hồi. Khi bàn giao TASK 15A đã sao lưu, kiểm tra và migrate SQLite local thật; dữ liệu nghiệp vụ cũ giữ nguyên. Không kết nối database production trong bước bàn giao. Cách sao lưu, migrate local/Render, dọn gợi ý hết hạn và kết quả kiểm thử: [docs/classification-feedback.md](docs/classification-feedback.md).

## Tên đăng nhập và mật khẩu — TASK 11D

Vào **Tài khoản** trong menu để xem tên đăng nhập hiện tại. Hai biểu mẫu độc lập cho phép **đổi tên đăng nhập** (tên mới + mật khẩu hiện tại) hoặc **đổi mật khẩu** (mật khẩu hiện tại + mật khẩu mới + xác nhận). Sau đổi tên, lần đăng nhập sau dùng tên mới; ID, quyền và dữ liệu thu chi giữ nguyên. Sau đổi mật khẩu, phiên hiện tại được giữ, các phiên khác mất hiệu lực khi được kiểm tra lại. Không có luồng quên mật khẩu/email trong bước này. Các ô mật khẩu không được điền lại khi có lỗi; không đưa mật khẩu lên URL. Chi tiết và giới hạn kiểm tra trình duyệt: [docs/account-management.md](docs/account-management.md).

## Thống kê theo danh mục và nhiều tháng — TASK 11C

Trang **Tổng quan** có **Cơ cấu chi theo danh mục** của tháng được chọn, biểu đồ thanh ngang và bảng số tiền/tỷ trọng. Chọn **So sánh 6 tháng/12 tháng** để xem thu, chi và chênh lệch từng tháng, kết thúc ở tháng đang xem. Biểu đồ cột và bảng dùng chung số liệu, chạy ngoại tuyến và không cần JavaScript. Trên màn hình nhỏ, kéo ngang riêng vùng biểu đồ để xem các tháng còn lại; bảng chuyển thành từng khối có nhãn.

Tháng hiện tại ghi **Tháng chưa kết thúc**. Tháng không có giao dịch hiện tổng đã ghi là 0 và trạng thái lịch sử riêng; số 0 thống kê không làm tháng đó thành dữ liệu đầy đủ để dự báo. Không có chi thì không hiển thị tỷ trọng giả. Chi tiết: [docs/financial-statistics.md](docs/financial-statistics.md).

## Tìm kiếm, lọc và xuất CSV — TASK 11B/11E

Sau khi **Lọc**, bấm **Xuất CSV** để tải toàn bộ kết quả, kể cả các trang chưa xem. Tệp UTF-8 có BOM dùng đúng năm cột của mẫu nhập CSV. Bộ lọc lỗi không cho tải; không có kết quả thì tệp chỉ có header. Các ô danh mục/mô tả có nguy cơ giống công thức được thêm tab bảo vệ trong bản xuất, nên có thể khác chuỗi gốc và **không bảo đảm nhập lại nguyên văn**. Import không tự bỏ tab này; danh mục đã được bảo vệ có thể không còn khớp tên hiện có. Chưa kiểm chứng bằng Excel thật. Xem [docs/csv-export.md](docs/csv-export.md).

Trong **Giao dịch**, nhập chuỗi mô tả (tối đa 500 ký tự), chọn **Tất cả/Thu nhập/Chi tiêu**, danh mục riêng của bạn và chế độ **Theo tháng** hoặc **Khoảng ngày**, rồi bấm **Lọc**. Tìm bằng chuỗi chứa không phân biệt hoa/thường, kể cả chữ Việt có dấu; vẫn phân biệt có dấu/không dấu. Khoảng ngày bao gồm cả hai ngày biên. Chỉ chế độ đã chọn có hiệu lực; mặc định là tháng hiện tại.

Tổng thu, tổng chi, chênh lệch và số kết quả tính trên **toàn bộ** kết quả lọc, không chỉ 20 dòng đang xem. Chuyển trang giữ các điều kiện; **Xóa bộ lọc** trở về tháng hiện tại. Bộ lọc sai sẽ báo lỗi, chưa hiển thị kết quả hoặc tổng tiền; danh mục không hợp lệ dùng thông báo chung, không tiết lộ tài khoản khác. Tìm kiếm chỉ đọc, không sửa/xóa giao dịch hoặc thay trạng thái lịch sử/dự báo. Chi tiết và kết quả kiểm tra: [docs/transaction-filters.md](docs/transaction-filters.md).

Danh mục phải cùng tài khoản và cùng loại thu/chi với giao dịch. Danh mục đã có giao dịch được đổi tên và nhãn gợi ý; không thể đổi loại hay xóa cho đến khi các giao dịch liên quan được chuyển hoặc xóa. Đổi nhãn gợi ý không sửa giao dịch cũ. Danh mục trùng tên và loại trong cùng tài khoản bị từ chối.

## Gợi ý phân loại thử nghiệm — TASK 08A / 10C

Biểu mẫu có hai chế độ thử nghiệm **VI — Tiếng Việt** (mặc định) và **EN — Tiếng Anh**, đặt gọn dưới Mô tả. Người dùng tự chọn; không nhận diện ngôn ngữ hoặc tự chuyển mô hình khi lỗi. Gợi ý có thể sai: phải kiểm tra, chọn danh mục rồi bấm **Áp dụng**; sau đó tự bấm **Lưu giao dịch**. Đổi chế độ, mô tả hoặc loại thu/chi hủy gợi ý cũ, kể cả phản hồi đang chờ. Thông tin mô hình và phản hồi trong mục **Về mô hình và phản hồi**.

Mô hình tiếng Việt là Pipeline TF-IDF `char_wb` (3,5) + LinearSVC C=10 của TASK 10B, giữ bản fit trên train, không refit. Dữ liệu mô phỏng nhỏ do dự án biên soạn với AI; chưa được kiểm chứng trên giao dịch thật đại diện người Việt. Giữ dấu khi chuẩn hóa NFC/casefold/khoảng trắng, bỏ đúng một tiền tố đầu `[debit]`/`[credit]`. Không hiển thị điểm kiểm thử hay decision score như độ chắc chắn của giao dịch; không có blacklist câu mơ hồ.

Artifact tiếng Việt riêng: `data/experiments/classification-vietnamese/task10b-vi-v1/models/char_linearsvc_C_10.joblib`, SHA-256 **`19709b38d0dfc0ffc4ced3ae94c7e27e3a7ec77bac8a781dd497a70e34a26f55`**. Xác minh với metadata `docs/metadata/vietnamese-classification-experiment-results.json` và `artifact-manifest.json` trong thư mục run trước khi giải tuần tự. Nếu chuyển máy, sao chép riêng artifact cùng manifest từ bản thí nghiệm đáng tin cậy. Không tải artifact do người dùng gửi.

Có thể đặt đường dẫn tiếng Việt trong PowerShell trước khi khởi động máy chủ:

```powershell
$env:DJANGO_VI_CLASSIFICATION_MODEL_PATH = 'D:\KHÓA LUẬN TỐT NGHIỆP\data\experiments\classification-vietnamese\task10b-vi-v1\models\char_linearsvc_C_10.joblib'
$env:DJANGO_VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH = 'D:\KHÓA LUẬN TỐT NGHIỆP\data\experiments\classification-vietnamese\task10b-vi-v1\artifact-manifest.json'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py runserver 127.0.0.1:8001
```

Metadata tiếng Việt dùng `VI_CLASSIFICATION_METADATA_PATH` trong cấu hình máy chủ. Không có mô hình/manifest, sai hash hoặc lỗi runtime thì báo không có gợi ý; vẫn nhập thủ công được. Không cài adapter DLL vào máy chủ. Chi tiết cấu hình, kiểm thử và kiểm tra giao diện: [docs/vietnamese-classification-integration.md](docs/vietnamese-classification-integration.md).

**Cấu hình tiếng Anh được giữ nguyên:**

Mô hình là Pipeline TF-IDF ký tự (`char_wb`, n-gram 3–5) + LinearSVC `C=10` đã chọn ở TASK 06B, không huấn luyện lại. Mô hình được đánh giá trên dữ liệu tổng hợp tiếng Anh, chưa được kiểm chứng cho tiếng Việt. Kết quả là nhãn dự đoán, không phải xác suất hay độ chắc chắn cho giao dịch.

Artifact mặc định trên máy:

```text
data/experiments/classification/task06b-v1-final/models/char_linearsvc_C_10p0.joblib
```

SHA-256 phải là `362328789e3c35923896ae8c639da2a40065a01950b67edf36e02e2c5174e345`, khớp metadata `docs/metadata/classification-experiment-results.json`. Dịch vụ kiểm tra hash trước khi tải chính các byte đã kiểm tra; chỉ cache Pipeline đã xác minh, vẫn hash lại tệp mỗi lần gợi ý. Chỉ sử dụng artifact do dự án tạo; không tải joblib/pickle lạ hoặc thay hash để bỏ qua xác minh. Mô hình vẫn nằm ngoài Git. Khi sao chép mã sang máy khác, phải chuyển riêng artifact này từ bản thí nghiệm đáng tin cậy; không có mô hình thì nhập thủ công vẫn dùng được.

Có thể chọn đường dẫn cục bộ khác **ở phía máy chủ**, trước khi khởi động lại Django (không nhập đường dẫn vào biểu mẫu):

```powershell
$env:DJANGO_CLASSIFICATION_MODEL_PATH = 'D:\KHÓA LUẬN TỐT NGHIỆP\data\experiments\classification\task06b-v1-final\models\char_linearsvc_C_10p0.joblib'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py runserver 127.0.0.1:8001
```

Không thêm launcher DLL vào máy chủ. Nếu thiếu thư viện, sai hash, lỗi nạp hoặc lỗi runtime: phần gợi ý báo tạm không sẵn sàng và vẫn cho nhập thủ công. Không cài thêm thư viện trong request.

Cách thử bằng trình duyệt:

1. Đăng nhập, vào **Danh mục → Thêm/Sửa**. Tự chọn **Liên kết với nhãn mô hình — tùy chọn** phù hợp: `Income` chỉ cho thu nhập, các nhãn còn lại cho chi tiêu. Có thể bỏ trống. Không có ánh xạ tự động từ tên danh mục; nhiều danh mục được phép cùng nhãn. `Transfer` không được ánh xạ vào thu/chi.
2. Vào **Thêm/Sửa giao dịch**, chọn loại thu/chi và nhập mô tả. Bấm **Gợi ý danh mục**. Có thể thử một chuỗi mô tả tiếng Anh, nhưng cần tự kiểm tra kết quả.
3. Nhãn dự đoán hiện ra; nếu có ánh xạ thuộc tài khoản và đúng loại thì chọn danh mục trong khung gợi ý, bấm **Áp dụng danh mục đã chọn**. Trước khi bấm, danh mục hiện tại giữ nguyên. Nếu không có ánh xạ, chỉ hiển thị nhãn; không tạo danh mục. `Transfer` hoặc nhãn khác loại luôn yêu cầu xem lại, không có nút áp dụng khả dụng.
4. Xem lại số tiền, ngày và danh mục rồi tự bấm **Lưu giao dịch**. Gợi ý/Áp dụng không lưu giao dịch và không tự học. Đổi mô tả hoặc loại sẽ hủy gợi ý cũ để tránh áp dụng nhầm.
5. Mô tả rỗng, chỉ có tiền tố hoặc không có đặc trưng phù hợp trả về không có gợi ý. Đầu vào tối đa 500 ký tự. Không gửi mô tả sang dịch vụ bên ngoài và không ghi mô tả vào log suy luận.

Migration `0002_category_canonical_label` chỉ thêm trường tùy chọn với giá trị rỗng; không tự ánh xạ hay tạo dữ liệu. Hãy chạy `manage.py migrate` trước khi mở website sau cập nhật.

## Nhập CSV có xem trước — TASK 08B

Vào **Giao dịch → Nhập CSV có xem trước**. Tải mẫu chỉ có header, tự chuẩn bị tệp UTF-8 (chấp nhận BOM), rồi **Kiểm tra và xem trước → Xác nhận nhập toàn bộ**. Tối đa 2 MiB và 5.000 giao dịch/lần. Các cột phải đúng thứ tự:

```text
date,kind,amount,category,description
```

Ngày dùng `YYYY-MM-DD`; loại là `income`/`expense`; số tiền là số nguyên VND dương, tối đa 15 chữ số, không có dấu phân cách. Danh mục phải thuộc tài khoản của bạn và đúng loại (so tên không phân biệt hoa/thường, không tự bỏ khoảng trắng). Mô tả có thể trống, tối đa 500 ký tự, vẫn giữ đủ 5 cột. Không nhận cột `user_id`. Có lỗi thì chưa cho xác nhận; không tự tạo danh mục hay gán ML.

Trang xem trước hiển thị số giao dịch, tổng thu/chi Decimal, mẫu tối đa 20 dòng và các lỗi/cảnh báo theo số dòng. Những dòng giống nhau chỉ được cảnh báo, không tự xóa/gộp. Tệp có cùng SHA-256 đã nhập thành công trong tài khoản sẽ bị chặn nhập lại. Hash tính trên byte gốc, không phải cách nhận diện mọi giao dịch trùng giữa các tệp khác nhau. Khoảng ngày trong CSV không chứng minh độ phủ lịch sử đầy đủ.

Bản xem trước giữ trong SQLite phía máy chủ và có hạn xác nhận **30 phút**, không nằm trong cookie. Khi nhập thành công, nội dung tạm được xóa ngay; chỉ giữ dấu vết tài khoản/hash/thời điểm/số dòng để chặn lại tệp. Khi tải tệp tiếp theo, hệ thống dọn các lô hết hạn của tài khoản đó. Chạy lệnh dưới để dọn mọi lô hết hạn trên máy, chẳng hạn khi bắt đầu/kết thúc buổi làm việc (không xóa giao dịch hoặc dấu vết hash thành công):

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate
& '.\.venv\Scripts\python.exe' -X utf8 manage.py cleanup_csv_imports
```

Hết hạn có nghĩa là không thể xem/xác nhận payload nữa; xóa vật lý diễn ra khi có lần dọn nói trên, không có tác vụ chạy theo đồng hồ riêng. Chi tiết định dạng, tính nguyên tử, giới hạn và kiểm thử ở [docs/csv-import.md](docs/csv-import.md).

## Lịch sử ghi chép theo tháng — TASK 08C

Mở **Lịch sử ghi chép**, chọn năm để xem các tháng đã kết thúc, tổng chi đã ghi và số giao dịch (cả thu lẫn chi). Trạng thái mặc định là **Chưa xác nhận**. Bạn có thể đánh dấu **Chưa đầy đủ**, **Xác nhận đầy đủ** hoặc **Hủy xác nhận**. Đây là xác nhận của bạn, không phải hệ thống chứng minh đã có mọi giao dịch.

Chỉ xác nhận đầy đủ tháng đã kết thúc theo `Asia/Ho_Chi_Minh`. Nếu tổng chi đã ghi bằng 0, trang hỏi **“Bạn xác nhận tháng này không có khoản chi?”** và yêu cầu đánh dấu rõ trước khi xác nhận. Thời điểm xác nhận được lưu và hiển thị; hủy xác nhận sẽ xóa thời điểm hiện hành.

Thêm, sửa, xóa hoặc nhập CSV thành công đưa các tháng liên quan về **Chưa xác nhận**. Đổi ngày qua tháng khác làm mất xác nhận ở cả tháng cũ và mới, kể cả thay đổi giao dịch thu nhập. Thao tác thất bại/rollback không làm mất xác nhận. Nếu giao dịch thay đổi sau khi mở trang xác nhận, hãy mở lại trang để kiểm tra; trang cũ không được dùng để xác nhận dữ liệu mới.

Tải CSV không tự xác nhận tháng nào. Dịch vụ chuẩn bị lịch sử giữ các tháng liên tiếp: chỉ tháng đã xác nhận đầy đủ mới có giá trị tổng chi dùng cho dự báo; tháng chưa xác nhận/chưa đầy đủ vẫn là **chưa biết**, không tự điền 0. Chạy `manage.py migrate` sau cập nhật để tạo bảng trạng thái mới, không sửa giao dịch cũ. Chi tiết ở [docs/monthly-coverage.md](docs/monthly-coverage.md).

## Ước tính tổng chi theo tài khoản — TASK 08D

Mở **Dự báo**. Tháng đích là **tháng hiện tại theo giờ Việt Nam** (ví dụ đang tháng 10 thì ước tính tổng tháng 10). Chỉ dùng đoạn tháng liên tiếp đã được chính bạn xác nhận đầy đủ, kết thúc đúng tháng liền trước. Không dùng giao dịch tháng hiện tại/tương lai để tính; không nối qua tháng chưa biết hoặc tự điền 0. Mục tiêu là **tổng các khoản expense được ghi trong website**, không phải toàn bộ chi tiêu thực tế.

- Dưới 3 tháng: báo thiếu lịch sử và liên kết tới đúng các tháng cần kiểm tra/xác nhận. Không tạo ước tính giả.
- Từ 3 đến 35 tháng: **Ước tính theo trung bình 3 tháng**, không phải Machine Learning.
- Từ 36 tháng: khi bấm **Tính dự báo**, so sánh tháng trước, trung bình 3 tháng, cùng tháng năm trước và StandardScaler + Ridge với alpha 0,1/1/10 trên 6 tháng validation cuối, cuốn chiếu một bước. Chọn MAE nhỏ nhất; hòa chính xác ưu tiên baseline theo thứ tự TB 3 tháng → tháng trước → cùng tháng năm trước; Ridge hòa chọn alpha nhỏ hơn. Có thể chọn baseline, không ép chọn ML. Sau lựa chọn, dùng toàn bộ lịch sử hợp lệ để tính tháng hiện tại.

Kết quả hiện tháng đích, số tháng, phương pháp, số VND làm tròn và bảng MAE khi đủ điều kiện. MAE validation không phải sai số test độc lập, khoảng tin cậy hoặc cam kết sai số tương lai. Không hiển thị phần trăm chính xác.

Chỉ POST có CSRF từ nút **Tính dự báo** mới tính/fit. Mở lại trang chỉ kiểm tra và đọc kết quả đã lưu; không huấn luyện lại. Mỗi kết quả giữ riêng trong SQLite theo tài khoản và dấu vân tay dữ liệu/xác nhận/cấu hình. Giao dịch (kể cả tháng hiện tại/tương lai) hoặc xác nhận thay đổi, cấu hình/runtime đổi, hay sang tháng mới thì kết quả cũ bị ẩn, yêu cầu tính lại. Nếu dữ liệu đổi trong lúc tính thì không công bố kết quả đó. Nhánh ML lỗi sẽ báo rõ, không tự gắn nhãn ML cho baseline thay thế.

Ridge từng lần tính chỉ ở bộ nhớ; không lưu/chia sẻ model người dùng, không dùng model, tiền tệ hoặc dữ liệu MoneyData. Kết quả VND được lưu dưới dạng chuỗi số nguyên và đọc thành Decimal để tránh SQLite làm tròn số lớn. Không đưa SQLite hoặc dữ liệu người dùng lên Git. Giữ nguyên các thí nghiệm nghiên cứu trước đó.

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate
& '.\.venv\Scripts\python.exe' -X utf8 manage.py runserver 127.0.0.1:8001
```

Không cần thêm thư viện hoặc tải mô hình cho chức năng này; dùng scikit-learn hiện có. Cách tính, dấu vân tay, lưu trữ và kiểm thử ở [docs/forecast-integration.md](docs/forecast-integration.md).

## Kiểm thử

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py makemigrations --check --dry-run
& '.\.venv\Scripts\python.exe' -X utf8 manage.py test --verbosity 2
```

Django tạo cơ sở dữ liệu kiểm thử riêng trong bộ nhớ. Các tài khoản và giao dịch trong kiểm thử chỉ là dữ liệu kiểm thử tạm thời, không được ghi vào `db.sqlite3` đang sử dụng. Các nhóm kiểm thử bao gồm đăng ký/đăng nhập/đăng xuất, CSRF, phân quyền giữa hai tài khoản, danh mục, tổng theo tháng và tiền/ngày/loại giao dịch không hợp lệ.

TASK 08A bổ sung kiểm thử hash/metadata, chuẩn hóa, vector rỗng, lỗi runtime/thiếu mô hình, ánh xạ đúng chủ sở hữu và loại, Transfer và migration giữ dữ liệu cũ. Kiểm thử sự kiện JavaScript nằm ở `scripts/test_transaction_suggestion.js`, dùng các module chuẩn của Node, không cần `npm install`; nếu máy có Node thì chạy `node --test scripts/test_transaction_suggestion.js`. Node chỉ phục vụ kiểm thử này, không phải yêu cầu để chạy website. Kết quả kiểm tra thực tế và danh sách tệp thay đổi: [docs/classification-integration.md](docs/classification-integration.md).

## Dữ liệu và cấu hình cục bộ

- `db.sqlite3`: dữ liệu thực của bạn, chỉ được tạo cấu trúc bảng khi chạy migrations; không tự thêm tài khoản, danh mục hoặc giao dịch.
- Lô CSV tạm và dấu vết hash thành công cũng nằm trong SQLite riêng tư này. Không đưa database/backup lên Git; dọn CSV hết hạn bằng lệnh ở trên. Website không lưu tệp CSV trong thư mục static hoặc cho tải lại bản gốc qua URL.
- `secrets/django-secret-key.txt`: khóa ngẫu nhiên được tạo riêng cho máy ở lần chạy đầu, đã được `.gitignore` loại trừ. Có thể thay bằng biến môi trường `DJANGO_SECRET_KEY` nếu cần. Không chia sẻ khóa này.
- Mọi trang quản lý yêu cầu đăng nhập và lọc dữ liệu theo chủ sở hữu, kể cả khi nhập trực tiếp URL hoặc giả mạo ID trong biểu mẫu.
- Biểu mẫu POST sử dụng CSRF; Django kiểm tra và băm mật khẩu, quản lý phiên và escape nội dung đầu ra. Thao tác xóa và đăng xuất yêu cầu POST.
- `DEBUG` mặc định bật để phát triển cục bộ; `ALLOWED_HOSTS` chỉ cho phép localhost. Đây là cấu hình chạy máy cá nhân bằng HTTP, chưa phải cấu hình triển khai công khai.
- `.gitignore` hiện có loại trừ môi trường ảo, khóa bí mật, dữ liệu cá nhân và SQLite. Hãy sao lưu `db.sqlite3` ở nơi riêng tư trước khi tự chỉnh sửa hoặc di chuyển dữ liệu.

## Demo dự báo độc lập (TASK 09A)

Đăng nhập → **Dự báo** → **Demo dự báo**, hoặc mở `/du-bao/demo/`. Bấm nút **Demo dự báo** để chạy thật baseline/Ridge trên 48 tổng tháng tự sinh; tháng đích cố định 01/2026. Đây là dữ liệu mô phỏng, không phải MoneyData hay giao dịch thật. Không tạo giao dịch, xác nhận tháng hoặc kết quả dự báo cá nhân. Kết quả demo chỉ ở RAM máy chủ, mở lại trang không tính lại; restart thì bấm tính lại. Hướng dẫn và kịch bản trình diễn 3–5 phút: [docs/demo-guide.md](docs/demo-guide.md).

## Cấu trúc chính

Render Free (TASK 14A): dùng riêng `config.render`, PostgreSQL qua `DATABASE_URL`, Waitress và WhiteNoise; local không đổi. Build: `bash deploy/render-build.sh`; Start: `bash deploy/render-start.sh`. Xem [env, private Release, migrations và giới hạn chưa kiểm chứng](docs/render-deployment.md). Chưa deploy; không dùng profile SQLite của TASK 13C trên Render Free.

Chuẩn bị triển khai (TASK 13C): local vẫn dùng `config.settings` và các lệnh hiện tại. Production dùng riêng `config.production`, môi trường bắt buộc, SQLite trên storage bền vững và WSGI Waitress; chưa deploy. Xem [cấu hình, static, gói EN/VI và kết quả kiểm tra](docs/deployment-preparation.md). `.env.example` chỉ có placeholder, Django không tự đọc `.env`. `requirements-production.txt` thêm Waitress, giữ nguyên `requirements.txt` và phiên bản ML.

```text
config/                 Cấu hình Django và URL gốc
finance/models.py       Danh mục, giao dịch và quy tắc dữ liệu
finance/forms.py        Biểu mẫu và giới hạn lựa chọn danh mục
finance/views.py         Các trang, CRUD và kiểm tra chủ sở hữu
finance/services.py      Tổng thu/chi Decimal theo tháng
finance/tests.py         Kiểm thử tự động
finance/migrations/      Lịch sử cấu trúc cơ sở dữ liệu
templates/               Giao diện Django tiếng Việt
static/                  CSS responsive và hỗ trợ chọn danh mục
requirements.txt         Phiên bản thư viện được giữ nguyên
```
## Mục tiêu tiết kiệm — TASK 18A

Trong nhóm **Kế hoạch**, mở **Mục tiêu tiết kiệm** để tạo mục tiêu, nhập số tiền cần đạt, ngày bắt đầu, hạn dự kiến và ghi chú tùy chọn. Ghi nhận **Đóng góp** hoặc **Rút khỏi mục tiêu** bằng số tiền dương, ngày thực tế không ở tương lai hoặc trước ngày bắt đầu. Có thể nhập `50000` hoặc `50.000`; tiền hiển thị `50.000 VND`.

Đây là **phân bổ do bạn tự ghi nhận**, không phải số dư ngân hàng hoặc tiền được hệ thống giữ hộ. Không tự tạo giao dịch thu/chi, lấy chênh lệch thu–chi làm tiết kiệm hoặc thay đổi ngân sách, coverage, dự báo và phản hồi ML. Chưa liên kết ngân hàng/giao dịch.

Mục tiêu có trạng thái **Đang thực hiện / Đã đạt / Đã lưu trữ**. Quá hạn chỉ cảnh báo; đạt/vượt vẫn được đóng góp. Lưu trữ giữ lịch sử, phải mở lại trước khi sửa mục tiêu hoặc thêm/sửa/xóa khoản. Sửa khoản có ô xác nhận; xóa có trang xác nhận. Hệ thống kiểm lại toàn lịch sử theo ngày rồi ID, từ chối nếu âm tại bất kỳ thời điểm nào. Hai khoản hợp lệ cùng ngày/số tiền vẫn được ghi riêng; mã thao tác chặn gửi lại cùng POST. Tổng quan hiển thị tối đa 3 mục tiêu chưa đạt, chưa lưu trữ.

**Migration `0013_savings_goals` đã áp dụng trên SQLite QA, PostgreSQL 18.6 QA localhost và SQLite local của dự án chính**. Bàn giao local ngày 26/10/2026 đã sao lưu bằng backup API, kiểm integrity/khóa ngoại/hash; dữ liệu nghiệp vụ cũ giữ nguyên, ba bảng tiết kiệm mới rỗng và system check đạt. Chưa kết nối hoặc chạy migration production trong bàn giao. Đã kiểm ba tình huống HTTP đồng thời trên PostgreSQL QA; không coi là kiểm tải hoặc mọi lịch tranh chấp. Chi tiết backup, quy tắc, triển khai, phạm vi PostgreSQL, kiểm thử và ảnh: [docs/savings-goals.md](docs/savings-goals.md).

## Ngân sách tháng (TASK 13A)

Mở **Ngân sách** trên menu, chọn tháng và **Tạo ngân sách**. Để trống danh mục để đặt hạn mức tổng; chọn danh mục chi của chính bạn để đặt hạn mức riêng. Số tiền là số nguyên VND dương, tối đa 15 chữ số. Mỗi phạm vi/tháng chỉ có một ngân sách, có thể sửa hoặc mở trang xác nhận xóa.

Số **Chi đã ghi nhận** lấy từ giao dịch chi của tháng; không dùng dự báo. Ngân sách tổng và danh mục không cộng thành một hạn mức. Cảnh báo theo các mốc 80%/100%/vượt; thanh vẽ tối đa 100%, số tiền/tỷ lệ vẫn hiển thị mức vượt thật. Tổng quan có tóm tắt cùng tháng và vẫn hiển thị trạng thái lịch sử ghi chép. Chưa có email hoặc thông báo đẩy.

Danh mục có ngân sách bị chặn xóa/đổi loại/chủ sở hữu; có thể đổi tên, hoặc xử lý ngân sách trước. Lưu/xóa ngân sách không thay đổi giao dịch, coverage hoặc kết quả dự báo. Cần khởi động lại server sau cập nhật code và áp dụng `0007_budget`, `0008_budget_category_guards` bằng Python `.venv` của **dự án chính**, sau khi sao lưu SQLite bằng backup API. Hai migration đã áp dụng trên máy hiện tại; không cần chạy trên bản phục hồi cổng 8003. Xem [quy tắc, kiểm thử và ảnh QA](docs/monthly-budget.md).

### Hướng dẫn liên kết danh mục với nhãn mô hình (TASK 19A)

Trong **Danh mục → Thêm/Sửa**, mặc định **Chưa ánh xạ**. Danh mục vẫn ghi giao dịch bình thường khi để trống. Chỉ chọn nhãn khi phạm vi phù hợp; xem **Xem phạm vi 17 nhãn mô hình** để đọc tên tiếng Việt, mã gốc và ranh giới. Giải trí (`Entertainment`) khác ăn uống chế biến sẵn (`Restaurants`) và du lịch (`Travel`); hệ thống không tự sửa hoặc chặn theo tên danh mục.

Thông báo các danh mục cùng nhãn chỉ thuộc tài khoản và loại đang chọn, không cấm lưu. Khi tắt JavaScript, điền biểu mẫu rồi bấm **Kiểm tra liên kết (chưa lưu)** để xem thông báo từ server, sau đó tự bấm **Lưu danh mục**. Đổi tên giữ ID/liên kết giao dịch; tên mới cũng xuất hiện trên giao dịch hiện có. Snapshot phản hồi ML đã lưu được giữ nguyên. Không cần migration cho TASK 19A. Xem [docs/category-mapping-help.md](docs/category-mapping-help.md) về quy tắc, kiểm thử và ảnh QA.

### Báo cáo thu–chi tháng và in PDF (TASK 19B)

Từ **Tổng quan**, chọn tháng rồi bấm **Báo cáo tháng**. Báo cáo gồm tổng thu/chi/chênh lệch, số giao dịch, cơ cấu chi và đối chiếu số đã ghi với tháng trước; hiển thị trạng thái ghi chép của cả hai tháng. Chọn **Bao gồm toàn bộ giao dịch trong tháng** rồi bấm **Xem báo cáo** nếu muốn in chi tiết (mặc định không chọn, không giới hạn 20 dòng).

Bấm **In / Lưu PDF** và chọn **Save as PDF**, khổ **A4**; có thể tắt header/footer do trình duyệt thêm nếu không muốn in URL. Khi JavaScript tắt, biểu mẫu vẫn hoạt động và có thể dùng Ctrl+P/menu In. Website không tự tạo/lưu/gửi PDF. Hãy lưu bản in chứa dữ liệu tài chính ở nơi riêng tư.

Đây là số đang ghi trong website, không phải chứng từ ngân hàng hay snapshot bất biến. Tháng trống không chứng minh không phát sinh thu/chi; tháng chưa đầy đủ không cho phép diễn giải chênh lệch là xu hướng thực tế. Khoản định kỳ chưa ghi nhận và tiền phân bổ mục tiêu không cộng vào thu–chi. Không tự xác nhận coverage hoặc tạo dự báo. Xem [docs/monthly-report.md](docs/monthly-report.md) về phạm vi, kiểm thử, PDF QA và giới hạn. Không cần migration.

### Phản hồi thao tác và bàn phím (TASK 19C)

Khi gửi biểu mẫu hợp lệ, trang hiện trạng thái đang xử lý và chặn gửi lặp tại giao diện; kiểm tra phía server vẫn giữ nguyên. Sau lỗi server, tóm tắt lỗi nhận focus và có liên kết tới trường cần sửa. Có thể dùng Tab/Enter, liên kết **Đến nội dung chính** và menu/phần mở rộng gốc của trình duyệt.

Nhập nhanh và gợi ý ML có thời gian chờ 20 giây, không tự retry; lỗi không làm mất dữ liệu nhập tay. Nếu mất kết nối sau thao tác tài chính, **chưa xác nhận được kết quả**: kiểm tra danh sách/trạng thái trước khi gửi lại, vì server có thể đã xử lý. Back/Forward khôi phục trạng thái giao diện. Khi tắt JavaScript vẫn dùng biểu mẫu nhập tay; nhập nhanh/ML vẫn cần JavaScript. Xem [docs/interaction-accessibility.md](docs/interaction-accessibility.md) về bằng chứng thật/giả lập, kiểm thử và giới hạn; không phải chứng nhận WCAG toàn diện.

### Tạo giao dịch tương tự (TASK 20A)

Ở **Chi tiết giao dịch**, bấm **Tạo giao dịch tương tự** (khác nút Sửa). Form điền mô tả, loại, số tiền và danh mục còn hợp lệ; ngày là **hôm nay theo giờ Việt Nam**. Mở form chưa tạo giao dịch. Kiểm tra/chỉnh rồi tự bấm **Lưu giao dịch**; giao dịch mới độc lập, không sửa nguồn hoặc nối vào kỳ định kỳ/lô CSV cũ. Không có phản hồi ML từ việc điền trước; muốn dùng ML phải yêu cầu gợi ý mới và chủ động Áp dụng như bình thường.

Mỗi lần mở form có mã thao tác mới, hiệu lực **2 giờ**. Gửi lại cùng mã/cùng dữ liệu dẫn tới giao dịch đã lưu; đổi dữ liệu với mã đã dùng bị từ chối. Hai lần chủ động mở form có thể tạo hai khoản hợp lệ giống nhau. Nếu mất kết nối, kiểm danh sách trước khi gửi lại; hệ thống không tự retry.

Cần migration **`0014_similar_transaction_operation`** để lưu receipt chống trùng bền vững. Giai đoạn QA đã kiểm trên SQLite/PostgreSQL riêng; bàn giao ngày **27/10/2026** đã sao lưu bằng SQLite backup API, kiểm bản sao và áp dụng vào **SQLite local thật**, system check đạt, dữ liệu nghiệp vụ cũ giữ nguyên. **Chưa áp dụng hoặc kiểm trên production.** Các máy/database khác vẫn cần sao lưu và migrate theo quy trình được duyệt. Xem [docs/duplicate-transaction.md](docs/duplicate-transaction.md) về bàn giao, triển khai, kiểm thử và ảnh QA.

### Lịch thu–chi (TASK 20B)

Mở **Ghi chép → Lịch thu–chi**, chọn tháng hoặc dùng Tháng trước/sau/hiện tại. Desktop là lịch tuần bắt đầu thứ Hai; mobile là danh sách theo ngày. Mỗi ngày xem trước tối đa 3 mục; bấm ngày hoặc **Xem thêm** để xem đủ, phân trang 20 dòng. Ngày hôm nay theo giờ Việt Nam.

Tổng thu/chi chỉ gồm giao dịch đã lưu, định dạng `50.000 VND`. Khoản định kỳ có nhãn **Dự kiến**, không cộng vào tổng; **Ghi nhận** chỉ mở biểu mẫu xác nhận hiện có. Kỳ đã ghi nhận không hiện tiếp như khoản chưa trả; giao dịch nằm ở ngày thực tế. Giao dịch ngày tương lai đã lưu vẫn có trong số đã ghi nhận và được đánh dấu rõ.

Định kỳ giữ phạm vi 12 tháng đến tháng hiện tại và xem trước tháng sau; ngoài phạm vi có thông báo, không ngầm kết luận không có khoản đến hạn. Ngày/tháng trống không chứng minh không phát sinh thu/chi. Xem lịch không tạo kỳ/giao dịch, không xác nhận coverage hoặc tính dự báo. Không cần migration hoặc dependency mới. Xem [docs/financial-calendar.md](docs/financial-calendar.md) về truy vấn, kiểm thử, ảnh QA và giới hạn.
