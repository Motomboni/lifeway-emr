"""NAFDAC formulary URL routes."""

from django.urls import path

from .nafdac_views import nafdac_formulary_list

urlpatterns = [
    path("nafdac-formulary/", nafdac_formulary_list, name="nafdac-formulary-list"),
]
