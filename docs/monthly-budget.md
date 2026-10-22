# TASK 13A — Ngân sách tháng và cảnh báo trong website

Thực hiện **21/10/2026** trên `D:\KHÓA LUẬN TỐT NGHIỆP`, Python của `.venv` dự án chính, cổng **8001**. Không sửa hay migrate bản phục hồi TASK 12B ở cổng 8003. Đã đọc models, forms, services/statistics, quyền sở hữu, CRUD danh mục/giao dịch và lịch sử ghi chép trước khi sửa.

## Sử dụng

1. Vào **Ngân sách**, chọn tháng (mặc định tháng hiện tại).
2. Chọn **Tạo ngân sách**. Để trống danh mục để đặt ngân sách tổng; chọn danh mục chi của mình để đặt ngân sách danh mục. Nhập số nguyên VND dương, tối đa 15 chữ số.
3. Sửa bằng biểu mẫu có POST/CSRF. Xóa mở trang xác nhận trước, chỉ POST mới xóa. Ngân sách của người khác trả 404 cho GET/POST sửa/xóa; không nhận user_id đích từ form.
4. Xem hạn mức, chi đã ghi nhận, còn lại hoặc vượt và trạng thái cảnh báo. Tổng quan có tóm tắt cho chính tháng đang chọn, liên kết tới trang ngân sách cùng tháng.

Không tự tạo ngân sách mặc định, tự sao ngân sách tháng khác hoặc thay giao dịch/coverage. Tổng và danh mục là hai góc theo dõi **riêng**, không cộng hạn mức, không phân bổ tự động. Chưa gửi email/push. Các tháng không có giao dịch hiển thị đã ghi nhận 0 nhưng vẫn giữ trạng thái lịch sử thực tế; không xác nhận đầy đủ hoặc đổi dữ liệu dự báo thành 0.

## Tính toán

`monthly_budgets(user, month)` chỉ đọc `expense` của đúng tài khoản, đúng tháng, danh mục thuộc tài khoản. Dùng cùng các bản ghi giao dịch như thống kê; cộng từng Decimal trong Python để tránh tổng SQLite bị chuyển qua float khi số lớn. Ngân sách danh mục nhóm theo ID, không theo tên. Thu nhập và dự báo không được cộng vào số đã chi.

Tổng chi được tính một lượt; ngân sách tổng dùng tổng đó, mỗi ngân sách danh mục dùng phần chi của chính danh mục. Không cộng thêm các phần danh mục vào tổng lần nữa. Khi sửa, xóa hoặc nhập giao dịch, lần xem tiếp theo tính từ dữ liệu hiện có, không giữ cache chi theo ngân sách.

| So sánh chính xác | Trạng thái |
|---|---|
| Đã chi < 80% hạn mức | Trong hạn mức |
| 80% ≤ đã chi < 100% | Gần chạm hạn mức |
| Đã chi = 100% | Đã chạm hạn mức |
| Đã chi > 100% | Vượt hạn mức |

So sánh Decimal trước khi làm tròn. Tỷ lệ hiển thị làm tròn hai chữ số (ROUND_HALF_UP); sát biên, số hiển thị có thể làm tròn đến 80/100 trong khi nhãn vẫn theo tỷ lệ chưa làm tròn. Phần vẽ `min(100, tỷ lệ)`; số tiền và tỷ lệ chữ vẫn giữ mức vượt, không cắt số đã chi. Thanh chỉ là minh họa; số liệu/trạng thái bằng chữ đọc được không cần JavaScript và không chỉ phân biệt bằng màu.

“Còn lại” là hạn mức trừ chi **đã ghi nhận**, không phải tiền mặt/số dư ngân hàng hoặc cam kết còn có thể chi. Trang ngân sách và Tổng quan giữ rõ trạng thái lịch sử ghi chép; không che trạng thái chưa xác nhận/chưa đầy đủ.

## Model và ràng buộc

`Budget`: user, tháng (ngày đầu tháng), category nullable, DecimalField amount `(max_digits=15, decimal_places=0)`.

- `category=NULL`: unique theo user/tháng, dùng partial unique constraint để xử lý NULL đúng trên SQLite.
- Có category: unique theo user/tháng/category. Category phải thuộc user và có loại expense.
- CHECK database: tháng ngày 1, tiền nguyên trong `[1, 999999999999999]`; model/form cũng validation.
- ModelForm chỉ cho chọn danh mục chi của request.user, kiểm trùng sớm; model kiểm lại và database chặn cạnh tranh. View bắt IntegrityError/ValidationError khi lưu và hiển thị lỗi chung, không in chi tiết database.
- SQLite CHECK không tham chiếu được bảng khác: migration `0008` dùng ba trigger để chặn ngân sách liên kết sai chủ/loại ở cả INSERT/UPDATE, và chặn đổi loại/chủ của danh mục đang có ngân sách. Các kiểm thử dùng bulk_create/queryset.update xác minh không thể vượt qua ràng buộc bằng cách bỏ model.clean(). Trigger này dành cho SQLite; cần chuyển đổi/kiểm lại nếu đổi engine sau này.
- FK category dùng PROTECT: không xóa danh mục làm mất ngân sách. Model Category.clean cũng chặn đổi loại/chủ khi có ngân sách, kể cả chưa có giao dịch. Có thể đổi tên; có thể sửa ngân sách sang danh mục khác hoặc xóa ngân sách rõ ràng trước khi xử lý danh mục. Form/thông báo/trang xác nhận danh mục nêu rõ cả giao dịch và ngân sách liên quan.
- Budget CRUD không gọi reset coverage, bump forecast version hoặc sửa ForecastResult. Các đường ghi giao dịch và logic dự báo vẫn như cũ.

## Sao lưu và migration dự án chính

Trước migration đã tạo mới:

```text
D:\SAO LUU KHOA LUAN\before-budget-13a-20261021-221041
```

`database.sqlite3` dùng **SQLite backup API từ nguồn chỉ đọc**, kiểm `integrity_check=ok`. `manifest.json`/`manifest.sha256` kiểm hash/kích thước snapshot và manifest bảo toàn artifact; không ghi đè bản cũ. Xác minh SQLite gốc vẫn đúng hash của lúc backup ngay trước migration. Log server đặt riêng ngoài snapshot.

Áp dụng thành công trên dự án chính:

```powershell
Set-Location -LiteralPath 'D:\KHÓA LUẬN TỐT NGHIỆP'
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate --noinput
& '.\.venv\Scripts\python.exe' -X utf8 manage.py check
& '.\.venv\Scripts\python.exe' -X utf8 manage.py migrate --check
```

- `0007_budget`: tạo bảng và các CHECK/unique/FK; `0008_budget_category_guards`: tạo trigger, có reverse DROP trigger.
- So sánh snapshot: toàn bộ bản ghi cũ của 16 bảng giữ nguyên. Django thêm đúng **2 migration records, 1 content type và 4 permission** cho Budget; không đổi quyền gán cho người dùng/nhóm. Không coi metadata chuẩn Django là dữ liệu tài chính bị sửa.
- Bảng Budget của dự án chính vẫn **0 dòng** sau migration; không đưa dữ liệu QA vào dữ liệu thật. `integrity_check=ok`, `foreign_key_check` không lỗi; không còn migration chờ.
- **181 tệp** dữ liệu/artifact, mã phân loại/coverage/dự báo và requirements trong manifest bảo toàn giữ nguyên hash. Không huấn luyện, refit, chạy lại thí nghiệm hoặc thay model.
- Máy chủ chính khởi động lại tại `http://127.0.0.1:8001/`. Bản phục hồi 8003 được giữ nguyên.

Không phục hồi đè snapshot cũ trong lúc server đang chạy. Nếu cần rollback, dừng server, sao lưu trạng thái mới trước, chọn rõ khôi phục cả mã/schema tương ứng; rollback migration `0007` sẽ xóa ngân sách đã tạo sau đó. Task này không thực hiện rollback hoặc phục hồi đè.

## Kiểm thử

- **10 kiểm thử ngân sách đạt**, gồm nhiều subcase: account scope/CSRF, giả user_id, phạm vi danh mục, tiền sai, trùng ở form/DB, bỏ qua validation bằng bulk/update, chặn đổi/xóa danh mục, đổi tên hợp lệ, các mốc 80/100/vượt, tháng zero/trạng thái đầy đủ, đổi năm, sửa ngày/sửa tiền/xóa giao dịch cập nhật số đã chi, không đếm đôi tổng.
- CRUD ngân sách được đối chiếu trước/sau với transaction, coverage, ForecastDataVersion và một ForecastResult đã có: không thay đổi. Kiểm lỗi cạnh tranh bằng mô phỏng IntegrityError ở bước lưu để đảm bảo form báo lỗi, không thành công giả.
- **198/198 kiểm thử Django hồi quy đạt**; log thiếu/lỗi mô hình là các nhánh kiểm lỗi có chủ đích. `manage.py check` không vấn đề; `makemigrations --check --dry-run` không thay đổi thiếu; migrate --check đạt.

## Thử trình duyệt bằng SQLite QA

QA mới tại **`D:\SAO LUU KHOA LUAN\qa-13a-20261021-221511`**, cổng **8009**, settings/SQLite/cookie/secret riêng. Dùng code của dự án chính; không sao/đọc giao dịch thật. Tạo hai tài khoản QA; chỉ người đầu có giao dịch mô phỏng, danh mục chi/thu, người thứ hai có danh mục riêng. Mật khẩu ngẫu nhiên không đưa vào tài liệu.

| Luồng UI thực tế | Kết quả |
|---|---|
| Chưa có ngân sách | Có lời dẫn/nút tạo tổng và danh mục, đã ghi nhận 80.000 VND, lịch sử Chưa xác nhận |
| Tạo tổng | 100.000 VND, đã chi 80.000 → Gần chạm hạn mức, 80% |
| Tạo danh mục | 50.000 VND, đã chi 80.000 → Vượt 30.000, 160%, thanh vẽ 100% |
| Sửa ngân sách | Đổi tổng thành 80.000 → Đã chạm hạn mức, 100%, còn 0 |
| Sửa giao dịch QA | Đổi 80.000 thành 120.000 qua form giao dịch → tổng 150%/vượt 40.000; danh mục 240%/vượt 70.000; cả hai thanh dừng 100% |
| Trùng ngân sách | POST tạo thêm tổng cùng tháng nhận lỗi tiếng Việt, giữ form, không tạo bản thứ hai |
| Xóa | Đã mở trang xác nhận và hủy, không xóa bằng GET; POST xóa được kiểm tự động, chưa bấm xóa qua UI trong lần QA này |
| Đổi năm/tháng trống | Xem 01/2027: chưa có ngân sách, đã ghi nhận 0, không tự xác nhận lịch sử |
| Tổng quan | Tóm tắt đúng tháng: 120.000 đã ghi nhận, 150% tổng, vượt 40.000; danh mục riêng vượt 70.000; vẫn hiện Chưa xác nhận |

Đã đo DOM sau hiệu chỉnh tỷ lệ hiển thị của công cụ: **desktop 1280×900**, **mobile 390×844 CSS px**. Ảnh đầu khi công cụ chưa hiệu chỉnh không dùng làm bằng chứng kích thước chính xác. Các trang danh sách/form/tổng quan cuối không tràn ngang toàn trang; menu, nút, nhãn trường và thẻ ngân sách thao tác được. Chỉ là khung responsive cùng engine, chưa điện thoại thật/Safari hoặc kiểm toán accessibility toàn diện.

Ảnh và bằng chứng nằm ngoài Git trong thư mục QA:

- `desktop-near80.png`, `desktop-over-category.png`: luồng tạo/cảnh báo ban đầu, kích thước công cụ chưa hiệu chỉnh.
- `desktop-final.png`, `desktop-dashboard.png`: desktop đã hiệu chỉnh 1280×900.
- `mobile-final-exact.png`, `mobile-form-exact.png`, `mobile-dashboard-exact.png`: khung đã hiệu chỉnh 390×844.
- `mobile-reached100.png`, `mobile-after-transaction-edit.png`, `mobile-duplicate-error.png`: trạng thái/thao tác mobile ở chiều rộng 390, một số ảnh trước hiệu chỉnh chiều cao cuối có chiều cao 845.
- `mobile-delete-confirm.png`, `mobile-empty-new-year.png`: xác nhận xóa và tháng trống.
- `browser-evidence.json`: kích thước thực tế, nội dung card và thanh vẽ; `migration-preservation.json`: đối chiếu dữ liệu sau migration; `qa-manifest.json`: SHA-256 bằng chứng cố định.

Server QA được dừng, viewport trả mặc định sau kiểm tra. Dữ liệu/tài khoản QA không vào Git hoặc SQLite chính. Không có email, push, carry-over, quy tắc ngân sách dùng dự báo hoặc deployment trong task này.
