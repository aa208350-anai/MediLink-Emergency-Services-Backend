# apps/accounts/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    # Registration
    RegisterClientView,
    RegisterDriverView,
    RegisterProviderAdminView,
    # Email verification
    VerifyEmailView,
    ResendVerificationView,
    # Auth
    LoginView,
    LogoutView,
    # Current user
    MeView,
    ProfileView,
    # Password
    ChangePasswordView,
    RequestPasswordResetView,
    ConfirmPasswordResetView,
    # Role upgrades
    UpgradeToDriverView,
    UpgradeToProviderAdminView,
    # Admin
    UserListView,
    UserDetailView,
    VerifyProfileView,
)

urlpatterns = [
    #  Registration 
    path("auth/register/client/",   RegisterClientView.as_view(),        name="register-client"),
    path("auth/register/driver/",   RegisterDriverView.as_view(),        name="register-driver"),
    path("auth/register/provider/", RegisterProviderAdminView.as_view(), name="register-provider"),

    #  Email verification 
    path("auth/verify-email/",        VerifyEmailView.as_view(),        name="verify-email"),
    path("auth/resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),

    #  Auth 
    path("auth/login/",         LoginView.as_view(),       name="login"),
    path("auth/logout/",        LogoutView.as_view(),      name="logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    #  Current user 
    path("auth/me/",      MeView.as_view(),      name="me"),
    path("auth/profile/", ProfileView.as_view(), name="profile"),

    #  Password management 
    path("auth/change-password/",        ChangePasswordView.as_view(),        name="change-password"),
    path("auth/password-reset/",         RequestPasswordResetView.as_view(),  name="password-reset-request"),
    path("auth/password-reset/confirm/", ConfirmPasswordResetView.as_view(),  name="password-reset-confirm"),

    #  Role upgrades 
    path("auth/upgrade/driver/",   UpgradeToDriverView.as_view(),        name="upgrade-driver"),
    path("auth/upgrade/provider/", UpgradeToProviderAdminView.as_view(), name="upgrade-provider"),

    #  Admin: user management 
    path("admin/users/",              UserListView.as_view(),   name="admin-user-list"),
    path("admin/users/<uuid:pk>/",    UserDetailView.as_view(), name="admin-user-detail"),
    path("admin/users/<uuid:pk>/verify/", VerifyProfileView.as_view(), name="admin-verify-profile"),
]


# ======================================================================
# URL summary
# ======================================================================
#
#  Method  URL                              Description               Auth
#  ------  -------------------------------  ------------------------  
#
#  -- Registration --
#  POST    /auth/register/client/           Create client account     Public
#  POST    /auth/register/driver/           Create driver account     Public
#  POST    /auth/register/provider/         Create provider admin     Public
#
#  -- Email verification --
#  POST    /auth/verify-email/              Verify OTP + token        Public
#  POST    /auth/resend-verification/       Resend OTP email          Public
#
#  -- Auth --
#  POST    /auth/login/                     Login → JWT pair          Public
#  POST    /auth/logout/                    Blacklist refresh token   Auth
#  POST    /auth/token/refresh/             Refresh access token      Public
#
#  -- Current user --
#  GET     /auth/me/                        Own user + profile        Auth
#  PATCH   /auth/me/                        Update first/last name    Auth
#  GET     /auth/profile/                   Own role profile          Auth
#  PATCH   /auth/profile/                   Update role profile       Auth
#
#  -- Password --
#  POST    /auth/change-password/           Change password (authed)  Auth
#  POST    /auth/password-reset/            Request reset OTP         Public
#  POST    /auth/password-reset/confirm/    Confirm OTP + new pass    Public
#
#  -- Role upgrades --
#  POST    /auth/upgrade/driver/            Upgrade to driver         Auth
#  POST    /auth/upgrade/provider/          Upgrade to provider admin Auth
#
#  -- Admin --
#  GET     /auth/admin/users/               List all users            Admin/Staff
#  GET     /auth/admin/users/{id}/          User detail               Admin/Staff
#  PATCH   /auth/admin/users/{id}/          Update role/status        Admin/Staff
#  POST    /auth/admin/users/{id}/verify/   Verify driver/provider    Admin/Staff
#
