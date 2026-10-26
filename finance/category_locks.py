"""Serialize supported category saves/default setup without changing account values."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import F


def lock_catalog(user_id, using='default'):
    # Call inside atomic, before reading the catalog. UPDATE also locks on SQLite;
    # select_for_update alone would not. last_login remains exactly unchanged.
    if not get_user_model().objects.using(using).filter(pk=user_id).update(last_login=F('last_login')):
        raise ValidationError('Tài khoản không còn khả dụng. Hãy đăng nhập lại.')
