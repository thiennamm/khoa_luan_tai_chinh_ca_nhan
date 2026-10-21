from django.db.models import F


def bump_forecast_version(user_ids, using):
    """Gọi bên trong transaction đã ghi dữ liệu, không chứa tiền hoặc mô tả."""
    from .models import ForecastDataVersion
    for user_id in sorted(set(user_ids)):
        version, created = ForecastDataVersion.objects.using(using).get_or_create(
            user_id=user_id, defaults={'version': 1})
        if not created:
            ForecastDataVersion.objects.using(using).filter(pk=version.pk).update(version=F('version') + 1)
