"""Display guidance from vi-authored-v1 §3 and classification-data-audit §4.

These are operational scopes, not a guarantee about EN/VI predictions.
Never infer or restrict a mapping from a user's category name.
"""
from .classification_labels import LABELS

MAPPING_LABEL = 'Liên kết với nhãn mô hình — tùy chọn'
MAPPING_HELP = ('Chỉ chọn khi ý nghĩa phù hợp. Không tìm thấy nhãn phù hợp, hãy để Chưa ánh xạ. '
                'Bạn vẫn có thể dùng danh mục để ghi giao dịch.')
RENAME_HELP = ('Tên mới cũng xuất hiện trên các giao dịch đang thuộc danh mục này. '
               'Đổi tên không tự chuyển giao dịch sang danh mục khác.')

SCOPES = {
    'Education': ('Giáo dục', 'Học, đào tạo, thi và vật dụng nêu rõ mục đích học; sách giải trí thuộc Entertainment.'),
    'Entertainment': ('Giải trí', 'Vé, hoạt động giải trí và nội dung mua lẻ; ăn uống thuộc Restaurants, chuyến nghỉ thuộc Travel, gói gia hạn thuộc Subscription.'),
    'Fees': ('Phí', 'Phí ngân hàng, thanh toán, thủ tục và tiền phạt riêng; không gom học phí, viện phí hay thuế chỉ vì tên có chữ phí.'),
    'Groceries': ('Thực phẩm và hàng thiết yếu', 'Nguyên liệu, thực phẩm dự trữ, thức ăn thú nuôi và đồ tiêu hao vệ sinh nhà; món chế biến để ăn ngay thuộc Restaurants.'),
    'Healthcare': ('Y tế', 'Khám, điều trị, phòng bệnh và thiết bị y tế có mục đích rõ; làm đẹp thường ngày thuộc Personal Care.'),
    'Income': ('Thu nhập', 'Khoản nhận có nguồn thu rõ như lương, kinh doanh, lãi hoặc trợ cấp không hoàn trả; không suy từ tiền vào, hoàn tiền hay tự chuyển vốn.'),
    'Insurance': ('Bảo hiểm', 'Mua, đóng hoặc gia hạn phí hợp đồng bảo hiểm; khoản bồi hoàn không mặc nhiên là Income hay phí bảo hiểm.'),
    'Mortgage': ('Vay nhà ở', 'Trả gốc/lãi nêu rõ vay mua, xây hoặc sửa nhà ở; trả góp chưa rõ mục đích chưa đủ để chọn nhãn này.'),
    'Personal Care': ('Chăm sóc cá nhân', 'Vệ sinh, làm đẹp và chăm sóc cơ thể không điều trị; chỉ định điều trị thuộc Healthcare, vệ sinh nhà thuộc Groceries.'),
    'Rent': ('Tiền thuê không gian', 'Thuê nơi ở, văn phòng hoặc kho thường xuyên; lưu trú kỳ nghỉ thuộc Travel, tiền cọc có thể hoàn chưa coi là Rent.'),
    'Restaurants': ('Ăn uống chế biến sẵn', 'Món đã nấu, đồ uống pha sẵn và phục vụ bữa ăn, kể cả giao về; nguyên liệu tự nấu thuộc Groceries, không phải mọi hoạt động giải trí.'),
    'Shopping': ('Mua sắm', 'Quần áo, phụ kiện, đồ dùng chung và đồ bền; ưu tiên mục đích rõ như y tế, học tập hoặc chăm sóc cá nhân hơn nơi bán.'),
    'Subscription': ('Thuê bao và hội viên', 'Quyền dùng nội dung, công cụ số hoặc hội viên gia hạn; không gom học phí, bảo hiểm, tiền thuê, điện hay mạng cơ bản chỉ vì định kỳ.'),
    'Transfer': ('Điều chuyển tiền — cần xem lại', 'Điều chuyển vốn cùng chủ hoặc đổi nơi giữ tiền, chưa tiêu dùng. Không liên kết vào loại thu/chi; chữ chuyển khoản riêng lẻ chưa đủ kết luận.'),
    'Transportation': ('Di chuyển thường ngày', 'Đi lại thường ngày và vận hành, sửa chữa, an toàn phương tiện; dịch vụ trong chuyến nghỉ có mục đích rõ thuộc Travel.'),
    'Travel': ('Du lịch', 'Chuyến nghỉ, lưu trú ngắn ngày và dịch vụ cấu thành chuyến đi; bữa ăn riêng thuộc Restaurants, bảo hiểm riêng thuộc Insurance; không phải giải trí nói chung.'),
    'Utilities': ('Điện nước và tiện ích', 'Điện, nước, nhiên liệu bếp, viễn thông cơ bản và vận hành nơi ở; công cụ số gia hạn thuộc Subscription, tiền thuê thuộc Rent.'),
}


def label_guide():
    return [{'code': code, 'name': SCOPES[code][0], 'scope': SCOPES[code][1]}
            for code in LABELS]


def mapping_peers(user, exclude_pk=None):
    from .models import Category
    rows = Category.objects.filter(user=user).exclude(canonical_label='')
    if exclude_pk:
        rows = rows.exclude(pk=exclude_pk)
    peers = {}
    for kind, label, name in rows.values_list('kind', 'canonical_label', 'name'):
        peers.setdefault(kind, {}).setdefault(label, []).append(name)
    return peers
