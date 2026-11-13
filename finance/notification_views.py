from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .notification_models import GroupNotification


@login_required
@require_GET
@never_cache
def inbox(request):
    rows = GroupNotification.objects.filter(recipient=request.user)
    return render(request, 'finance/notifications.html', {
        'page_obj': Paginator(rows, 20).get_page(request.GET.get('page')),
    })


def invitation_unavailable(request, row, version):
    status = row.get_status_display() if str(row.invitation_version) == str(version) else 'Đã được thay thế'
    messages.info(request, f'Lời mời không còn mở được. Trạng thái: {status}.')
    return redirect('finance:group_list')


@login_required
@require_POST
@never_cache
def open_notification(request, pk):
    notice = get_object_or_404(
        GroupNotification.objects.filter(recipient=request.user).select_related(
            'invitation__group', 'share__expense', 'share__member', 'settlement__creditor',
        ), pk=pk,
    )
    # Keep the original read timestamp when opened again or from two tabs.
    GroupNotification.objects.filter(pk=notice.pk, recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
    if notice.invitation_id:
        row = notice.invitation
        if row.user_id == request.user.pk:
            if row.invitation_version == notice.invitation_version and row.status in ['invited', 'active']:
                url = reverse('finance:group_member_action', args=[row.group_id, row.pk, 'join'])
                return redirect(f'{url}?lan={notice.invitation_version}')
            return invitation_unavailable(request, row, notice.invitation_version)
    elif notice.share_id:
        row = notice.share
        if row.member.user_id == request.user.pk and row.member.status == 'active' and row.member.group_id == row.expense.group_id:
            return redirect('finance:group_expense', pk=row.expense.group_id, expense_id=row.expense_id)
    else:
        row = notice.settlement
        if row.creditor.user_id == request.user.pk and row.creditor.status == 'active' and row.creditor.group_id == row.group_id:
            return redirect('finance:group_settlement', pk=row.group_id, settlement_id=row.pk)
    messages.info(request, 'Nội dung thông báo không còn truy cập được.')
    return redirect('finance:group_list')
