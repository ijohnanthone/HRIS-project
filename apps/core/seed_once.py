import sys
from django.core.management import call_command

_TEAM_SEED_CHECKED = False


def ensure_team_seed_once():
    """
    Runs the one-time team member seed at most once per database.
    Uses AuditLog action 'ONE_TIME_TEAM_SEED_V1' as a permanent DB marker
    so deleted or modified employees are never re-created.
    """
    global _TEAM_SEED_CHECKED
    if _TEAM_SEED_CHECKED or 'test' in sys.argv:
        return
    try:
        from apps.core.models import AuditLog
        if not AuditLog.objects.filter(action='ONE_TIME_TEAM_SEED_V1').exists():
            call_command('seed_team_members')
        _TEAM_SEED_CHECKED = True
    except Exception:
        pass
