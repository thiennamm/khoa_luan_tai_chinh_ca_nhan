from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .category_defaults import DEFAULTS, preview, add_defaults


class DefaultSelectionForm(forms.Form):
    items = forms.MultipleChoiceField(choices=[(item.key,item.name) for item in DEFAULTS],
        error_messages={'required':'Chọn ít nhất một danh mục muốn thêm.',
            'invalid_choice':'Danh sách lựa chọn không hợp lệ. Chỉ chọn các mục đang hiển thị.'})


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def category_defaults(request):
    form=DefaultSelectionForm(request.POST if request.method=='POST' else None)
    result=None
    if request.method=='POST' and form.is_valid():
        try:
            result=add_defaults(request.user,form.cleaned_data['items'])
        except (ValidationError,IntegrityError):
            form.add_error(None,'Chưa thêm danh mục. Dữ liệu có thể vừa thay đổi; hãy tải lại trang và kiểm tra.')
        except OperationalError as exc:
            if 'locked' not in str(exc).lower():raise
            form.add_error(None,'Tài khoản đang xử lý thao tác khác. Hãy thử lại; danh mục đã tồn tại sẽ được bỏ qua.')
    rows=preview(request.user,form.data.getlist('items') if form.is_bound else ())
    return render(request,'finance/category_defaults.html',{'form':form,'rows':rows,'result':result,
        'available_count':sum(not row['exists'] for row in rows)})
