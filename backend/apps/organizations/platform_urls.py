from django.urls import path

from .platform_views import PlatformOrganizationsView, PlatformOverviewView

urlpatterns = [
    path("overview/", PlatformOverviewView.as_view(), name="platform-overview"),
    path(
        "organizations/",
        PlatformOrganizationsView.as_view(),
        name="platform-organizations",
    ),
]
