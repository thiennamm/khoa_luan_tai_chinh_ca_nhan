from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import groups
from .group_models import ExpenseGroup, GroupMember, GroupExpense, GroupShare, GroupSettlement, GroupWalletPosting
from .group_forms import OperationForm, GroupForm, InvitationForm, ExpenseForm, ShareForm, SettlementForm, PostingForm


def membership(request,pk,invited=False):
    return get_object_or_404(GroupMember.objects.select_related('group'),group_id=pk,user=request.user,
        status__in=['active','invited'] if invited else ['active'])


def submit(request, form, callback):
    if request.method != 'POST' or not form.is_valid():
        return None
    try:
        return callback()
    except ValidationError as exc:
        form.add_error(None,' '.join(exc.messages))
    except (IntegrityError,OperationalError):
        form.add_error(None,'Chưa xác nhận được kết quả. Hãy kiểm tra sổ nhóm trước khi gửi lại; không tự gửi lại thao tác tài chính.')


def action_page(request,form,title,notice,group=None):
    return render(request,'finance/groups/form.html',{'form':form,'title':title,'notice':notice,'group':group})


@login_required
@require_http_methods(['GET'])
@never_cache
def index(request):
    rows = GroupMember.objects.filter(user=request.user,status__in=['active','invited']).select_related('group').order_by('-pk')
    return render(request,'finance/groups/list.html',{'page_obj':Paginator(rows,20).get_page(request.GET.get('page'))})


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def create(request):
    form = GroupForm(request.POST if request.method=='POST' else None,initial={'operation_token':groups.issue(request.user,'create')})
    pk = submit(request,form,lambda:groups.create_group(request.user,form.cleaned_data['operation_token'],form.cleaned_data['name']))
    if pk: return redirect('finance:group_detail',pk=pk)
    return action_page(request,form,'Tạo nhóm','Chỉ chia sẻ các khoản được ghi trong nhóm, không chia sẻ toàn bộ sổ cá nhân.')


@login_required
@require_http_methods(['GET'])
@never_cache
def detail(request,pk):
    actor = membership(request,pk)
    states = groups.obligations(pk)
    mine = [row for row in states if row['share'].member_id==actor.pk]
    receivable = [row for row in states if row['share'].expense.payer_id==actor.pk]
    all_shares = GroupShare.objects.filter(expense__group_id=pk,expense__voided=False,member=actor).select_related('expense').order_by('-expense__date','-pk')
    return render(request,'finance/groups/detail.html',{'group':actor.group,'actor':actor,
        'members':GroupMember.objects.filter(group_id=pk).select_related('user').order_by('pk'),
        'is_owner':actor.group.owner_id==request.user.pk,
        'expense_page':Paginator(GroupExpense.objects.filter(group_id=pk).select_related('payer__user'),20).get_page(request.GET.get('expenses')),
        'share_page':Paginator(all_shares,20).get_page(request.GET.get('shares')),
        'debt_page':Paginator(states,20).get_page(request.GET.get('debts')),
        'settlement_page':Paginator(GroupSettlement.objects.filter(group_id=pk).select_related('debtor__user','creditor__user'),20).get_page(request.GET.get('settlements')),
        'payable':sum((r['remaining'] for r in mine),Decimal(0)),
        'reserved':sum((r['reserved'] for r in mine),Decimal(0)),
        'receivable':sum((r['remaining'] for r in receivable),Decimal(0)),
        'now':timezone.now(),'pagination_query':request.GET.copy()})


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def invite(request,pk):
    actor=membership(request,pk)
    if actor.group.owner_id!=request.user.pk:
        from django.http import Http404
        raise Http404
    form=InvitationForm(request.POST if request.method=='POST' else None,initial={'operation_token':groups.issue(request.user,'invite',pk)})
    result=submit(request,form,lambda:groups.invite(request.user,form.cleaned_data['operation_token'],pk,form.cleaned_data['username']))
    if result: return redirect('finance:group_detail',pk=pk)
    return action_page(request,form,'Mời thành viên','Lời mời không tự thêm người đó vào nhóm. Người nhận phải chấp nhận.',actor.group)


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def member_action(request,pk,member_id,action):
    actor=membership(request,pk,invited=action in ['join','decline'])
    row=get_object_or_404(GroupMember,pk=member_id,group_id=pk)
    if (action in ['join','decline','leave'] and row.user_id!=request.user.pk) or (action=='revoke' and actor.group.owner_id!=request.user.pk):
        from django.http import Http404
        raise Http404
    titles={'join':'Chấp nhận lời mời','decline':'Từ chối lời mời','revoke':'Thu hồi lời mời','leave':'Rời nhóm'}
    if action not in titles:
        from django.http import Http404
        raise Http404
    form=OperationForm(request.POST if request.method=='POST' else None,initial={'operation_token':groups.issue(request.user,action,pk,member_id)})
    result=submit(request,form,lambda:groups.membership_action(request.user,form.cleaned_data['operation_token'],pk,member_id,action))
    if result: return redirect('finance:group_detail',pk=pk) if action in ['join','revoke'] else redirect('finance:group_list')
    return action_page(request,form,titles[action]+' — '+actor.group.name,
        'Không xóa lịch sử tài chính. Người rời nhóm mất quyền truy cập sổ nhóm; chủ nhóm không rời trong bản này.',
        actor.group if actor.status=='active' else None)


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def archive(request,pk):
    actor=membership(request,pk)
    if actor.group.owner_id!=request.user.pk:
        from django.http import Http404
        raise Http404
    form=OperationForm(request.POST if request.method=='POST' else None,initial={'operation_token':groups.issue(request.user,'archive',pk)})
    result=submit(request,form,lambda:groups.archive_group(request.user,form.cleaned_data['operation_token'],pk))
    if result: return redirect('finance:group_detail',pk=pk)
    return action_page(request,form,'Lưu trữ nhóm','Chỉ lưu trữ khi không còn nợ/phần chia/lời mời chờ. Lịch sử được giữ, nhóm chuyển sang chỉ đọc.',actor.group)


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def rename(request,pk):
    actor=membership(request,pk)
    if actor.group.owner_id!=request.user.pk:
        from django.http import Http404
        raise Http404
    form=GroupForm(request.POST if request.method=='POST' else None,
        initial={'operation_token':groups.issue(request.user,'rename',pk),'name':actor.group.name})
    result=submit(request,form,lambda:groups.rename_group(request.user,form.cleaned_data['operation_token'],pk,form.cleaned_data['name']))
    if result:return redirect('finance:group_detail',pk=pk)
    return action_page(request,form,'Đổi tên nhóm','Chỉ đổi tên hiển thị, không sửa khoản chi hoặc lịch sử đã chốt.',actor.group)


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def expense_create(request,pk):
    actor=membership(request,pk)
    form=ExpenseForm(request.POST if request.method=='POST' else None,group=actor.group,user=request.user,
        initial={'operation_token':groups.issue(request.user,'expense',pk),'date':groups.today()})
    preview=None
    if request.method=='POST' and form.is_valid():
        preview=[{'member':m,'amount':form.cleaned_data['parts'][m.pk]} for m in form.members if m.pk in form.cleaned_data['parts']]
        if request.POST.get('phase')=='confirm':
            if not form.cleaned_data['confirm']:
                form.add_error('confirm','Cần xác nhận đã kiểm khoản chi và phần chia.')
            else:
                result=submit(request,form,lambda:groups.create_expense(request.user,form.cleaned_data['operation_token'],pk,form.payload()))
                if result:return redirect('finance:group_expense',pk=pk,expense_id=result)
    return render(request,'finance/groups/form.html',{'form':form,'group':actor.group,'title':'Lập khoản chi nhóm',
        'notice':'Bạn là người đã trả toàn bộ tiền. Mỗi người phải tự xác nhận phần chia; chưa tự ghi chi hoặc trừ ví của ai. Khoản chốt không sửa tiền/ngày/phần chia.',
        'expense_form':True,'preview':preview})


@login_required
@require_http_methods(['GET'])
@never_cache
def expense_detail(request,pk,expense_id):
    actor=membership(request,pk)
    row=get_object_or_404(GroupExpense.objects.select_related('payer__user'),pk=expense_id,group_id=pk)
    shares=row.shares.select_related('member__user').order_by('member_id')
    return render(request,'finance/groups/expense.html',{'group':actor.group,'expense':row,'shares':shares,
        'is_payer':row.payer.user_id==request.user.pk,'posted':GroupWalletPosting.objects.filter(expense=row,user=request.user).exists()})


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def share_action(request,pk,share_id,action):
    actor=membership(request,pk)
    share=get_object_or_404(GroupShare.objects.select_related('expense'),pk=share_id,expense__group_id=pk,member__user=request.user)
    if action not in ['accept','reject']:
        from django.http import Http404
        raise Http404
    form_class=ShareForm if action=='accept' else OperationForm
    kwargs={'user':request.user,'share':share} if action=='accept' else {}
    form=form_class(request.POST if request.method=='POST' else None,
        initial={'operation_token':groups.issue(request.user,'share_'+action,pk,share_id)},**kwargs)
    result=submit(request,form,lambda:groups.respond_share(request.user,form.cleaned_data['operation_token'],pk,share_id,
        action=='accept',getattr(form.cleaned_data.get('category'),'pk',None)))
    if result:return redirect('finance:group_expense',pk=pk,expense_id=share.expense_id)
    from .money import format_vnd
    return action_page(request,form,'Xác nhận phần chi của tôi' if action=='accept' else 'Từ chối phần chia',
        f'{share.expense.description} · Phần của bạn {format_vnd(share.amount)} · {share.expense.date:%d/%m/%Y}. '
        'Chấp nhận sẽ ghi phần dương vào chi cá nhân, cập nhật ngân sách và hủy xác nhận coverage tháng liên quan. Không tự trừ ví; dòng tiền ghi riêng. Từ chối không tạo công nợ hay giao dịch.',actor.group)


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def expense_void(request,pk,expense_id):
    actor=membership(request,pk)
    get_object_or_404(GroupExpense,pk=expense_id,group_id=pk,payer__user=request.user)
    form=OperationForm(request.POST if request.method=='POST' else None,initial={'operation_token':groups.issue(request.user,'void',pk,expense_id)})
    result=submit(request,form,lambda:groups.void_expense(request.user,form.cleaned_data['operation_token'],pk,expense_id))
    if result:return redirect('finance:group_expense',pk=pk,expense_id=expense_id)
    return action_page(request,form,'Hủy khoản chưa ghi sổ','Chỉ hủy khi chưa có ai chấp nhận phần chia hoặc ghi ví. Sau mốc này chưa hỗ trợ sửa sai; không xóa lịch sử.',actor.group)


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def settlement_create(request,pk):
    actor=membership(request,pk)
    # Preserve only the actor's submitted share choices on a bound form. A
    # successful earlier POST may have reserved all debt; its receipt must still
    # reach the idempotent service. Fresh intents are revalidated under lock.
    submitted=set(request.POST.getlist('shares')) if request.method=='POST' else set()
    rows=[r for r in groups.obligations(pk) if r['share'].member_id==actor.pk
          and (r['available']>0 or str(r['share'].pk) in submitted)]
    form=SettlementForm(request.POST if request.method=='POST' else None,rows=rows,
        initial={'operation_token':groups.issue(request.user,'settlement',pk),'date':groups.today()})
    result=submit(request,form,lambda:groups.propose_settlement(request.user,form.cleaned_data['operation_token'],pk,
        {key:form.cleaned_data[key] for key in ['amount','date','shares']}))
    if result:return redirect('finance:group_settlement',pk=pk,settlement_id=result)
    return action_page(request,form,'Đề nghị ghi nhận hoàn trả','Chỉ ghi tiền đã thực sự hoàn. Đề nghị giữ chỗ nợ tối đa 7 ngày, chưa giảm nợ hoặc trừ ví. Người nhận phải xác nhận.',actor.group)


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def settlement_detail(request,pk,settlement_id,action=None):
    actor=membership(request,pk)
    row=get_object_or_404(GroupSettlement.objects.select_related('debtor__user','creditor__user'),pk=settlement_id,group_id=pk)
    if action is not None:
        if action not in ['confirm','reject','cancel']:
            from django.http import Http404
            raise Http404
        expected=row.debtor_id if action=='cancel' else row.creditor_id
        if actor.pk!=expected:
            from django.http import Http404
            raise Http404
        form=OperationForm(request.POST if request.method=='POST' else None,
            initial={'operation_token':groups.issue(request.user,'settlement_'+action,pk,settlement_id)})
        result=submit(request,form,lambda:groups.settlement_action(request.user,form.cleaned_data['operation_token'],pk,settlement_id,action))
        if result:return redirect('finance:group_settlement',pk=pk,settlement_id=settlement_id)
        return action_page(request,form,{'confirm':'Xác nhận đã nhận tiền','reject':'Từ chối đề nghị','cancel':'Hủy đề nghị'}[action],
            'Xác nhận chỉ khi đã nhận đủ tiền/ngày được nêu. Sau xác nhận chưa hỗ trợ sửa hoặc đảo hoàn trả. Không tạo thu–chi lần nữa; mỗi bên tự gắn ví riêng.',actor.group)
    if request.method=='POST':
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['GET'])
    side='pay' if row.debtor_id==actor.pk else 'receive' if row.creditor_id==actor.pk else None
    return render(request,'finance/groups/settlement.html',{'group':actor.group,'record':row,'side':side,
        'pending':row.status=='pending' and row.expires_at>timezone.now(),
        'expired':row.status=='pending' and row.expires_at<=timezone.now(),
        'posted':GroupWalletPosting.objects.filter(settlement=row,user=request.user).exists(),
        'allocations':row.allocations.select_related('share__expense')})


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def posting(request,pk,source_id,side):
    actor=get_object_or_404(GroupMember.objects.select_related('group'),group_id=pk,user=request.user)
    if side=='bill':
        source=get_object_or_404(GroupExpense,pk=source_id,group_id=pk,payer__user=request.user,voided=False)
    elif side in ['pay','receive']:
        source=get_object_or_404(GroupSettlement,pk=source_id,group_id=pk,status='confirmed',
            **{'debtor__user' if side=='pay' else 'creditor__user':request.user})
    else:
        from django.http import Http404
        raise Http404
    form=PostingForm(request.POST if request.method=='POST' else None,user=request.user,
        initial={'operation_token':groups.issue(request.user,'post_'+side,pk,source_id)})
    result=submit(request,form,lambda:groups.post_wallet(request.user,form.cleaned_data['operation_token'],pk,source_id,side,form.cleaned_data['wallet'].pk))
    if result:return redirect('finance:group_posting_detail',posting_id=result)
    from .money import format_vnd
    notice=f"Dòng tiền {'vào' if side=='receive' else 'ra'} {format_vnd(source.amount)} ngày {source.date:%d/%m/%Y}. Chỉ tác động ví của bạn; không tạo thu/chi lần nữa. Bản này chưa hỗ trợ đổi ví hoặc đảo dòng tiền đã ghi."
    return action_page(request,form,'Ghi dòng tiền vào ví của tôi',notice,actor.group if actor.status=='active' else None)


@login_required
@require_http_methods(['GET'])
@never_cache
def unassigned(request):
    return render(request,'finance/groups/unassigned.html',{'page_obj':Paginator(groups.unassigned_entries(request.user),20).get_page(request.GET.get('page'))})


@login_required
@require_http_methods(['GET'])
@never_cache
def posting_detail(request,posting_id):
    row=get_object_or_404(GroupWalletPosting.objects.select_related('wallet','expense','settlement'),pk=posting_id,user=request.user,wallet__user=request.user)
    return render(request,'finance/groups/posting.html',{'posting':row})
