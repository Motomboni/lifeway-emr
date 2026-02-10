"""
URL configuration for authentication endpoints.
"""
from django.urls import path, include
from .views import login, refresh_token, logout, me, register, list_doctors

urlpatterns = [
    path('login/', login, name='auth-login'),
    path('register/', register, name='auth-register'),
    path('refresh/', refresh_token, name='auth-refresh'),
    path('logout/', logout, name='auth-logout'),
    path('me/', me, name='auth-me'),
    path('doctors/', list_doctors, name='auth-doctors'),
    # OTP and biometric (patient portal)
    path('', include('apps.auth_otp.urls')),
]
