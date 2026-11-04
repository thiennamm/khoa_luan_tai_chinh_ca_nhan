# Bảo trì WSGI cho Render Free

Ngày chuẩn bị: 04/11/2026. Người dùng chọn phương án miễn phí sau khi Dashboard báo Maintenance Mode yêu cầu Upgrade. Không nâng gói. Đây là lớp vận hành tùy chọn; không thay schema, dependency, mô hình ML hoặc nghiệp vụ tài chính.

## Cách hoạt động

`scripts/serve_render.py` bọc ứng dụng bằng `scripts/maintenance_gate.py` trước khi đưa cho Waitress. Thiếu `DJANGO_MAINTENANCE_MODE` tương đương `0`: trả nguyên ứng dụng WSGI cũ, local runserver không dùng cổng này. Chỉ chấp nhận mode `0`/`1`.

Mode `1` yêu cầu `DJANGO_MAINTENANCE_BYPASS_TOKEN` ngẫu nhiên 32–128 ký tự URL-safe, không phải placeholder. Thiếu/sai cấu hình làm start thất bại; không in giá trị khóa. Mọi request công khai bị chặn trước Django/session/database, trả trang bảo trì không có biểu mẫu. GET/HEAD đúng `/tai-khoan/dang-nhap/` trả cùng trang tĩnh với HTTP 200 để giữ health check hiện có; POST vào đó vẫn bị chặn 503. Các đường khác trả 503, HEAD không có body. Không dùng health 200 làm bằng chứng đăng nhập đã hoạt động.

Chỉ request có header **X-SoThuChi-Maintenance-Key** khớp chính xác khóa mới đi tiếp. So sánh constant-time; khóa không đi qua URL/cookie/query string, không nằm trong HTML. Header được lấy khỏi environ trước khi chuyển cho Django để giảm nguy cơ lọt vào META/log lỗi. Các cơ chế CSRF, cookie, phân quyền và xác thực của Django vẫn áp dụng. Đây là quyền kiểm tra vận hành, không phải khóa tài khoản hoặc cơ chế bỏ CSRF. Không dùng khóa để ghi giao dịch thử vào tài khoản thật.

Trang bảo trì không cần CDN/JS, có no-store/private, nosniff, DENY frame và CSP hạn chế. Cache reverse proxy/health không được dùng để suy dữ liệu còn mới. Không thêm URL/tài khoản demo hoặc số tài chính giả vào production.

## Trình tự fail-closed khi đang chạy bản cũ

1. Chuẩn bị/kiểm thử mã, commit riêng trước. **Chưa push** cho tới khi đã ngừng ghi và backup mới đạt.
2. Dashboard Web Service → Suspend Service, không suspend database. Xác nhận Suspended, public không truy cập ứng dụng và không còn thao tác ghi đang chạy. Không sửa dữ liệu qua client khác trong cửa sổ bảo trì.
3. Trong lúc service dừng, đặt env `DJANGO_MAINTENANCE_MODE=1` và khóa ngẫu nhiên qua clipboard riêng/Environment secret; không gửi chat, không ghi Git/log. Health Check Path phải là `/tai-khoan/dang-nhap/`. Đổi **Start Command tạm** thành **`bash deploy/render-maintenance-start.sh`**. Không thay Build Command.
4. Wrapper Start này **không có ở các commit cũ**; nếu Resume nhầm bản cũ, nó không thể chạy web cũ. Trên bản mới, wrapper kiểm mode=1/khóa hợp lệ trước khi gọi start cũ, migrate và serve. Chưa có cổng thì không phục vụ công khai. Không dùng Start Command bình thường trong giai đoạn này.
5. Tạo backup PostgreSQL mới bằng script đã kiểm, xác minh archive/hash và giữ nguyên bản đã restore thử. Lưu mốc đối chiếu dữ liệu ngoài Git; ngừng ghi vẫn được giữ bằng Suspend.
6. Push main bình thường. Theo dõi Auto-Deploy On Commit. Nếu Render chưa start vì Suspended thì Resume/Deploy latest commit khi sẵn sàng; wrapper nêu trên giữ fail-closed nếu nền tảng thử start commit cũ. Không reverse/restore tự động khi build/start lỗi.
7. Kiểm công khai đang nhận trang bảo trì, đúng commit Live và migration/checks trong log. Dùng header khóa qua helper riêng để kiểm HTTP đăng nhập/read-only các trang hiện có. Đối chiếu dữ liệu bằng kết nối PostgreSQL read-only ép đúng đích; không in dữ liệu cá nhân. Mọi lần kiểm khóa/credential dùng prompt ẩn và file tạm bảo vệ ngoài Git.
8. Sau khi đạt: đổi Start Command lại **`bash deploy/render-start.sh` trong khi mode vẫn 1**, đợi deploy cùng mã trong bảo trì đạt. Sau đó đặt mode=0 (hoặc bỏ mode) và bỏ khóa tạm trong cùng lần Save Environment; việc này khởi động lại cùng commit và mở trang. Xác minh Live/HTTP và quyền giữ nguyên. Nếu có lỗi, giữ hoặc bật lại bảo trì, đánh giá trước khi xử lý.
9. Đóng connection/cửa sổ kiểm tra, logout phiên vận hành, xóa khóa/URL/credential tạm khỏi máy và env Render. Không xóa backup. Git commit báo cáo sau cùng cần được cân nhắc Auto-Deploy; không tự push báo cáo chỉ để làm working tree sạch.

Render Free không có chế độ bảo trì hạ tầng như gói trả phí. Suspend ban đầu cần thiết vì mã đang Live chưa có cổng WSGI. Cổng chỉ ngăn request qua Web Service; không chặn người quản trị/ứng dụng khác ghi trực tiếp PostgreSQL, nên cửa sổ bảo trì phải bao gồm các tác nhân đó. Khóa tạm phải giữ kín và bị gỡ sau khi mở lại.

## Kiểm chứng

Nhóm QA riêng gồm gate/start/deploy config/diagnostics và ví: 65 bài, 63 đạt + 2 skip (hai bài đồng thời PostgreSQL không đổi, đã có bằng chứng đạt ở đợt 204 PostgreSQL). Có 11 bài mới về gate: default-off, chặn mọi phương thức ghi, health tĩnh, HEAD, key đúng/sai/Unicode/quá dài, header bị gỡ, giữ CSRF/cookie, lỗi cấu hình không lộ khóa, start guard và Waitress thật sự nhận gate. Không cộng số lượt này vào các tổng 484/204 cũ.

Không chạy full suite hoặc thí nghiệm ML. Kết quả Bash/HTTP QA và triển khai thực tế được bổ sung theo biên bản TASK 23A; tài liệu này không tự khẳng định deploy đã hoàn tất hoặc mọi UI đạt. Nguồn giới hạn native Maintenance Mode: https://render.com/docs/maintenance-mode .

Đã kiểm Bash syntax và 7 điểm HTTP/Start bằng Waitress QA loopback không database: public GET/POST bị chặn, health tĩnh 200, HEAD rỗng, key đúng đi tiếp nhưng không lọt vào Django, bản thiếu module không start, Start bảo trì không nhận mode=0. Listener QA đã đóng. System check và makemigrations dry-run QA đạt; chưa phải kết quả production. Bằng chứng ngoài Git: `D:\SAO LUU KHOA LUAN\wallet0015-deployment-20261104-d8a43c8c`.
