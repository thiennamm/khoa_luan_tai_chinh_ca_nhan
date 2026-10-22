from django.urls import path
from . import views
from . import csv_views
from . import coverage_views
from . import forecast_views
from . import forecast_demo_views
from .csv_export import transaction_export
from . import budget_views

app_name = "finance"
urlpatterns = [
    path('phan-hoi-phan-loai/', views.classification_feedback_list, name='classification_feedback'),
    path('giao-dich/goi-y-danh-muc/thao-tac/', views.suggestion_action, name='suggestion_action'),
    path("", views.dashboard, name="dashboard"),
    path('ngan-sach/', budget_views.budget_list, name='budget_list'),
    path('ngan-sach/them/', budget_views.budget_edit, name='budget_create'),
    path('ngan-sach/<int:pk>/sua/', budget_views.budget_edit, name='budget_edit'),
    path('ngan-sach/<int:pk>/xoa/', budget_views.budget_delete, name='budget_delete'),
    path('du-bao/', forecast_views.forecast, name='forecast'),
    path('du-bao/demo/', forecast_demo_views.demo, name='forecast_demo'),
    path('lich-su-ghi-chep/', coverage_views.history, name='monthly_history'),
    path('lich-su-ghi-chep/<int:year>/<int:month>/xac-nhan/', coverage_views.confirm, name='coverage_confirm'),
    path('lich-su-ghi-chep/<int:year>/<int:month>/trang-thai/', coverage_views.change_status, name='coverage_status'),
    path("giao-dich/", views.transaction_list, name="transaction_list"),
    path('giao-dich/xuat-csv/', transaction_export, name='transaction_export'),
    path('giao-dich/nhap-csv/', csv_views.csv_upload, name='csv_upload'),
    path('giao-dich/nhap-csv/mau/', csv_views.csv_template, name='csv_template'),
    path('giao-dich/nhap-csv/<uuid:pk>/', csv_views.csv_preview, name='csv_preview'),
    path('giao-dich/nhap-csv/<uuid:pk>/xac-nhan/', csv_views.csv_confirm, name='csv_confirm'),
    path("giao-dich/them/", views.transaction_edit, name="transaction_create"),
    path("giao-dich/goi-y-danh-muc/", views.category_suggestion, name="category_suggestion"),
    path("giao-dich/<int:pk>/", views.transaction_detail, name="transaction_detail"),
    path("giao-dich/<int:pk>/sua/", views.transaction_edit, name="transaction_edit"),
    path("giao-dich/<int:pk>/xoa/", views.transaction_delete, name="transaction_delete"),
    path("danh-muc/", views.category_list, name="category_list"),
    path("danh-muc/them/", views.category_edit, name="category_create"),
    path("danh-muc/<int:pk>/sua/", views.category_edit, name="category_edit"),
    path("danh-muc/<int:pk>/xoa/", views.category_delete, name="category_delete"),
]
