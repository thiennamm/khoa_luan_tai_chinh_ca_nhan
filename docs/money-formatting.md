# TASK 17C — Thống nhất tiền VND

Ngày thực hiện và chốt bàn giao: 25/10/2026. Mã được bàn giao lên `main` theo yêu cầu chốt TASK 17C; SHA và kết quả push được báo trong tin nhắn bàn giao. Chỉ dùng SQLite QA mới, không kết nối production hoặc áp dụng migration vào SQLite thật. Push không được coi là bằng chứng UI trên Render đã hoạt động; chưa kiểm online trong task này.

## Quy ước hiển thị và nhập

Tiền trên trang dùng dấu chấm phân cách hàng nghìn và hậu tố có khoảng trắng: **0 VND; 50.000 VND; 1.250.000 VND; -50.000 VND**. Giá trị chưa biết (`None`) hiện **—**, không tự thành 0. Giữ phép định dạng nguyên đồng `.0f` của bộ lọc cũ; không thay quy tắc làm tròn, phép tính hoặc giá trị lưu. Số chi trong danh sách vẫn có dấu trừ trình bày, số tiền lưu vẫn dương theo model.

| Nơi nhập | Chấp nhận | Không chấp nhận |
|---|---|---|
| Trường số tiền giao dịch/ngân sách/quy tắc và xác nhận định kỳ | `50000`, `50.000`, `1.250.000`; khoảng trắng ngoài được bỏ | `50.00`, `1.25.000`, `50,000`, `1.000,00`, `50 000`, `50.000 VND`, `+50000`, số âm, phần lẻ, `5e4` |
| CSV nhập/xuất | Giữ hợp đồng số nguyên không dấu phân cách, ví dụ `50000` | CSV nhập vẫn từ chối `50.000`; không dùng bộ đọc trường tiền mới cho CSV |
| Câu nhập nhanh | Giữ các đơn vị/cú pháp đã có: `45k`, `45 nghìn`, `1,5 triệu`, `45000đ`… | Không mở rộng parser trong task này |

Giới hạn trường tiền vẫn là **1–999999999999999**, kiểm lại bằng Decimal phía server. Nhóm có dấu chấm phải gồm nhóm đầu 1–3 chữ số không bắt đầu bằng 0, các nhóm sau đúng 3 chữ số; `0.000`, `001.000` bị từ chối. Chuỗi chữ số thuần có số 0 đầu vẫn được đọc theo số nguyên (trong giới hạn độ dài); giao diện chỉ gọn lại khi rời ô. Không xóa mọi dấu chấm/phẩy để cố biến đầu vào sai thành tiền hợp lệ.

Trường dùng `type=text`, `inputmode=numeric`, nhãn VND bên cạnh và nhãn trường có đơn vị. JavaScript tự phân nhóm số nguyên khi nhập/dán hợp lệ, giữ vị trí theo thứ tự chữ số khi sửa giữa chuỗi hoặc chọn đoạn. Backspace ngay sau dấu chấm tự động xóa chữ số ngay trước dấu chấm; Delete ngay trước dấu chấm xóa chữ số ngay sau. Đầu vào dán có nhóm sai được giữ để sửa; không âm thầm quy đổi. Gõ/xóa chữ số từ một giá trị hợp lệ có thể tạm làm lệch nhóm: chỉ trường hợp chỉnh sửa đã biết này mới được phân nhóm lại. Không can thiệp giữa một phiên composition/IME.

Khi JavaScript tắt, nhãn VND vẫn có và backend vẫn nhận số nguyên hoặc nhóm dấu chấm hợp lệ. Form lỗi giữ nguyên chuỗi sai. Trường không dùng JavaScript làm nguồn xác thực duy nhất. Nhập nhanh vẫn cần xác nhận thay thế khi form có dữ liệu; chỉ điền form, không tự gọi ML hoặc lưu. Việc đổi mô tả/loại vẫn vô hiệu gợi ý ML qua luồng có sẵn và backend kiểm lại khi lưu.

## Thành phần dùng chung và phạm vi

- `finance/money.py`: định dạng hiển thị Python và nhận diện chặt chuỗi tiền form; không dùng cho CSV hoặc parser nhập nhanh.
- Bộ lọc template `vnd` chuyển tiếp vào hàm chung, áp dụng cho Tổng quan, giao dịch/chi tiết/xóa, ngân sách, định kỳ/ghi nhận/lịch sử, coverage, dự báo/lịch sử/demo, xem trước CSV. Biểu đồ Tổng quan giữ nhãn đơn vị rút gọn như **triệu VND**, cùng bảng tiền đầy đủ và giải thích tháng chưa xác nhận. Trục 0 của demo dùng cùng bộ lọc.
- `finance/money_fields.py` và widget trong app: cả ba ModelForm dùng chung VNDAmountField/VNDInput; xác nhận định kỳ kế thừa TransactionForm. Giữ validator model, quyền sở hữu, loại danh mục và giới hạn cũ.
- `static/js/money.js`: API `SoThuChiMoney` chung cho ô nhập và hiển thị động. `quick-entry.js` dùng lại để điền trường tiền, tóm tắt và bảng nhận diện. Được nạp bằng `defer` trước script nhập nhanh, không CDN/dependency mới.
- CSV, tiền lưu database, tổng hợp tài chính, coverage, ngân sách, điều kiện/thuật toán dự báo và suy luận/phản hồi ML không đổi. Không thay giá trị chưa biết bằng 0.

**Không cần migration**: không đổi schema/model. `makemigrations --check --dry-run` trên QA báo `No changes detected`.

## Kiểm thử thực tế

| Nhóm | Kết quả | Phạm vi |
|---|---|---|
| Django toàn `finance` | **325/325 đạt**, 140,894 giây | Hồi quy gồm cả 7 bài tiền mới, không cộng lại thành 332 |
| Django tiền mới, chạy riêng trước hồi quy | **7/7 đạt** | 0/âm/số lớn/chưa biết, giữ làm tròn, chuỗi hợp lệ/sai/quá giới hạn, cùng field ở các form, POST hợp lệ và giữ lỗi |
| JavaScript | **30/30 đạt** | 5 bài formatter/input mới và các bài nhập nhanh, ML suggestion, form feedback; không cộng với kết quả cũ của TASK 17B |
| Django tiền + demo sau chỉnh cuối nhãn 0 trên trục demo | **19/19 đạt**, 11,476 giây | Thuộc suite 325; kiểm lại phần liên quan, không cộng thành tổng mới |
| Django system check QA | **Không lỗi** | Settings chỉ tới SQLite QA |
| Kiểm migration QA | **Không thay đổi** | Chỉ kiểm khô, không tạo migration |

Lệnh kiểm thử dùng runtime sẵn có `D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe` (Python 3.13, không cài lại dependency) và wrapper/settings riêng ngoài Git tại thư mục QA bên dưới:

```powershell
& 'D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe' -X utf8 'D:\SAO LUU KHOA LUAN\qa-17c-20261025\manage_qa.py' test finance --noinput --settings=qa17c_test_settings
node --test scripts/test_money.js scripts/test_quick_entry.js scripts/test_transaction_suggestion.js scripts/test_form_feedback.js
& 'D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe' -X utf8 'D:\SAO LUU KHOA LUAN\qa-17c-20261025\manage_qa.py' check
& 'D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe' -X utf8 'D:\SAO LUU KHOA LUAN\qa-17c-20261025\manage_qa.py' makemigrations --check --dry-run
```

## QA trình duyệt và ảnh

URL QA: **http://127.0.0.1:8019/**. Database/settings/credential/ảnh/log đều ở **`D:\SAO LUU KHOA LUAN\qa-17c-20261025`**, không đưa vào Git. Database khởi tạo mới; chỉ tài khoản `qa17c_main` và dữ liệu mô phỏng, có banner QA. Không sao chép tài khoản hoặc dữ liệu thật.

Đã thao tác Edge/Chromium headless tại **1280×900** và **390×844**, locale Việt Nam/múi giờ Việt Nam, reduced motion:

- Kiểm Tổng quan, Giao dịch, Ngân sách, Định kỳ, Dự báo, Lịch sử dự báo, demo (GET), xem trước CSV có hậu tố VND; không tràn ngang toàn trang ở các trang đã kiểm. Biểu đồ vẫn có vùng cuộn riêng.
- Nhập thật qua bàn phím `50000` → `50.000`; Backspace/Delete sát dấu phân nhóm, chèn giữa chuỗi, thay một đoạn chọn, xóa hết, nhập 15 chữ số. Thay nội dung bằng `50.00` rồi rời ô: giữ nguyên, không sửa thành `5.000`. Kiểm bulk replacement mô phỏng dán; không thao tác clipboard hệ điều hành.
- Câu `Chi: Ăn trưa 1,5 triệu` vẫn nhận đúng 1.500.000, tóm tắt **1.500.000 VND**, chưa lưu và chưa chọn danh mục. Không đổi cách hiểu parser.
- Một context mobile **tắt JavaScript** đã gửi form `50,000`: server báo lỗi, giữ chuỗi nhập; sửa thành `50000` lưu thành công. Một form khác gửi `50.000` cũng lưu đúng 50.000. Hai giao dịch này chỉ nằm trong QA, sau thời điểm chụp các ảnh tổng hợp ban đầu.
- Đã tải CSV QA qua HTTP: BOM và cột amount vẫn là `50000`/`1250000`; kiểm lại bằng csv.reader. CSV có amount `50.000` bị từ chối, không có thao tác xác nhận nhập.
- Dự báo QA dùng 6 tháng mô phỏng có xác nhận để hiện trung bình 3 tháng; không fit Ridge mới. Demo chỉ mở GET để xem lịch sử, không chạy lại thí nghiệm. Kiểm thử tự động bao phủ định dạng kết quả/MAE demo; chưa chụp lại demo đã tính trên trình duyệt trong đợt này.

Ảnh ban đầu: Tổng quan có thu 1.250.000, chi 1.300.000, chênh lệch **-50.000 VND**; ngân sách tổng 1.000.000 và phần vượt. Sau đó có thêm hai giao dịch QA 50.000 khi kiểm lưu không JavaScript; ảnh ban đầu và database cuối phiên khác thời điểm, không dùng chúng để khẳng định tổng hiện tại.

| Bằng chứng | Tên tệp trong thư mục QA |
|---|---|
| Tổng quan 0/âm/thu–chi, cơ cấu và ngân sách | `desktop-dashboard.png`, `mobile-dashboard.png` |
| Trường tiền và nhãn VND | `desktop-money-form.png`, `mobile-money-form.png` |
| Nhập nhanh giữ `1,5 triệu` | `desktop-quick-vnd.png`, `mobile-quick-vnd.png` |
| Các trang danh sách/ngân sách/định kỳ | `{desktop,mobile}-transactions.png`, `-budget.png`, `-recurring.png` |
| Dự báo/lịch sử/demo chưa tính | `{desktop,mobile}-forecast.png`, `-history.png`, `-demo.png` |
| Xem trước CSV | `desktop-csv-preview.png`, `mobile-csv-preview.png` |
| Lỗi server khi tắt JavaScript | `mobile-invalid-nojs.png` |
| Hồi quy, kiểm liên quan cuối và đối chiếu dữ liệu bảo vệ | `regression.log`, `money-demo-final.log`, `protected-after.json` |
| Kiểm form không JS và CSV | `browser-additional-checks.json`, `qa-export.csv`, `csv-wire-check.json` |
| Tổng hợp QA và rà diff | `browser-checks.json`, `diff-review.json`, `evidence-manifest.json` |

Ảnh/bằng chứng giữ ngoài repository. Chưa kiểm Safari/Firefox, bàn phím/clipboard trên điện thoại vật lý, screen reader hoặc UI online. Mobile là viewport mô phỏng, không phải kết quả trên thiết bị thật. Không coi kiểm HTTP hay unit test là thay thế kiểm UI.

## Tệp thay đổi và bảo vệ dữ liệu

Tệp mới: `finance/money.py`, `finance/money_fields.py`, `finance/templates/finance/widgets/vnd_input.html`, `finance/test_money.py`, `static/js/money.js`, `scripts/test_money.js`, tài liệu này.

Tệp cập nhật: `finance/forms.py`, `finance/budget_forms.py`, `finance/recurring_forms.py`, `finance/templatetags/money.py`; template `base.html`, `finance/monthly_history.html`, `finance/forecast_demo.html`, `includes/transaction_table.html`; `static/css/app.css`, `static/js/quick-entry.js`; các kỳ vọng trình bày trong `finance/tests.py`, `finance/test_forecast.py`, `finance/test_forecast_demo.py`, `finance/test_monthly_coverage.py`, `scripts/test_quick_entry.js`; và README.

Không sửa model/migration, dependency, parser Python, CSV import/export, dịch vụ ML, cấu hình local/production hoặc `.gitignore`. Đối chiếu SHA-256 SQLite thật và hai model trước/sau QA **đều khớp**; không xem nội dung dữ liệu thật hoặc ghi vào đó. Đã rà diff và quét mẫu bí mật trên **23 tệp** mới/sửa: không phát hiện mẫu credential, không có database/dataset/model/ảnh/credential QA trong danh sách thay đổi. `git diff --check` và kiểm cú pháp Node đạt. Quét mẫu không phải bảo đảm tuyệt đối cho mọi dạng bí mật.

## Chốt bàn giao: collectstatic production QA

Đã import profile **`config.render` thực tế**, `DEBUG=False`, WhiteNoise `CompressedManifestStaticFilesStorage`. Settings và đầu ra riêng tại **`D:\SAO LUU KHOA LUAN\qa-17c-20261025\handoff-17c`**, ngoài Git. Host QA dùng `.invalid`, secret ngẫu nhiên chỉ trong bộ nhớ, database PostgreSQL dummy `127.0.0.1:1`; `BaseDatabaseWrapper.ensure_connection` bị chặn **trước Django setup**. Không đọc URL production, không kết nối database hoặc fallback SQLite, không tải/huấn luyện mô hình.

Kết quả: **7 static files copied, 14 post-processed**; system check không lỗi. Xác minh manifest, URL `{% static %}`, tệp thật và giải gzip khớp byte cho cả bảy tài nguyên:

| Nguồn | Tên đóng gói |
|---|---|
| `css/app.css` | `css/app.db6242c78901.css` |
| `js/money.js` | `js/money.f8ad2307326e.js` |
| `js/quick-entry.js` | `js/quick-entry.7b921d3d69b2.js` |
| `js/transaction-form.js` | `js/transaction-form.93fd08bdff76.js` |
| `js/transaction-filters.js` | `js/transaction-filters.08166be8015f.js` |
| `js/form-feedback.js` | `js/form-feedback.23a41e39df0d.js` |
| `img/brand.svg` | `img/brand.749d6337c5ed.svg` |

Đã kiểm nội dung tiền/nhập nhanh mới trong static đã collect; không có database, model, CSV, credential hoặc Python trong output. Bằng chứng ngoài Git: `handoff-collectstatic.log`, `handoff-static-report.json`, cùng script/settings QA. Đây là kiểm đóng gói production trên **Windows**, chưa phải build Linux/Render hoặc kiểm UI online.

Mã ứng dụng không sửa thêm trong lần chốt, tận dụng kết quả **325 Django** và **30 JavaScript** đã đạt; **19 bài tiền/demo là tập con của 325**, không cộng thành 344. Collectstatic/system check là kiểm vận hành riêng, không cộng vào số bài hồi quy.

Đã xác minh tài khoản GitHub `thiennamm`, repository `thiennamm/khoa_luan_tai_chinh_ca_nhan` vẫn **Private**, nhánh `main`. Giữ remote/quyền truy cập; chỉ commit mã, kiểm thử và tài liệu đã rà, không force-push. SHA local/remote và trạng thái working tree được đối chiếu sau push, báo ở tin nhắn cuối. Không nhúng SHA của chính commit vào nội dung tệp.
