"""
Admin role assumption — lets administrators test the app as clinical staff roles.
"""
# Roles an admin may view-as (excludes ADMIN and PATIENT)
ASSUMABLE_ROLES = [
    'DOCTOR',
    'NURSE',
    'LAB_TECH',
    'RADIOLOGY_TECH',
    'PHARMACIST',
    'RECEPTIONIST',
    'IVF_SPECIALIST',
    'EMBRYOLOGIST',
]

ROLE_DISPLAY_NAMES = {
    'DOCTOR': 'Doctor',
    'NURSE': 'Nurse',
    'LAB_TECH': 'Lab Scientist',
    'RADIOLOGY_TECH': 'Radiology Technician',
    'PHARMACIST': 'Pharmacist',
    'RECEPTIONIST': 'Receptionist',
    'IVF_SPECIALIST': 'IVF Specialist',
    'EMBRYOLOGIST': 'Embryologist',
}


def can_assume_roles(user):
    """Only administrators may switch into another role for testing."""
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or getattr(user, 'role', None) == 'ADMIN'


def is_valid_assumable_role(role):
    return role in ASSUMABLE_ROLES


def serialize_user_with_role_context(user):
    """Build user dict for API responses, including view-as metadata."""
    from apps.users.serializers import UserSerializer

    data = UserSerializer(user).data
    assumed = getattr(user, '_role_assumed', False)
    actual = getattr(user, '_actual_role', data.get('role'))

    if assumed:
        data['role'] = user.role
        data['actual_role'] = actual
        data['viewing_as_role'] = True
    else:
        data['actual_role'] = actual
        data['viewing_as_role'] = False

    return data
