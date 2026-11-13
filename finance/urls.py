from django.urls import path
from . import views
from . import csv_views
from . import coverage_views
from . import forecast_views
from . import forecast_demo_views
from .csv_export import transaction_export
from . import budget_views
from . import recurring_views
from . import forecast_history_views
from . import quick_entry_views
from . import savings_views
from . import category_defaults_views
from .monthly_report_views import monthly_report
from .financial_calendar_views import calendar_month, calendar_day
from . import wallet_views
from . import group_views
from . import notification_views

app_name = "finance"
urlpatterns = [
    path('thong-bao/', notification_views.inbox, name='notification_inbox'),
    path('thong-bao/<int:pk>/mo/', notification_views.open_notification, name='notification_open'),
    path('chia-tien-nhom/', group_views.index, name='group_list'),
    path('chia-tien-nhom/them/', group_views.create, name='group_create'),
    path('chia-tien-nhom/dong-tien-chua-gan/', group_views.unassigned, name='group_unassigned'),
    path('chia-tien-nhom/dong-tien/<int:posting_id>/', group_views.posting_detail, name='group_posting_detail'),
    path('chia-tien-nhom/<int:pk>/', group_views.detail, name='group_detail'),
    path('chia-tien-nhom/<int:pk>/moi/', group_views.invite, name='group_invite'),
    path('chia-tien-nhom/<int:pk>/doi-ten/', group_views.rename, name='group_rename'),
    path('chia-tien-nhom/<int:pk>/thanh-vien/<int:member_id>/<str:action>/', group_views.member_action, name='group_member_action'),
    path('chia-tien-nhom/<int:pk>/luu-tru/', group_views.archive, name='group_archive'),
    path('chia-tien-nhom/<int:pk>/khoan-chi/them/', group_views.expense_create, name='group_expense_create'),
    path('chia-tien-nhom/<int:pk>/khoan-chi/<int:expense_id>/', group_views.expense_detail, name='group_expense'),
    path('chia-tien-nhom/<int:pk>/khoan-chi/<int:expense_id>/huy/', group_views.expense_void, name='group_expense_void'),
    path('chia-tien-nhom/<int:pk>/phan-chia/<int:share_id>/<str:action>/', group_views.share_action, name='group_share_action'),
    path('chia-tien-nhom/<int:pk>/hoan-tra/them/', group_views.settlement_create, name='group_settlement_create'),
    path('chia-tien-nhom/<int:pk>/hoan-tra/<int:settlement_id>/', group_views.settlement_detail, name='group_settlement'),
    path('chia-tien-nhom/<int:pk>/hoan-tra/<int:settlement_id>/<str:action>/', group_views.settlement_detail, name='group_settlement_action'),
    path('chia-tien-nhom/<int:pk>/gan-vi/<int:source_id>/<str:side>/', group_views.posting, name='group_posting'),
    path('vi/', wallet_views.wallet_list, name='wallet_list'),
    path('vi/them/', wallet_views.wallet_edit, name='wallet_create'),
    path('vi/chua-xac-dinh/', wallet_views.wallet_detail, name='wallet_unknown'),
    path('vi/chuyen/', wallet_views.transfer_create, name='wallet_transfer'),
    path('vi/chuyen/<int:pk>/', wallet_views.transfer_detail, name='wallet_transfer_detail'),
    path('vi/<int:pk>/', wallet_views.wallet_detail, name='wallet_detail'),
    path('vi/<int:pk>/sua/', wallet_views.wallet_edit, name='wallet_edit'),
    path('vi/<int:pk>/trang-thai/', wallet_views.wallet_status, name='wallet_status'),
    path('lich-thu-chi/', calendar_month, name='financial_calendar'),
    path('lich-thu-chi/ngay/<str:day>/', calendar_day, name='financial_calendar_day'),
    path('bao-cao-thang/', monthly_report, name='monthly_report'),
    path('danh-muc/mau/', category_defaults_views.category_defaults, name='category_defaults'),
    path('muc-tieu-tiet-kiem/', savings_views.goal_list, name='savings_list'),
    path('muc-tieu-tiet-kiem/them/', savings_views.goal_edit, name='savings_create'),
    path('muc-tieu-tiet-kiem/<int:pk>/', savings_views.detail, name='savings_detail'),
    path('muc-tieu-tiet-kiem/<int:pk>/sua/', savings_views.goal_edit, name='savings_edit'),
    path('muc-tieu-tiet-kiem/<int:pk>/trang-thai/<str:action>/', savings_views.goal_status, name='savings_status'),
    path('muc-tieu-tiet-kiem/<int:pk>/phan-bo/', savings_views.entry_edit, name='savings_entry_create'),
    path('muc-tieu-tiet-kiem/<int:pk>/phan-bo/<int:entry_id>/sua/', savings_views.entry_edit, name='savings_entry_edit'),
    path('muc-tieu-tiet-kiem/<int:pk>/phan-bo/<int:entry_id>/xoa/', savings_views.entry_delete, name='savings_entry_delete'),
    path('giao-dich-dinh-ky/', recurring_views.recurring_list, name='recurring_list'),
    path('giao-dich-dinh-ky/them/', recurring_views.rule_edit, name='recurring_create'),
    path('giao-dich-dinh-ky/<int:pk>/sua/', recurring_views.rule_edit, name='recurring_edit'),
    path('giao-dich-dinh-ky/<int:pk>/lich-su/', recurring_views.rule_history, name='recurring_history'),
    path('giao-dich-dinh-ky/<int:pk>/trang-thai/<str:action>/', recurring_views.rule_status, name='recurring_status'),
    path('giao-dich-dinh-ky/<int:pk>/<int:year>/<int:month>/<str:action>/', recurring_views.occurrence_action, name='recurring_occurrence'),
    path('phan-hoi-phan-loai/', views.classification_feedback_list, name='classification_feedback'),
    path('giao-dich/goi-y-danh-muc/thao-tac/', views.suggestion_action, name='suggestion_action'),
    path("", views.dashboard, name="dashboard"),
    path('ngan-sach/', budget_views.budget_list, name='budget_list'),
    path('ngan-sach/them/', budget_views.budget_edit, name='budget_create'),
    path('ngan-sach/<int:pk>/sua/', budget_views.budget_edit, name='budget_edit'),
    path('ngan-sach/<int:pk>/xoa/', budget_views.budget_delete, name='budget_delete'),
    path('du-bao/', forecast_views.forecast, name='forecast'),
    path('du-bao/lich-su/', forecast_history_views.history, name='forecast_history'),
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
    path('giao-dich/tao-tuong-tu/luu/', views.transaction_duplicate_save, name='transaction_duplicate_save'),
    path('giao-dich/nhap-nhanh/', quick_entry_views.analyze, name='quick_entry'),
    path("giao-dich/goi-y-danh-muc/", views.category_suggestion, name="category_suggestion"),
    path("giao-dich/<int:pk>/", views.transaction_detail, name="transaction_detail"),
    path("giao-dich/<int:pk>/sua/", views.transaction_edit, name="transaction_edit"),
    path('giao-dich/<int:pk>/tao-tuong-tu/', views.transaction_duplicate, name='transaction_duplicate'),
    path("giao-dich/<int:pk>/xoa/", views.transaction_delete, name="transaction_delete"),
    path("danh-muc/", views.category_list, name="category_list"),
    path("danh-muc/them/", views.category_edit, name="category_create"),
    path("danh-muc/<int:pk>/sua/", views.category_edit, name="category_edit"),
    path("danh-muc/<int:pk>/xoa/", views.category_delete, name="category_delete"),
]
