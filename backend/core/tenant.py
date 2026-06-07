"""
Multi-tenant organization scoping utilities.

Used across viewsets to enforce tenant isolation in production SaaS.
Superusers bypass org filters for platform administration.
"""

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied


def get_organization_from_request_headers(request):
    """
    Resolve tenant from subdomain, X-Organization-Id / slug headers.
    Safe in Django middleware before DRF JWT authentication runs.
    """
    from core.tenant_subdomain import resolve_organization_from_host

    host_org = resolve_organization_from_host(request)
    if host_org is not None:
        return host_org

    org_id = request.headers.get("X-Organization-Id") if hasattr(request, "headers") else None
    if not org_id:
        org_id = request.META.get("HTTP_X_ORGANIZATION_ID")
    if org_id:
        try:
            from apps.organizations.models import Organization

            return Organization.objects.get(pk=int(org_id), is_active=True)
        except (ValueError, Organization.DoesNotExist):
            pass

    org_slug = request.headers.get("X-Organization-Slug") if hasattr(request, "headers") else None
    if not org_slug:
        org_slug = request.META.get("HTTP_X_ORGANIZATION_SLUG")
    if org_slug:
        try:
            from apps.organizations.models import Organization

            return Organization.objects.get(slug=org_slug, is_active=True)
        except Organization.DoesNotExist:
            pass
    return None


def get_request_organization(request):
    """Return the resolved organization on the request, if any."""
    org = getattr(request, "organization", None)
    if org is not None:
        try:
            # Force evaluation of SimpleLazyObject
            org.pk
            return org
        except Exception:
            org = None

    # Fallback: resolve directly from headers (DRF tests / early request lifecycle)
    org_id = request.headers.get("X-Organization-Id") if hasattr(request, "headers") else None
    if not org_id:
        org_id = request.META.get("HTTP_X_ORGANIZATION_ID")
    if org_id and getattr(request, "user", None) and request.user.is_authenticated:
        try:
            from apps.organizations.models import Organization, OrganizationUser

            org = Organization.objects.get(pk=int(org_id), is_active=True)
            if OrganizationUser.objects.filter(organization=org, user=request.user).exists():
                return org
        except (ValueError, Organization.DoesNotExist):
            pass
    return None


def is_platform_superuser(request) -> bool:
    user = getattr(request, "user", None)
    return bool(user and getattr(user, "is_superuser", False))


def filter_by_organization(queryset, request, org_field="organization"):
    """Filter queryset by direct organization FK."""
    org = get_request_organization(request)
    if org and not is_platform_superuser(request):
        return queryset.filter(**{org_field: org})
    return queryset


def filter_by_visit_organization(queryset, request):
    """Filter queryset via visit.organization."""
    org = get_request_organization(request)
    if org and not is_platform_superuser(request):
        return queryset.filter(visit__organization=org)
    return queryset


def filter_by_patient_organization(queryset, request):
    """Filter queryset via patient.organization."""
    org = get_request_organization(request)
    if org and not is_platform_superuser(request):
        return queryset.filter(patient__organization=org)
    return queryset


def filter_by_related_organization(queryset, request, org_path):
    """Filter queryset via a nested organization path (e.g. visit__organization)."""
    org = get_request_organization(request)
    if org and not is_platform_superuser(request):
        return queryset.filter(**{org_path: org})
    return queryset


def filter_by_radiology_order_visit_organization(queryset, request):
    """Filter queryset via radiology_order.visit.organization."""
    return filter_by_related_organization(
        queryset, request, "radiology_order__visit__organization"
    )


def filter_catalog_by_organization(queryset, request):
    """
    Org-specific rows plus optional global templates (organization IS NULL).
    Mirrors ServiceCatalogViewSet behavior.
    """
    from django.db.models import Q

    org = get_request_organization(request)
    if org and not is_platform_superuser(request):
        return queryset.filter(Q(organization=org) | Q(organization__isnull=True))
    return queryset


def try_get_org_scoped_visit(request, visit_id):
    """
    Load a visit scoped to request.organization, or None if not found / wrong tenant.
    Use in permission classes (return False instead of raising Http404).
    """
    from apps.visits.models import Visit

    org = get_request_organization(request)
    if org and not is_platform_superuser(request):
        return Visit.objects.filter(pk=visit_id, organization=org).first()
    if not is_platform_superuser(request):
        return None
    return Visit.objects.filter(pk=visit_id).first()


def get_org_scoped_visit(request, visit_id):
    """
    Load a visit scoped to request.organization.
    Raises 404 if visit belongs to another tenant.
    """
    from django.http import Http404

    visit = try_get_org_scoped_visit(request, visit_id)
    if visit is None:
        raise Http404("Visit not found.")
    return visit


def get_org_scoped_patient(request, patient_id):
    """Load a patient scoped to request.organization."""
    from apps.patients.models import Patient

    org = get_request_organization(request)
    if org and not is_platform_superuser(request):
        return get_object_or_404(Patient, pk=patient_id, organization=org)
    if not is_platform_superuser(request):
        from django.http import Http404

        raise Http404("Organization context required.")
    return get_object_or_404(Patient, pk=patient_id)


def assert_visit_in_organization(visit, request):
    """Raise PermissionDenied if visit is outside current org."""
    org = get_request_organization(request)
    if org and not is_platform_superuser(request):
        if getattr(visit, "organization_id", None) != org.id:
            raise PermissionDenied("Visit does not belong to your organization.")


def assert_patient_in_organization(patient, request):
    """Raise PermissionDenied if patient is outside current org."""
    org = get_request_organization(request)
    if org and not is_platform_superuser(request):
        if getattr(patient, "organization_id", None) != org.id:
            raise PermissionDenied("Patient does not belong to your organization.")
