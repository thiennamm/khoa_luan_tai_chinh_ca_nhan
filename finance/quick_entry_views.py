from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from .quick_entry import parse_entry, QuickEntryError


@login_required
@require_POST
@never_cache
def analyze(request):
    try:
        if len(request.POST.getlist('text')) != 1:
            raise QuickEntryError(['Chỉ gửi một câu nhập nhanh mỗi lần.'])
        result = parse_entry(request.POST.get('text', ''))
    except QuickEntryError as error:
        return JsonResponse({'status': 'invalid', 'errors': error.errors}, status=400)
    return JsonResponse(result)
