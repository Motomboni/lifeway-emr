"""
OTP and Biometric Authentication URLs
"""
from django.urls import path
from . import views

urlpatterns = [
    # OTP endpoints
    path('request-otp/', views.request_otp, name='request-otp'),
    path('verify-otp/', views.verify_otp, name='verify-otp'),
    path('logout/', views.logout, name='logout'),
    # Biometric endpoints
    path('register-biometric/', views.register_biometric, name='register-biometric'),
    path('biometric-login/', views.biometric_login, name='biometric-login'),
]
