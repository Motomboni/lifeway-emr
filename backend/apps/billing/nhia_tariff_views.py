"""
NHIA tariff lookup API for doctors and scribe validation.

GET /api/v1/billing/nhia-tariffs/?search=...&icd11=...&nhia=...
"""

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsDoctor

from .nhia_tariff_models import NHIATariff
from .nhia_tariff_serializers import NHIATariffSerializer


class NHIATariffViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only NHIA tariff reference lookup."""

    serializer_class = NHIATariffSerializer
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_queryset(self):
        qs = NHIATariff.objects.filter(is_active=True)
        params = self.request.query_params

        icd11 = (params.get("icd11") or "").strip().upper()
        if icd11:
            qs = qs.filter(icd11_codes__contains=[icd11])

        nhia = (params.get("nhia") or "").strip()
        if nhia:
            qs = qs.filter(nhia_code=nhia)

        category = (params.get("category") or "").strip().upper()
        if category:
            qs = qs.filter(category=category)

        search = (params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(nhia_code__icontains=search)
                | Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(keywords__icontains=search)
            )

        return qs.order_by("category", "nhia_code")
