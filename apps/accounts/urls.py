from django.urls import path
from .views import (
    HRequestLoginView,
    HRequestLogoutView,
    UserProfileView,
    HRequestPasswordChangeView,
)

app_name = 'accounts'

urlpatterns = [
    path('login/', HRequestLoginView.as_view(), name='login'),
    path('logout/', HRequestLogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('password/change/', HRequestPasswordChangeView.as_view(), name='password_change'),
]
