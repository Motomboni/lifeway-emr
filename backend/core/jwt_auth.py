"""
JWT authentication that applies admin view-as-role for the current request.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication


class RoleAwareJWTAuthentication(JWTAuthentication):
    """
    When the access token includes effective_role (issued via assume-role),
    override user.role on the in-memory user instance so all permission checks
    use the assumed role. The database role is unchanged.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result
        effective_role = validated_token.get('effective_role')
        actual_role = validated_token.get('actual_role')

        if effective_role:
            user._actual_role = actual_role or user.role
            user._role_assumed = True
            user.role = effective_role
        else:
            user._actual_role = user.role
            user._role_assumed = False

        return user, validated_token
