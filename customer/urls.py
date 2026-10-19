from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomerRegisterView,
    CustomerLoginView,
    CustomerProfileView,
)

app_name = 'customer'

urlpatterns = [
    # Registration & Login
    path('register/', CustomerRegisterView.as_view(), name='register'),
    path('login/', CustomerLoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Profile Management
    path('profile/', CustomerProfileView.as_view(), name='profile'),
]
