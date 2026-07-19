"""NAFDAC formulary reference API."""

from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .nafdac_models import NAFDACFormularyEntry
from .permissions import CanViewNafdacFormulary


@api_view(["GET"])
@permission_classes([IsAuthenticated, CanViewNafdacFormulary])
def nafdac_formulary_list(request):
    qs = NAFDACFormularyEntry.objects.all().order_by("product_name")
    search = (request.query_params.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(product_name__icontains=search) | Q(nafdac_reg_no__icontains=search)
        )
    nhia_only = request.query_params.get("nhia_tariff_only", "").lower() == "true"
    if nhia_only:
        qs = qs.filter(nhia_tariff_code__gt="")
    return Response(
        [
            {
                "id": e.id,
                "nafdac_reg_no": e.nafdac_reg_no,
                "product_name": e.product_name,
                "active_ingredient": e.active_ingredient,
                "dosage_form": e.dosage_form,
                "strength": e.strength,
                "manufacturer": e.manufacturer,
                "nhia_tariff_code": e.nhia_tariff_code,
                "is_essential_medicine": e.is_essential_medicine,
                "is_active": e.is_active,
            }
            for e in qs[:500]
        ]
    )
