"""Patient allergy API — nested under /api/v1/patients/{patient_id}/allergies/."""

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.exceptions import PermissionDenied

from .allergy_models import PatientAllergy
from .allergy_serializers import PatientAllergyCreateSerializer, PatientAllergySerializer
from .models import Patient
from .permissions import CanManagePatientAllergies, CanViewPatient


class PatientAllergyViewSet(viewsets.ModelViewSet):
    """CRUD for structured patient allergies."""

    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanViewPatient()]
        return [IsAuthenticated(), CanManagePatientAllergies()]

    def get_patient(self):
        patient = get_object_or_404(
            Patient,
            pk=self.kwargs["patient_id"],
            is_active=True,
        )
        org = getattr(self.request, "organization", None)
        if org and patient.organization_id and patient.organization_id != org.id:
            raise PermissionDenied("Patient not found in this organization.")
        return patient

    def get_queryset(self):
        patient = self.get_patient()
        qs = PatientAllergy.objects.filter(patient=patient).select_related(
            "created_by"
        )
        if self.request.query_params.get("is_active", "true").lower() != "false":
            qs = qs.filter(is_active=True)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PatientAllergyCreateSerializer
        return PatientAllergySerializer

    def perform_create(self, serializer):
        patient = self.get_patient()
        allergy = serializer.save(patient=patient, created_by=self.request.user)
        self._sync_patient_allergy_summary(patient)

    def perform_update(self, serializer):
        allergy = serializer.save()
        self._sync_patient_allergy_summary(allergy.patient)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        self._sync_patient_allergy_summary(instance.patient)

    @staticmethod
    def _sync_patient_allergy_summary(patient: Patient) -> None:
        """Keep legacy free-text field as comma-separated summary for compatibility."""
        names = list(
            PatientAllergy.objects.filter(patient=patient, is_active=True)
            .order_by("allergen")
            .values_list("allergen", flat=True)
        )
        summary = ", ".join(names) if names else ""
        if (patient.allergies or "") != summary:
            patient.allergies = summary or None
            patient.save(update_fields=["allergies", "updated_at"])

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        out = PatientAllergySerializer(self.get_queryset().get(pk=serializer.instance.pk))
        return Response(out.data, status=status.HTTP_201_CREATED)
