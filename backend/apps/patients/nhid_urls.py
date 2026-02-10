"""National Health ID verification URLs."""
from django.urls import path
from .nhid_views import verify_nhid

urlpatterns = [
    path('verify/', verify_nhid, name='nhid-verify'),
]
