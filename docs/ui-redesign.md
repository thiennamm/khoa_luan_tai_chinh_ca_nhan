# TASK 17A — Thiết kế lại giao diện Sổ Thu Chi

Thực hiện ngày **24–25/10/2026**, giờ Việt Nam, trên dự án chính `D:\KHÓA LUẬN TỐT NGHIỆP`. Các lượt đầu hoàn thành bản local để xem trước; đợt **chốt bàn giao 25/10/2026** được người dùng cho phép commit/push main sau rà soát. Xem kết quả chốt dưới đây; các ghi chú “chưa commit/push” ở những lượt trước là trạng thái tại thời điểm kiểm tra đó.

## Khảo sát và phương án đã triển khai

Đã đọc template, CSS/JavaScript dùng chung, trang tổng quan, thống kê, giao dịch, ngân sách, định kỳ, dự báo, phản hồi ML, tài khoản và các tài liệu UI trước đó (`ui-polish.md`, `predeployment-ui.md`). Đã chụp bản cũ bằng SQLite QA riêng trước khi sửa.

Bản cũ có menu dài ít phân nhóm; các phần thống kê xếp dọc khiến người dùng cuộn nhiều; nhiều khối trắng có trọng lượng tương đương; bảng giao dịch khó quét trên điện thoại. CSS tích lũy nhiều lớp ghi đè làm khó giữ cùng một hệ khoảng cách. Phương án mới giữ nhận diện xanh đậm, dùng phân cấp bằng số liệu, nền theo ngữ nghĩa và bố cục hai cột thay vì tăng số khung trang trí.

| Thành phần | Thiết kế đã thực hiện |
|---|---|
| Nhận diện | Xanh đậm `#123f36`, nền sáng `#f3f6f5`, màu thu xanh, chi đỏ đất, cảnh báo vàng; chữ hệ thống Segoe UI/system-ui, không font/CDN ngoài |
| Điều hướng | Tổng quan riêng; các nhóm Ghi chép, Kế hoạch, Cá nhân. Trang đang mở có nền sáng và `aria-current`; lịch sử dự báo cũng đánh dấu Dự báo. Mobile dùng menu HTML `details/summary`, mở/đóng được không cần JS |
| Icon | Một bộ SVG nét thống nhất tự vẽ trong template dùng chung, favicon SVG local; icon trang trí ẩn với công nghệ hỗ trợ, luôn có chữ cho thao tác |
| Tổng quan | Tiêu đề/bộ chọn tháng gọn, nút Thêm giao dịch rõ; ba thẻ thu/chi/chênh lệch; biểu đồ thời gian và cơ cấu chi đặt cạnh nhau trên desktop; ngân sách và khoản định kỳ gọn phía dưới; lối tắt Dự báo; giao dịch gần đây |
| Số liệu/biểu đồ | Dùng nguyên các giá trị và tỷ lệ do dịch vụ hiện có tổng hợp. Đơn vị VND và chú giải thu/chi rõ; bảng đầy đủ trong phần mở rộng HTML. Không tạo tăng/giảm giả, chia cho zero hoặc đổi định nghĩa chênh lệch thu–chi |
| Ngân sách/định kỳ | Tiến độ kèm chữ trong/vượt hạn mức, tiền thực tế vẫn phản ánh phần vượt. Coverage chưa xác nhận luôn thấy. Khoản định kỳ ghi rõ dự kiến, ngày, trạng thái và Ghi nhận; không cộng khoản dự kiến vào tổng |
| Giao dịch | Bộ lọc và CSV nằm trong mục riêng; giữ lỗi bộ lọc tự mở. Bảng desktop, các dòng gọn trên mobile; danh mục/mô tả dài không đẩy rộng toàn trang |
| Biểu mẫu/ML | Hệ trường, lỗi, nút chính/phụ/xóa thống nhất; bố cục nhập giao dịch hai cột desktop, một cột mobile. Gợi ý vẫn là phần tùy chọn, cảnh báo cần kiểm tra nằm ngay điểm sử dụng. Giữ nguyên Apply chủ động, vô hiệu gợi ý cũ, lưu thủ công và thông báo đang gửi/chống bấm lặp hiện có |
| Các trang khác | CSS chung áp dụng cho Ngân sách, Định kỳ, Dự báo/lịch sử, Phản hồi ML, Coverage, Danh mục, Tài khoản, CSV; đăng nhập/đăng ký cùng nhận diện xanh đậm |
| Khả năng tiếp cận | Giữ label, lỗi theo trường, skip link, focus rõ, chữ và màu cùng diễn đạt trạng thái. Chuyển động vào trang 0,18 giây; tắt animation/transition theo `prefers-reduced-motion`. Bảng rộng cuộn trong vùng riêng |

Không thay đổi Python nghiệp vụ, schema, chính sách ngày/tiền, quyền sở hữu, thuật toán, hai model, dependency hoặc các kết quả thí nghiệm. JavaScript hiện có được giữ nguyên. Không bổ sung tỷ lệ chắc chắn ML hoặc tự tính dự báo khi mở trang. Nội dung tài chính và bảng HTML đọc được khi JavaScript tắt; ML vẫn cần JS như trước.

## Tệp thay đổi

- `static/css/app.css`: thay CSS tích lũy bằng hệ giao diện có biến màu, khoảng cách và các nhóm thành phần; responsive chung.
- `static/img/brand.svg` (mới): favicon local.
- `templates/includes/icon.html` (mới): bộ SVG dùng chung.
- `templates/base.html`, `templates/includes/navigation.html`: khung trang, thương hiệu, điều hướng, tài khoản; phiên bản CSS cuối là `17a.3`.
- `templates/finance/dashboard.html`, `templates/finance/includes/financial_statistics.html`, `templates/finance/includes/budget_summary.html`: bố cục tổng quan, biểu đồ/bảng mở rộng, ngân sách/định kỳ và lối tắt.
- `templates/includes/transaction_table.html`, `templates/finance/transaction_list.html`, `templates/finance/category_list.html`: trình bày danh sách và công cụ.
- `templates/registration/login.html`, `templates/registration/signup.html`: nhận diện và SVG.
- `docs/ui-redesign.md`: biên bản này.
- `finance/views.py`: thêm cờ chỉ đọc `has_transactions` từ queryset thuộc tài khoản để chọn lời dẫn trống; không đổi điều kiện lọc, phân trang hoặc tính tổng.
- `finance/test_transaction_filters.py`, `finance/test_statistics.py`: kiểm trạng thái trống/phân quyền và lời giải thích zero/coverage.
- `finance/statistics.py`: thêm metadata nhãn/đơn vị cho trục biểu đồ từ cùng giá trị cực đại đang dùng; không đổi tổng tiền hoặc chiều cao cột.

Tổng cộng cuối **18 tệp**, gồm 15 tệp sửa và 3 tệp mới. Không có migration, thay đổi `.gitignore`, JS hay kiểm thử chỉ để kiểm tên class CSS.

## Môi trường QA và bảo vệ dữ liệu

Thư mục riêng: **`D:\SAO LUU KHOA LUAN\qa-17a-20261024`**. SQLite `qa.sqlite3` được tạo/migrate mới, không sao tài khoản hay giao dịch thật. Settings, khóa phiên, cookie và thông tin đăng nhập QA riêng; máy chủ tại **http://127.0.0.1:8017/**. Middleware chỉ trong cấu hình QA chèn nhãn vàng **“QA · Dữ liệu mô phỏng, không phải tài khoản thật”**; không đưa nhãn hoặc tài khoản QA vào mã sản phẩm. Có thể tự đăng ký tài khoản thử mới tại cổng QA; không dùng thông tin đăng nhập thật. Máy chủ QA được giữ chạy khi bàn giao, chỉ nghe loopback.

Runtime QA dùng Python 3.13 có sẵn tại `D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe` để tải hai model với bộ thư viện tương thích đã có. Đây chỉ là dùng lại runtime; cấu hình QA17 **ghi đè rõ database sang SQLite QA**, không dùng settings/kết nối PostgreSQL của QA16E. Không cài gói, dùng launcher can thiệp DLL hoặc thay runtime của dự án chính.

Fixture cố định để so ảnh trước/sau:

- Tháng 10/2026: thu **22.000.000**, chi **8.735.000**, chênh lệch **13.265.000 VND**; sáu nhóm chi, có tên dài và tên chứa `< >`, `&` để kiểm hiển thị/escaping.
- Ngân sách tổng **8.000.000**, vượt **735.000 VND**; ngân sách Ăn uống **1.000.000**, đã chi **870.000**. Coverage tháng hiện tại giữ Chưa xác nhận.
- Sáu tháng 04–09/2026 được giả lập đầy đủ riêng trong QA; tháng 06 bằng zero. Tạo sẵn một kết quả TB3 **3.600.000 VND** bằng dịch vụ hiện có để kiểm trình bày. Không fit Ridge hoặc huấn luyện lại ML; không chạy lại các thí nghiệm.
- Hai khoản định kỳ dự kiến, tháng trống 01/2026 và tài khoản trống để kiểm trạng thái ít/chưa có dữ liệu.
- Một tài khoản QA thao tác riêng được đăng ký qua trình duyệt: tạo danh mục, lưu hai giao dịch VI/EN, tạo ngân sách, ghi nhận định kỳ và nhập một dòng CSV. Các thao tác này không thay fixture dùng chụp trước/sau.

Các tệp `protected-*.json` xác minh **SHA-256 SQLite thật và cả hai model EN/VI không đổi**. Git diff không có thay đổi model/form, logic tổng hợp/dự báo, dependency hay thí nghiệm; view chỉ thêm cờ cho trạng thái trống, thống kê chỉ thêm metadata trình bày trục. Không truy cập production. Mọi tệp QA, CSV xuất, thông tin đăng nhập và ảnh đều ở ngoài Git.

## Bằng chứng trình duyệt và ảnh

Thử bằng **Microsoft Edge/Chromium headless qua Playwright**, viewport chính xác **1280×900** và **390×844 CSS px**, locale tiếng Việt, múi giờ Asia/Ho_Chi_Minh. Đây là thao tác/render trình duyệt thật, không suy ra từ HTTP 200; chưa thử thiết bị điện thoại vật lý.

Có **12 ảnh trước** (6 trang × 2 kích thước), **26 ảnh sau** (13 trang × 2 kích thước), thêm ảnh menu, bảng mở rộng, tháng trống, lỗi form, Apply, CSV và định kỳ. Các ảnh `draft-*` chỉ là bản rà giữa chừng; dùng `before-*` và `after-*` khi đối chiếu. Ảnh sau được chụp khi animation kết thúc (`animations: disabled`), không chỉnh sửa ảnh hoặc tạo ảnh giao diện giả.

Tất cả đường dẫn dưới đây cùng nằm trong thư mục QA trên:

| Nội dung | Trước desktop / mobile | Sau desktop / mobile |
|---|---|---|
| Tổng quan | `before-desktop-dashboard.png` / `before-mobile-dashboard.png` | `after-desktop-dashboard.png` / `after-mobile-dashboard.png` |
| Giao dịch | `before-desktop-transactions.png` / `before-mobile-transactions.png` | `after-desktop-transactions.png` / `after-mobile-transactions.png` |
| Thêm giao dịch | `before-desktop-form.png` / `before-mobile-form.png` | `after-desktop-form.png` / `after-mobile-form.png` |
| Ngân sách | `before-desktop-budget.png` / `before-mobile-budget.png` | `after-desktop-budget.png` / `after-mobile-budget.png` |
| Dự báo | `before-desktop-forecast.png` / `before-mobile-forecast.png` | `after-desktop-forecast.png` / `after-mobile-forecast.png` |
| Đăng nhập | `before-desktop-login.png` / `before-mobile-login.png` | `after-desktop-login.png` / `after-mobile-login.png` |

Các trang sau bổ sung: `after-{desktop|mobile}-{history|feedback|categories|recurring|account|coverage|signup}.png`. Ảnh một viewport Tổng quan: `after-desktop-dashboard-viewport.png`, `after-mobile-dashboard-viewport.png`.

Liên kết xem nhanh:

- [Tổng quan trước desktop](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/before-desktop-dashboard.png>) · [sau desktop](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/after-desktop-dashboard-viewport.png>) · [sau mobile](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/after-mobile-dashboard-viewport.png>).
- [Form mobile](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/after-mobile-form.png>) · [Apply VI](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/after-mobile-vi-applied.png>) · [Apply EN](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/after-mobile-en-applied.png>).
- [Ngân sách mobile](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/after-mobile-budget.png>) · [Menu mobile](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/after-mobile-menu-open.png>) · [Định kỳ xác nhận](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/after-mobile-recurring-confirm.png>).

`browser-pages.json` ghi 26 trang/kích thước; **không có scrollWidth lớn hơn chiều rộng viewport**, không có `pageerror` trong các lượt rà. Tổng quan full-page giảm từ **3659 → 2192 px** desktop và **7502 → 3798 px** mobile trên cùng fixture; bảng chi tiết vẫn mở được khi cần, không xóa số liệu.

`evidence-manifest.json` ghi kích thước và SHA-256 của **61 tệp bằng chứng lượt đầu** (ảnh trước/sau, no-JS, thống kê QA và log), không đưa credential vào manifest. Đợt tinh chỉnh có `refine-evidence-manifest.json` riêng, giữ nguyên ảnh cũ. Rà các tệp chuẩn bị bàn giao: không có tệp dữ liệu/model/bí mật, không có mẫu credential trong nội dung; kết hợp với việc đọc diff thủ công, không chỉ dựa vào quét chuỗi.

## Các thao tác đã thử

Chi tiết máy đọc được trong `browser-checks.json`; **16 nhóm kiểm tra hành vi đạt**:

1. Chọn so sánh 12 tháng, mở bảng thu/chi và cơ cấu; cộng số tiền các danh mục bằng **8.735.000 VND**, khớp tổng chi. Tháng hiện tại ghi chưa kết thúc.
2. Tháng trống không sinh cơ cấu/tỷ trọng giả, không NaN/Infinity; có hành động thêm giao dịch.
3. Menu mobile mở bằng click, đóng bằng Space; trang Lịch sử dự báo vẫn đánh dấu Dự báo.
4. Chuyển chế độ khoảng ngày/tháng, ngày sai hiện lỗi và mở bộ lọc; phối hợp mô tả + loại + khoảng ngày trả đúng một kết quả fixture.
5. Context thật sự tắt JavaScript: đăng nhập bằng Enter, menu, bảng mở rộng và nhập tay vẫn hoạt động; submit danh mục sai loại được server báo lỗi, giữ số tiền đã nhập. Không tạo giao dịch lỗi.
6. Đăng ký qua UI chuyển đến đăng nhập, không tự đăng nhập; đăng nhập tài khoản QA mới, thấy trạng thái trống và tạo danh mục được.
7. Mobile: gợi ý VI không tự gán danh mục; bấm Apply rồi chủ động Lưu mới tạo giao dịch.
8. Mobile: gợi ý EN, đổi chế độ làm mất gợi ý cũ; yêu cầu lại, Apply và Lưu; trang Phản hồi có hai dòng đã lưu. Không hiển thị score thành phần trăm.
9. Tạo ngân sách 200.000 sau hai khoản chi tổng 230.000: hiển thị vượt 30.000.
10. Tạo quy tắc 60.000 đến hạn ngày 31; form ghi nhận mặc định ngày Việt Nam 25/10/2026, cho sửa thực tế thành 65.000; lưu thành giao dịch ngày thực tế.
11. Ngân sách chỉ tăng chi sau ghi nhận thực tế: 295.000, vượt 95.000; khoản dự kiến không bị cộng thêm.
12. CSV BOM qua tải lên → xem trước → xác nhận một dòng; tải bản xuất qua nút trình duyệt, nhận BOM và nội dung QA đã nhập (bốn giao dịch của tài khoản thử).
13. Tài khoản mới thiếu lịch sử: trang Dự báo chỉ rõ 07–09/2026 cần xác nhận, không tạo ước tính.
14. Bật prefers-reduced-motion trong context: animation của main bằng `none`.
15. Skip link nhận focus bàn phím, outline hiển thị.
16. Desktop: yêu cầu gợi ý VI và bấm Apply; trước click danh mục vẫn trống, sau click mới đổi. Không lưu giao dịch này.

Có rà trực quan các ảnh đã chụp. Đo tương phản trên **124 phần chữ đang hiển thị ở Tổng quan desktop**: không thấy dưới 4,5:1 với chữ thường hoặc 3:1 với chữ lớn theo phép đo màu nền kết hợp. Đây là kiểm tra có phạm vi, **không phải chứng nhận WCAG toàn website**; chưa kiểm screen reader hoặc mọi trạng thái màu/trình duyệt.

## Kiểm thử mã và kiểm tra cuối

| Kiểm tra | Kết quả |
|---|---|
| Django `test finance --noinput --settings=qa17_test_settings` | Lượt đầu **303/303 đạt**, 89,333 giây; sau tinh chỉnh **305/305 đạt**, 104,841 giây; SQLite test riêng được hủy sau chạy |
| Node `--test scripts/test_form_feedback.js scripts/test_transaction_suggestion.js` | **17/17 đạt**; bao gồm trạng thái gửi/chống gửi lặp, Apply và vô hiệu gợi ý cũ |
| Django `check` với settings QA17 | Không lỗi, 0 cảnh báo bị tắt |
| `makemigrations --check --dry-run` | No changes detected |
| `git diff --check` | Không lỗi whitespace; Git chỉ nhắc chuẩn hóa LF/CRLF trên một số template |
| Bảo vệ dữ liệu | Hash database thật và model EN/VI không đổi; diff gồm template/CSS/SVG, cờ hiển thị ở view, kiểm thử và tài liệu; không chứa credential, dump hoặc dữ liệu QA |

Lần chạy test đầu dùng cookie riêng `qa17_csrf` của website QA khiến sáu test bảo mật cũ (đọc tên mặc định `csrftoken`) lỗi. Đã tách **settings kiểm thử** dùng tên cookie mặc định Django, vẫn giữ database test QA; chạy lại đầy đủ đạt 303. Không sửa test, bỏ kiểm CSRF hay thay cấu hình website để làm đạt. Log cuối: `django-tests-final.log`; log đầu giữ lại để truy vết.

## Tinh chỉnh theo yêu cầu trước bàn giao — 25/10/2026

### Thay đổi cuối

- Thu gọn khoảng cách giữa thương hiệu, nhóm menu và các mục; giữ vùng bấm ít nhất 44px và `overflow-y:auto` cho sidebar. Không cho các phần tử sidebar co lại che nội dung khi thiếu chiều cao.
- Trang Giao dịch bỏ câu dẫn lặp; bộ lọc và Nhập / xuất CSV nằm cùng hàng khi đóng, phần mở dùng đủ chiều rộng. Rút gọn điều kiện đang áp dụng bằng cách không nhắc lại Loại/Danh mục “Tất cả”; vẫn hiện đầy đủ điều kiện người dùng chọn. Thẻ tổng và tiêu đề danh sách gọn hơn, số tiền phổ biến không bị đẩy ký hiệu đồng xuống dòng trên mobile; ngày desktop giữ cùng một dòng.
- Tách **“Bạn chưa ghi nhận giao dịch nào”** (không có giao dịch nào của chính tài khoản, có nút thêm đầu tiên/chuẩn bị danh mục) và **“Không có kết quả phù hợp”** (đã có giao dịch, nhưng không khớp tháng hoặc điều kiện; có nút xóa bộ lọc và hướng dẫn chọn lại thời gian). Bộ lọc sai vẫn báo lỗi, không chuyển thành trạng thái trống hợp lệ. Chưa có bản ghi không được diễn đạt là chưa phát sinh chi tiêu thực tế.
- Chú thích ngay dưới biểu đồ giải thích rõ zero là tổng đã ghi, không chứng minh không chi tiền; tháng chưa xác nhận/chưa đầy đủ vẫn là dữ liệu chưa biết cho dự báo. Bảng mở rộng giữ trạng thái từng tháng. Không đổi dữ liệu thống kê hoặc dịch vụ dự báo.

### Fixture và ảnh bổ sung

Chỉ tạo thêm tài khoản **mô phỏng QA riêng**, không thay fixture cũ, tài khoản trống hoặc SQLite thật. Sao các bản ghi **đã là mô phỏng** từ fixture QA, thêm 24 khoản chi cố định với mô tả dài; tháng 10/2026 có **32 giao dịch**, phân trang **20 + 12**. Tổng thu **22.000.000**, chi **9.665.000**, chênh lệch **12.335.000 VND**; ngân sách tổng **8.000.000**, vượt **1.665.000**. Danh mục có tên dài/ký tự đặc biệt; lịch sử nhiều tháng có thu và chi. Không tính dự báo hay chạy mô hình khi tạo fixture này.

Ảnh cuối nằm cùng thư mục QA, ưu tiên các tên **`refined-*`** cho bản bàn giao:

| Ảnh | Desktop 1280×900 | Mobile 390×844 |
|---|---|---|
| Tổng quan, đầy đủ biểu đồ/cơ cấu/ngân sách | `refined-desktop-dashboard.png` | `refined-mobile-dashboard.png` |
| Tổng quan, một viewport | `refined-desktop-dashboard-viewport.png` | `refined-mobile-dashboard-viewport.png` |
| Giao dịch có 32 kết quả, trang đầu | `refined-desktop-transactions.png` | `refined-mobile-transactions.png` |
| Giao dịch, một viewport | `refined-desktop-transactions-viewport.png` | `refined-mobile-transactions-viewport.png` |
| Trang 2 có 12 dòng | `refined-desktop-transactions-page2.png` | `refined-mobile-transactions-page2.png` |
| Không khớp bộ lọc | `refined-desktop-no-match.png` | `refined-mobile-no-match.png` |
| Bảng 12 tháng, zero/chưa xác nhận và zero/đầy đủ | `refined-desktop-unknown-and-confirmed-zero.png` | `refined-mobile-unknown-and-confirmed-zero.png` |

Thêm `refined-mobile-no-transactions.png` cho tài khoản trống và `refined-mobile-filter-pagination.png` cho bộ lọc có trang 2/công cụ CSV mở. Ảnh giữ nhãn QA, không chỉnh ảnh hoặc đưa vào repository.

[Tổng quan cuối desktop](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/refined-desktop-dashboard.png>) · [Tổng quan cuối mobile](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/refined-mobile-dashboard.png>) · [Giao dịch desktop](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/refined-desktop-transactions-viewport.png>) · [Giao dịch mobile](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/refined-mobile-transactions-viewport.png>).

### Kết quả xác minh bổ sung

`refine-browser-checks.json` ghi **9 nhóm kiểm tra đạt**, không có lỗi JavaScript được ghi nhận trong các trang này:

- Hai viewport: 20 dòng trang đầu và 12 dòng trang sau; link giữ tháng. Mô tả dài được rút gọn trong danh sách, mở chi tiết đọc đủ nội dung.
- Ở 1280×900: đủ **9 mục điều hướng** trong viewport, mục cuối kết thúc khoảng y=643px. Cửa sổ cao 500px: sidebar cuộn được tới mục cuối. Mô phỏng chữ menu tăng từ 14 lên 28px bằng CSS trong trình duyệt: nội dung cao hơn vùng hiển thị và vẫn cuộn tới cuối; đây là mô phỏng chữ lớn, chưa phải kiểm tất cả chế độ zoom hệ điều hành/trình duyệt.
- Tổng quan/danh sách ở 1280×900 và 390×844 không tràn ngang toàn trang. Dòng đầu danh sách bắt đầu khoảng y=512px desktop và y=544px mobile, có tính nhãn QA riêng. Bảng/biểu đồ rộng vẫn cuộn trong vùng riêng.
- Cả hai viewport: không khớp mô tả hiện đúng lời dẫn bộ lọc. Tài khoản QA trống có nút thêm đầu tiên, không bị dữ liệu tài khoản khác làm đổi trạng thái.
- Cả hai viewport: chú thích zero hiển thị; bảng 12 tháng có 11/2025 chi đã ghi bằng 0/Chưa xác nhận và 06/2026 chi bằng 0/Đã xác nhận đầy đủ. Kiểm thử dịch vụ giữ `forecast_expense` tương ứng `None`/`Decimal('0')`, không nối hoặc điền thiếu tháng cho dự báo.
- Mobile: lọc mô tả + loại cho 24 dòng, sang trang 2 còn 4 dòng, tham số vẫn giữ; công cụ CSV mở và nút xuất vẫn truy cập được.

Kiểm thử liên quan: **23/23 đạt** (`refine-tests.log`). Hồi quy sau chỉnh template cuối: **305/305 đạt** (`refine-regression.log`, gồm hai test mới); system check không lỗi. Tái sử dụng kết quả **17/17 JavaScript** đã đạt vì không sửa JS. `check`, `makemigrations --check --dry-run` và rà diff/bí mật được thực hiện cuối; không tạo migration, commit hoặc push.

## Chốt QA trục giá trị và ảnh gửi bàn giao — 25/10/2026

Biểu đồ thu–chi có trục dọc với năm mốc **0%, 25%, 50%, 75%, 100% của cùng cực đại đang dùng cho cột**. Đây là vị trí chia trục, không hiển thị thành tỷ lệ thu/chi. Nhãn giá trị dùng Decimal, rút gọn theo VND/nghìn/triệu/tỷ/nghìn tỷ/triệu tỷ VND, làm tròn tối đa hai chữ số thập phân với dấu phẩy; bảng vẫn giữ tiền VND đầy đủ. Không đổi thang cột hoặc tổng hợp nghiệp vụ. Chuỗi hoàn toàn zero chỉ hiện một nhãn **0**, không tự đặt hạn mức dương giả.

Trục nằm ngoài vùng cuộn ngang, cố định rộng 40px trên mobile; giá trị/đơn vị không bị cắt. Vạch lưới cùng chiều cao/thang trục (220px desktop, 200px mobile). Bảng thay thế và chú thích về zero/coverage vẫn có thể đọc/mở không cần JS.

Fixture vẫn là tài khoản mô phỏng `qa17_refine` trong SQLite QA17, không tạo thêm giao dịch hoặc tính lại mô hình. Với cực đại 22.000.000 VND, nhãn là **22; 16,5; 11; 5,5; 0**, đơn vị **triệu VND**. Kiểm trình duyệt ở 1280×900 và 390×844 xác nhận tất cả nhãn/đơn vị nằm trong vùng hiển thị, trục không chạy theo khi cuộn cột, bảng sáu tháng mở được, chú thích dữ liệu chưa biết còn rõ, không tràn ngang toàn trang. Không có pageerror được ghi nhận. Bằng chứng: `axis-browser-checks.json`.

Ảnh mới nhất, cùng thư mục `D:\SAO LUU KHOA LUAN\qa-17a-20261024`:

- [Tổng quan desktop đầy đủ: nhiều tháng, nhiều danh mục và ngân sách](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/final-desktop-dashboard.png>).
- [Tổng quan mobile đầy đủ](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/final-mobile-dashboard.png>).
- [Trục/biểu đồ desktop 1280×900](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/final-desktop-chart-axis.png>) · [trục/biểu đồ mobile 390×844](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/final-mobile-chart-axis.png>).
- [Giao dịch mobile 390×844 có phân trang](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/final-mobile-filtered-pagination-390x844.png>): lọc 24 dòng mô phỏng, trang 2/2 có bốn dòng; ảnh chụp cuộn xuống để thấy phân trang, không cắt/ghép ảnh.
- [Giao dịch mobile trang 2/2 của toàn bộ 32 dòng](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/final-mobile-transactions-pagination-390x844.png>) · [ảnh toàn trang](<D:/SAO LUU KHOA LUAN/qa-17a-20261024/final-mobile-transactions-page2-full.png>).

Kiểm thử sau thay đổi trục: **26/26 đạt**, gồm thống kê, bộ lọc và ba test mới về nhãn, zero, ranh giới đơn vị/giá trị Decimal lớn (`axis-tests.log`). Django system check không lỗi; `git diff --check` không lỗi. Không chạy lại toàn bộ 305 bài hoặc 17 bài JS vì phần thay đổi chỉ là metadata/HTML/CSS của biểu đồ, JS không đổi; kết quả hồi quy trước được giữ rõ theo từng lượt. Không tự gọi là đã chạy 308 bài hồi quy.

`axis-evidence-manifest.json` ghi hash ảnh/bằng chứng mới; `protected-axis.json` đối chiếu database thật/hai model với hash ban đầu. Rà diff không đưa bí mật/dữ liệu QA vào Git. **Chưa commit/push/deploy**; không sửa database thật hoặc production.

## Chốt bàn giao và đóng gói production QA — 25/10/2026

### Đối chiếu 32 giao dịch với 24 giao dịch trong ảnh

Đã chạy lại **hai view thực tế** Tổng quan/danh sách qua RequestFactory, cùng tài khoản mô phỏng trong SQLite QA17. Theo dõi câu lệnh database: **28 truy vấn, tất cả SELECT**, không sửa dữ liệu. Đối chiếu kết quả với điều kiện đã dùng chụp ảnh:

| Trang/điều kiện | Tổng kết quả | Tổng thu VND | Tổng chi VND | Chênh lệch VND | Phân trang |
|---|---:|---:|---:|---:|---|
| Tổng quan `month=2026-10&span=6` | 32 | 22.000.000 | 9.665.000 | 12.335.000 | Hiện 5 giao dịch gần đây |
| Danh sách `month=2026-10`, không lọc thêm | 32 | 22.000.000 | 9.665.000 | 12.335.000 | 20 + 12 |
| Ảnh mobile: `month=2026-10&q=QA mô phỏng&kind=expense&page=2` | 24 | 0 | 930.000 | −930.000 | 20 + 4 |

**Kết luận: chênh lệch do bộ lọc, không phải mất giao dịch hoặc lỗi đếm.** Bộ lọc mô tả + loại Chi loại ra **2 khoản thu tổng 22.000.000 VND và 6 khoản chi tổng 8.735.000 VND**. Kiểm tra: `24 + 2 + 6 = 32`, `930.000 + 8.735.000 = 9.665.000`. Bỏ điều kiện mô tả/loại cho kết quả giống Tổng quan. Ảnh phân trang mobile được cuộn xuống nên điều kiện lọc ở đầu trang không nằm trong khung ảnh; không được so sánh 24 với tổng tháng mà bỏ qua bộ lọc.

Nguồn bằng chứng ngoài Git: `handoff-reconciliation.json`; script QA `handoff_reconcile.py` kiểm tra cứng đúng SQLite QA, gọi view hiện có và xác nhận số dòng/tổng tiền. **Không cần sửa mã chức năng** từ đợt trục biểu đồ. Tái sử dụng kết quả 305 bài hồi quy, 26 bài liên quan sau trục và 17 bài JS đã ghi rõ ở trên; không chạy lại chỉ để lặp kết quả.

### Collectstatic với cấu hình Render QA

Đã chạy `collectstatic --noinput` bằng runtime Python 3.13 hiện có, **import profile `config.render` thực tế**, `DEBUG=False`, `CompressedManifestStaticFilesStorage` của WhiteNoise. Settings QA riêng nằm **ngoài repository**; chỉ đổi đầu ra static/model sang thư mục QA. Host/origin là domain QA `.invalid`; secret ngẫu nhiên trong bộ nhớ, kết nối khai báo là PostgreSQL dummy `127.0.0.1:1`. Có chốt `BaseDatabaseWrapper.ensure_connection` từ chối **mọi** kết nối database trước khi setup/chạy lệnh. Không dùng URL production hoặc fallback SQLite.

Kết quả: **5 static files copied, 10 post-processed**, system check không lỗi. Kiểm manifest ánh xạ đủ năm tài nguyên, `{% static %}` trả URL tên hash, tệp có thật; giải nén gzip so khớp byte với bản gốc, không chỉ kiểm tên tệp.

| Tài nguyên | Tên được đóng gói |
|---|---|
| CSS | `css/app.9b48273d83db.css` |
| Icon thương hiệu | `img/brand.749d6337c5ed.svg` |
| Phản hồi gửi form | `js/form-feedback.23a41e39df0d.js` |
| Bộ lọc giao dịch | `js/transaction-filters.08166be8015f.js` |
| Biểu mẫu/Apply ML | `js/transaction-form.93fd08bdff76.js` |

SVG giao diện còn lại là inline từ `templates/includes/icon.html`, được theo dõi như template, không cần file tải từ CDN. Thư mục collectstatic chỉ có tài nguyên công khai và manifest, không có model, CSV, database, tệp Python hoặc credential.

Bằng chứng ngoài Git: `handoff-static-report.json`, `handoff-collectstatic.log`, `static-production-handoff/`; cấu hình và script chạy QA nằm cùng thư mục QA17. Đây là **kiểm đóng gói trên Windows**, chưa phải build Linux/Render thực tế hoặc xác minh giao diện online sau push.

### Rà phạm vi và mốc mã

- Rà 18 tệp TASK17A: thay đổi template/CSS/SVG; Python chỉ thêm cờ chỉ đọc phục vụ trạng thái trống và metadata nhãn trục. Không đổi query lọc/sắp xếp/tính tổng hiện có, schema/migration, luồng lưu/CSRF/phân quyền, coverage, ngân sách, dự báo, model, dependency hoặc thí nghiệm.
- Không đưa settings QA, script QA, tài khoản/dữ liệu QA, ảnh, static đã build, database hoặc credential vào commit; chúng ở ngoài repository. Chỉ tài liệu mô tả số tổng của dữ liệu mô phỏng được chia sẻ.
- Xác minh GitHub bằng đăng nhập hiện có: tài khoản `thiennamm`, repository `thiennamm/khoa_luan_tai_chinh_ca_nhan` **Private**, nhánh mặc định main; remote không đổi. Không in token hoặc thông tin kết nối riêng tư.
- Mốc bàn giao dùng tiêu đề commit **`Redesign So Thu Chi UI and document QA handoff`** trên main. SHA sau push và đối chiếu local/remote được báo trong tin nhắn bàn giao; không nhúng SHA của chính commit vào nội dung để tránh tự tham chiếu.
- Giữ nguyên giới hạn: Edge/Chromium headless desktop/mobile viewport đã thử; **chưa kiểm Safari/Firefox, điện thoại vật lý hoặc screen reader**. Không coi push/Render Live là bằng chứng UI online đã đạt; không truy cập database production trong bàn giao này.

## Giới hạn và cách xem bản local

- Mở **http://127.0.0.1:8017/** để xem bản QA; ảnh có dữ liệu mô phỏng sẵn trong thư mục bằng chứng. Không dùng cổng production/bản phục hồi làm đích QA.
- Sau khi dừng server QA, có thể chạy lại bằng `& 'D:\POSTGRESQL QA\application-16e-20261024\.venv\Scripts\python.exe' 'D:\SAO LUU KHOA LUAN\qa-17a-20261024\serve.py'`. Đây là lệnh QA riêng, không thay lệnh chạy local trong README.
- Chưa kiểm Safari/Firefox, screen reader, điện thoại vật lý, production hoặc PostgreSQL trong task UI này. Không gọi các thao tác smoke UI là kiểm thử mọi tình huống nghiệp vụ; hồi quy Django/JS là bằng chứng bổ sung riêng.
- Trang demo vẫn dùng CSS chung; không chạy lại demo Ridge hoặc thí nghiệm để tạo ảnh, không thay kết quả nghiên cứu. Kết quả dự báo fixture chỉ là TB3 trong QA.
- Không phát hiện vấn đề nghiệp vụ cần sửa trong phạm vi đã thử. Không thay dữ liệu thật, áp migration, huấn luyện hoặc deploy; chờ người dùng xem bản local trước khi quyết định đưa lên Render.
