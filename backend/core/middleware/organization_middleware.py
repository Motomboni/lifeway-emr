"""
Organization (Tenant) Middleware.

Resolves the current organization from:
1. X-Organization-Id header (API requests)
2. X-Organization-Slug header
3. JWT claim 'organization_id' (set by auth)
4. User's default organization

Sets request.organization for use in views and queryset filtering.
"""


from django.utils.functional import SimpleLazyObject

def _org_for_authenticated_user(request, org):
    """Return org if the user is a member (or platform superuser)."""
    from apps.organizations.models import OrganizationUser
    from core.tenant import is_platform_superuser

    if is_platform_superuser(request):
        return org
    if OrganizationUser.objects.filter(organization=org, user=request.user).exists():
        return org
    return None


def get_organization(request):
    # This runs lazily when request.organization is accessed.
    # By this time, DRF has authenticated the user and updated request.user.

    # 0. Subdomain tenant (works before auth for public branding endpoints)
    from core.tenant_subdomain import resolve_organization_from_host

    host_org = resolve_organization_from_host(request)
    if host_org is not None:
        request.tenant_from_subdomain = True
        if hasattr(request, "user") and request.user.is_authenticated:
            return _org_for_authenticated_user(request, host_org)
        return host_org

    if not hasattr(request, "user") or not request.user.is_authenticated:
        return None

    # 1. Header: X-Organization-Id (preferred for API)
    org_id = request.headers.get("X-Organization-Id") or request.META.get(
        "HTTP_X_ORGANIZATION_ID"
    )
    if org_id:
        try:
            from apps.organizations.models import Organization, OrganizationUser

            org = Organization.objects.get(pk=int(org_id), is_active=True)
            return _org_for_authenticated_user(request, org)
        except (ValueError, Organization.DoesNotExist):
            pass

    # 2. Header: X-Organization-Slug
    org_slug = request.headers.get("X-Organization-Slug") or request.META.get(
        "HTTP_X_ORGANIZATION_SLUG"
    )
    if org_slug:
        try:
            from apps.organizations.models import Organization, OrganizationUser

            org = Organization.objects.get(slug=org_slug, is_active=True)
            return _org_for_authenticated_user(request, org)
        except Organization.DoesNotExist:
            pass

    # 3. JWT claim (set by custom token serializer)
    if hasattr(request, "auth") and request.auth:
        org_id = (
            request.auth.get("organization_id")
            if isinstance(request.auth, dict)
            else getattr(request.auth, "organization_id", None)
        )
        if org_id:
            try:
                from apps.organizations.models import Organization, OrganizationUser

                org = Organization.objects.get(pk=org_id, is_active=True)
                return _org_for_authenticated_user(request, org)
            except (ValueError, Organization.DoesNotExist):
                pass

    # 4. User's default organization
    from apps.organizations.models import OrganizationUser

    default_membership = (
        OrganizationUser.objects.filter(user=request.user, is_default=True)
        .select_related("organization")
        .first()
    )

    if default_membership:
        return default_membership.organization

    # 5. Fallback: first organization (disabled when explicit tenant context is required)
    from django.conf import settings

    require_explicit = getattr(settings, "REQUIRE_ORGANIZATION_CONTEXT", False)
    if not require_explicit:
        first_membership = (
            OrganizationUser.objects.filter(user=request.user)
            .select_related("organization")
            .first()
        )
        if first_membership:
            return first_membership.organization

    return None


class OrganizationMiddleware:
    """
    Attach the current organization to the request.
    Evaluated lazily so DRF authentication can complete first.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = SimpleLazyObject(lambda: get_organization(request))
        return self.get_response(request)
