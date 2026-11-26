from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import AccessAuthenticationForm

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=AccessAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("switch/", views.switch_account, name="switch"),
    path("signup/", views.signup, name="signup"),
    path("requests/", views.account_requests, name="requests"),
    path("requests/<int:pk>/approve/", views.approve_request, name="approve"),
    path("requests/<int:pk>/reject/", views.reject_request, name="reject"),
]
