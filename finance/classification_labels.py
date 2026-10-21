"""Nhãn của thí nghiệm 06B; ánh xạ do từng người dùng chủ động chọn."""

LABELS = {
    'Education': 'Giáo dục',
    'Entertainment': 'Giải trí',
    'Fees': 'Phí',
    'Groceries': 'Thực phẩm, hàng thiết yếu',
    'Healthcare': 'Y tế',
    'Income': 'Thu nhập',
    'Insurance': 'Bảo hiểm',
    'Mortgage': 'Khoản vay mua nhà',
    'Personal Care': 'Chăm sóc cá nhân',
    'Rent': 'Tiền thuê',
    'Restaurants': 'Ăn tại nhà hàng',
    'Shopping': 'Mua sắm',
    'Subscription': 'Thuê bao',
    'Transfer': 'Chuyển khoản — cần xem lại',
    'Transportation': 'Đi lại',
    'Travel': 'Du lịch',
    'Utilities': 'Điện, nước và tiện ích',
}

# Transfer không có ánh xạ thu/chi. Chuỗi mã giữ đúng nhãn đã đánh giá.
MAPPING_CHOICES = [(code, f'{label} ({code})') for code, label in LABELS.items() if code != 'Transfer']


def compatible_kind(label):
    if label == 'Transfer' or label not in LABELS:
        return None
    return 'income' if label == 'Income' else 'expense'
