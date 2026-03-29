"""
URL configuration for Referrals (visit-scoped).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReferralViewSet

router = DefaultRouter()
# Prefix must be '' — parent URL already ends with /referrals/ (see apps.visits.urls).
router.register(r'', ReferralViewSet, basename='referral')

urlpatterns = router.urls
