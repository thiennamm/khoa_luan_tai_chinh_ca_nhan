import hashlib

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, OperationalError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .csv_import import (HEADER, MAX_BYTES, ImportProblem, cleanup_batches, confirm_batch,
                         inspect_batch, inspect_csv, stage_csv)
from .forms import CsvUploadForm
from .models import CsvImportBatch, CsvImportReceipt


@login_required
@require_http_methods(['GET'])
@never_cache
def csv_template(request):
    response = HttpResponse(','.join(HEADER) + '\r\n', content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="transaction-template.csv"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@require_http_methods(['GET', 'POST'])
@never_cache
def csv_upload(request):
    form = CsvUploadForm(request.POST if request.method == 'POST' else None,
                         request.FILES if request.method == 'POST' else None)
    inspection = None
    if request.method == 'POST':
        cleanup_batches(user=request.user)
        if getattr(request, 'csv_upload_too_large', False):
            form.add_error(None, 'Tệp vượt giới hạn 2 MiB (2.097.152 byte).')
        elif len(request.FILES) != 1 or len(request.FILES.getlist('file')) != 1:
            form.add_error(None, 'Mỗi lần chỉ tải một tệp CSV ở trường chọn tệp.')
        elif form.is_valid():
            raw = form.cleaned_data['file'].read(MAX_BYTES + 1)
            if CsvImportReceipt.objects.filter(user=request.user, sha256=hashlib.sha256(raw).hexdigest()).exists():
                form.add_error(None, 'Tệp có cùng SHA-256 đã được nhập thành công trong tài khoản này; đã chặn nhập lại.')
            else:
                inspection = inspect_csv(raw, request.user)
                if inspection.valid:
                    try:
                        batch = stage_csv(raw, request.user, inspection)
                    except ImportProblem as exc:
                        form.add_error(None, str(exc))
                    else:
                        return redirect('finance:csv_preview', pk=batch.pk)
    return render(request, 'finance/csv_upload.html', {'form': form, 'inspection': inspection})


def preview_context(batch, user):
    context = {'batch': batch, 'can_confirm': False}
    if batch.status == 'completed':
        context['receipt'] = CsvImportReceipt.objects.filter(user=user, batch=batch).first()
        context['notice'] = 'Lô này đã nhập thành công. Bấm lại không tạo thêm giao dịch.'
        return context, 200
    try:
        inspection = inspect_batch(batch, user)
    except ImportProblem as exc:
        context['notice'] = str(exc)
        return context, 410
    context['inspection'] = inspection
    already_imported = CsvImportReceipt.objects.filter(user=user, sha256=batch.sha256).exists()
    if already_imported:
        context['notice'] = 'Tệp có cùng SHA-256 đã nhập thành công trong tài khoản này; đã chặn nhập lại.'
    context['can_confirm'] = inspection.valid and batch.status == 'pending' and not already_imported
    return context, 200


@login_required
@require_http_methods(['GET'])
@never_cache
def csv_preview(request, pk):
    batch = get_object_or_404(CsvImportBatch, pk=pk, user=request.user)
    context, status = preview_context(batch, request.user)
    return render(request, 'finance/csv_preview.html', context, status=status)


@login_required
@require_http_methods(['POST'])
@never_cache
def csv_confirm(request, pk):
    # Xem/xác nhận lô của người khác đều 404, không tiết lộ tình trạng lô.
    batch = get_object_or_404(CsvImportBatch, pk=pk, user=request.user)
    try:
        confirm_batch(batch.pk, request.user)
    except (ImportProblem, IntegrityError, OperationalError) as exc:
        # Không xuất nội dung exception DB hoặc bản ghi giao dịch.
        message = (str(exc) if isinstance(exc, ImportProblem) else
                   'Không thể hoàn tất lô nhập hoặc đang có thao tác khác. Chưa thêm giao dịch từ lần xác nhận này; kiểm tra lại trạng thái rồi thử lại.')
        return render(request, 'finance/csv_preview.html', {'batch': batch, 'notice': message, 'can_confirm': False}, status=409)
    return redirect('finance:csv_preview', pk=batch.pk)
