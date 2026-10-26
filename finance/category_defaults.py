"""Opt-in configuration only. No transactions, inference, or automatic signup hooks."""
import unicodedata
from dataclasses import dataclass
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Category, Transaction, Budget
from .classification_labels import compatible_kind
from .category_locks import lock_catalog


@dataclass(frozen=True)
class DefaultCategory:
    key: str
    name: str
    kind: str
    label: str
    explanation: str


DEFAULTS = (
    DefaultCategory('dining','Ăn uống','expense','',
        'Nhóm rộng có thể gồm ăn ngoài và thực phẩm mua về; chưa chọn Restaurants hoặc Groceries thay bạn.'),
    DefaultCategory('groceries','Đi chợ & siêu thị','expense','Groceries',
        'Dùng cho nguyên liệu, thực phẩm và hàng tiêu hao vệ sinh nhà; đồ bền hoặc quần áo chọn nhóm khác.'),
    DefaultCategory('transport','Di chuyển','expense','Transportation',
        'Đi lại thường ngày và vận hành phương tiện; chuyến du lịch có mục đích riêng.'),
    DefaultCategory('housing','Nhà ở','expense','',
        'Có thể gồm thuê nhà, vay mua nhà hoặc tiện ích; chưa chọn Rent, Mortgage hay Utilities thay bạn.'),
    DefaultCategory('bills','Hóa đơn','expense','',
        'Hóa đơn có nhiều mục đích: điện nước, thuê bao, bảo hiểm…; không gom tất cả vào Utilities.'),
    DefaultCategory('health','Sức khỏe','expense','Healthcare',
        'Khám, điều trị, phòng bệnh và thiết bị y tế; làm đẹp thông thường không thuộc phạm vi này.'),
    DefaultCategory('education','Giáo dục','expense','Education',
        'Học tập, đào tạo, thi và vật dụng nêu rõ mục đích học.'),
    DefaultCategory('shopping','Mua sắm','expense','Shopping',
        'Quần áo, phụ kiện và đồ dùng chung; các mục đích chuyên biệt như y tế, học tập chọn riêng.'),
    DefaultCategory('entertainment','Giải trí','expense','Entertainment',
        'Vé và hoạt động giải trí, nội dung mua lẻ; thuê bao gia hạn có nhãn khác.'),
    DefaultCategory('salary','Lương','income','Income',
        'Khoản thu xác định từ công việc; không suy thu nhập chỉ từ chiều tiền vào.'),
    DefaultCategory('other_income','Thu nhập khác','income','',
        'Cần xác minh nguồn và bản chất khoản nhận trước khi chọn nhãn; không mặc định hoàn tiền hay chuyển khoản là Income.'),
)
BY_KEY = {item.key:item for item in DEFAULTS}
assert len(BY_KEY)==len(DEFAULTS)
assert all(not item.label or compatible_kind(item.label)==item.kind for item in DEFAULTS)


def normalized_name(value):
    # Preserve accents/punctuation: no translation, accent stripping or '&'/'và' guessing.
    return unicodedata.normalize('NFC',' '.join(unicodedata.normalize('NFC',value).casefold().split()))


def existing_keys(user):
    return {(kind,normalized_name(name)) for kind,name in Category.objects.filter(user=user).values_list('kind','name')}


def preview(user, selected=()):
    existing=existing_keys(user)
    return [{'item':item,'exists':(item.kind,normalized_name(item.name)) in existing,'selected':item.key in selected}
        for item in DEFAULTS]


@transaction.atomic
def add_defaults(user, selected):
    if not selected or any(key not in BY_KEY for key in selected):
        raise ValidationError('Chỉ chọn các danh mục trong bộ mẫu được cho phép.')
    lock_catalog(user.pk)
    existing=existing_keys(user)
    created=[];skipped=[]
    for item in DEFAULTS:
        if item.key not in selected:
            continue
        key=(item.kind,normalized_name(item.name))
        if key in existing:
            skipped.append(item)
            continue
        Category.objects.create(user=user,name=item.name,kind=item.kind,canonical_label=item.label)
        existing.add(key)
        created.append(item)
    return {'created':created,'skipped':skipped}


def getting_started(user):
    categories=Category.objects.filter(user=user).exists()
    transactions=Transaction.objects.filter(user=user).exists()
    return {'categories':categories,'transactions':transactions,'budget':Budget.objects.filter(user=user).exists(),
        'completed':int(categories)+int(transactions),'complete':categories and transactions}
