from django.urls import path
from users.views import (
    RegisterView,
    LoginView,
    TokenRefreshView,
    ProfileView,
    ChangePasswordView,
    AvatarUploadView,
    GetAllUsersView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('profile/', ProfileView.as_view(), name='user-profile'),
    path('profile/avatar/', AvatarUploadView.as_view(), name='user-avatar'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('get-users/', GetAllUsersView.as_view(), name='get-all-users'),
]
