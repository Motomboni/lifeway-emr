"""
URL configuration for authentication endpoints.
"""
from django.urls import path, include
from .views import (
    login, refresh_token, logout, me, register, list_doctors,
    list_pending_staff, approve_staff, list_all_staff, deactivate_staff,
)

urlpatterns = [
    path('login/', login, name='auth-login'),
    path('register/', register, name='auth-register'),
    path('refresh/', refresh_token, name='auth-refresh'),
    path('logout/', logout, name='auth-logout'),
    path('me/', me, name='auth-me'),
    path('doctors/', list_doctors, name='auth-doctors'),
    path('pending-staff/', list_pending_staff, name='auth-pending-staff'),
    path('pending-staff/<int:user_id>/approve/', approve_staff, name='auth-approve-staff'),
    path('staff/', list_all_staff, name='auth-list-staff'),
    path('staff/<int:user_id>/deactivate/', deactivate_staff, name='auth-deactivate-staff'),
    # OTP and biometric (patient portal)
    path('', include('apps.auth_otp.urls')),
]
