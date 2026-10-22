from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from .account_forms import UsernameChangeForm, VietnamesePasswordChangeForm


@sensitive_post_parameters()
@login_required
@require_http_methods(['GET', 'POST'])
@never_cache
def account(request):
    action = request.POST.get('action') if request.method == 'POST' else None
    username_form = UsernameChangeForm(request.user,
        request.POST if action == 'username' else None, prefix='username')
    password_form = VietnamesePasswordChangeForm(request.user,
        request.POST if action == 'password' else None, prefix='password')
    if action == 'username' and username_form.is_valid():
        try:
            username_form.save()
        except IntegrityError:
            username_form.add_error('new_username', 'Tên đăng nhập này đã được sử dụng. Vui lòng chọn tên khác.')
        except ValidationError as exc:
            username_form.add_error(None, exc)
        except OperationalError:
            username_form.add_error(None, 'Chưa thể cập nhật lúc này. Vui lòng thử lại.')
        else:
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Đã đổi tên đăng nhập. Lần đăng nhập sau hãy dùng tên mới.')
            return redirect('account')
    elif action == 'password' and password_form.is_valid():
        password_form.save()
        update_session_auth_hash(request, password_form.user)
        messages.success(request, 'Đã đổi mật khẩu. Phiên hiện tại được giữ; các phiên khác sẽ hết hiệu lực khi được kiểm tra lại.')
        return redirect('account')
    elif request.method == 'POST' and action not in ('username', 'password'):
        messages.error(request, 'Thao tác không hợp lệ. Vui lòng dùng đúng biểu mẫu.')
        return render(request, 'registration/account.html',
            {'username_form': username_form, 'password_form': password_form}, status=400)
    return render(request, 'registration/account.html',
        {'username_form': username_form, 'password_form': password_form})
