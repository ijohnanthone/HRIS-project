def hrequest_context(request):
    """
    Supplies global branding variables and user role helper flags to all templates.
    """
    context = {
        'APP_NAME': 'HRequest',
        'APP_FULL_NAME': 'Human Resource Information System',
        'APP_YEAR': 2026,
    }
    if request.user.is_authenticated:
        role = getattr(request.user, 'role', '')
        context.update({
            'user_role': role,
            'is_super_admin': role == 'SUPER_ADMIN' or request.user.is_superuser,
            'is_hr_admin': role == 'HR_ADMIN',
            'is_hr_staff': role == 'HR_STAFF',
            'is_employee': role == 'EMPLOYEE',
            'is_hr_team': role in ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF'] or request.user.is_superuser,
        })
    return context
