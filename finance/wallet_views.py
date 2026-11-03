from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import Wallet, WalletTransfer
from .wallet_forms import WalletForm, WalletHistoryForm, TransferForm
from . import wallets


@login_required
@require_http_methods(['GET'])
@never_cache
def wallet_list(request):
    context = wallets.balances(request.user)
    context['page_obj'] = Paginator(context['wallet_rows'],20).get_page(request.GET.get('page'))
    return render(request,'finance/wallet_list.html',context)


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def wallet_edit(request, pk=None):
    wallet = get_object_or_404(Wallet,pk=pk,user=request.user) if pk else None
    form = WalletForm(request.POST if request.method=='POST' else None,user=request.user,instance=wallet)
    if request.method=='POST' and form.is_valid():
        try:
            saved = form.save()
        except (ValidationError,IntegrityError,OperationalError):
            form.add_error(None,'Chưa lưu được ví. Kiểm tra tên trùng, mốc đã có nghiệp vụ hoặc thao tác đang xử lý.')
        else:
            messages.success(request,'Đã lưu ví. Số dư dựa trên mốc và ghi chép của bạn, không phải đối soát ngân hàng.')
            return redirect('finance:wallet_detail',pk=saved.pk)
    return render(request,'finance/wallet_form.html',{'form':form,'wallet':wallet})


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def wallet_status(request, pk):
    wallet = get_object_or_404(Wallet,pk=pk,user=request.user)
    class Confirm(forms.Form):
        action = forms.ChoiceField(choices=[('archive','Lưu trữ'),('reopen','Mở lại')],widget=forms.HiddenInput)
        confirm = forms.BooleanField(label='Tôi xác nhận thay đổi trạng thái ví này.')
    form = Confirm(request.POST if request.method=='POST' else None,initial={'action':'reopen' if wallet.archived else 'archive'})
    if request.method=='POST' and form.is_valid():
        try:
            wallet.archived = form.cleaned_data['action']=='archive'
            wallet.save(update_fields=['archived'])
        except (ValidationError,OperationalError):
            form.add_error(None,'Chưa đổi được trạng thái. Hãy tải lại trước khi thử lại.')
        else:
            return redirect('finance:wallet_detail',pk=wallet.pk)
    return render(request,'finance/wallet_status.html',{'form':form,'wallet':wallet})


@login_required
@require_http_methods(['GET'])
@never_cache
def wallet_detail(request, pk=None):
    wallet = get_object_or_404(Wallet,pk=pk,user=request.user) if pk else None
    form = WalletHistoryForm(request.GET)
    valid = form.is_valid()
    rows = wallets.history(request.user,wallet,form.cleaned_data.get('start'),form.cleaned_data.get('end')) if valid else []
    context = wallets.balances(request.user)
    context.update(wallet=wallet,form=form,filter_query=request.GET.copy(),today=wallets.today(),
                   page_obj=Paginator(rows,20).get_page(request.GET.get('page')))
    context['filter_query'].pop('page',None)
    context['filter_query'] = context['filter_query'].urlencode()
    context['item'] = next((r for r in context['wallet_rows'] if r['wallet'].pk==pk),None)
    return render(request,'finance/wallet_detail.html',context,status=200 if valid else 400)


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def transfer_create(request):
    form = TransferForm(request.POST if request.method=='POST' else None,user=request.user,
        initial={'operation_token':wallets.issue_transfer(request.user)})
    if request.method=='POST' and form.is_valid():
        try:
            saved, repeated = wallets.transfer(request.user,form.cleaned_data['operation_token'],form.cleaned_data)
        except (ValidationError,IntegrityError,OperationalError):
            form.add_error(None,'Chưa xác nhận được chuyển tiền. Kiểm tra lịch sử trước khi gửi lại; ví/ngày có thể đã thay đổi hoặc mã đã dùng với dữ liệu khác.')
        else:
            messages.success(request,'Thao tác đã được ghi trước đó, không chuyển thêm.' if repeated else 'Đã ghi chuyển nội bộ; không tính vào thu nhập/chi tiêu.')
            return redirect('finance:wallet_transfer_detail',pk=saved.pk)
    return render(request,'finance/wallet_transfer_form.html',{'form':form})


@login_required
@require_http_methods(['GET'])
@never_cache
def transfer_detail(request, pk):
    item = get_object_or_404(WalletTransfer.objects.select_related('source','destination'),pk=pk,user=request.user,
        source__user=request.user,destination__user=request.user)
    return render(request,'finance/wallet_transfer_detail.html',{'transfer':item})
