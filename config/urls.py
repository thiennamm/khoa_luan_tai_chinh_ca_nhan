from django.contrib.auth import views as auth_views
from django.urls import include, path
from finance.forms import VietnameseAuthenticationForm
from finance.views import signup

urlpatterns = [
    path("tai-khoan/dang-ky/", signup, name="signup"),
    path("tai-khoan/dang-nhap/", auth_views.LoginView.as_view(
        template_name="registration/login.html", authentication_form=VietnameseAuthenticationForm,
        redirect_authenticated_user=True,
    ), name="login"),
    path("tai-khoan/dang-xuat/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("finance.urls")),
]
