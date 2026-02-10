"""
URL configuration for Explainable Lock System.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .lock_views import LockEvaluationViewSet

router = DefaultRouter()
router.register(
    r'',  # Empty prefix since 'locks/' is already in the main URL config
    LockEvaluationViewSet,
    basename='lock-evaluation'
)

urlpatterns = router.urls

