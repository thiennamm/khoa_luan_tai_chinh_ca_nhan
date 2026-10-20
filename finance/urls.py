from django.urls import path
from . import views

app_name = "finance"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("giao-dich/", views.transaction_list, name="transaction_list"),
    path("giao-dich/them/", views.transaction_edit, name="transaction_create"),
    path("giao-dich/<int:pk>/", views.transaction_detail, name="transaction_detail"),
    path("giao-dich/<int:pk>/sua/", views.transaction_edit, name="transaction_edit"),
    path("giao-dich/<int:pk>/xoa/", views.transaction_delete, name="transaction_delete"),
    path("danh-muc/", views.category_list, name="category_list"),
    path("danh-muc/them/", views.category_edit, name="category_create"),
    path("danh-muc/<int:pk>/sua/", views.category_edit, name="category_edit"),
    path("danh-muc/<int:pk>/xoa/", views.category_delete, name="category_delete"),
]
