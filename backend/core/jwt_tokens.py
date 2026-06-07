"""
JWT helpers for admin role assumption (view-as-role testing).
"""
from rest_framework_simplejwt.tokens import RefreshToken


class RoleAwareRefreshToken(RefreshToken):
    """Refresh token that propagates effective_role claims to new access tokens."""

    @property
    def access_token(self):
        access = super().access_token
        effective_role = self.get('effective_role')
        if effective_role:
            access['effective_role'] = effective_role
            access['actual_role'] = self.get('actual_role')
        return access


def issue_tokens_for_user(user, effective_role=None):
    """
    Issue JWT pair. When effective_role is set, embed view-as claims (admin testing only).
    """
    refresh = RoleAwareRefreshToken.for_user(user)
    if effective_role:
        refresh['effective_role'] = effective_role
        refresh['actual_role'] = user.role
    return refresh
