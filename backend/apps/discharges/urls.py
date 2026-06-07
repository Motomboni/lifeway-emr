"""
URL configuration for Discharge Summaries (visit-scoped).
"""

from rest_framework.routers import DefaultRouter

from .views import DischargeSummaryViewSet

router = DefaultRouter()
router.register(
    r"discharge-summaries", DischargeSummaryViewSet, basename="discharge-summary"
)

urlpatterns = router.urls
