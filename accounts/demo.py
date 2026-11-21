"""
Demo-mode helpers: one-click switching between the seeded demo accounts.

Only active when settings.DEMO_MODE is True (defaults to DEBUG). Never enable it on a real
deployment: anyone who can reach the site could sign in as the HQ administrator.
"""
from django.contrib.auth import get_user_model


def demo_usernames():
    from core.management.commands.seed_demo import DEMO_USERS

    return [row[0] for row in DEMO_USERS]


def demo_accounts():
    """The seeded demo users that exist, in seed order (HQ admin first)."""
    names = demo_usernames()
    found = {
        u.username: u
        for u in get_user_model().objects.filter(username__in=names, is_active=True).select_related("station")
    }
    return [found[n] for n in names if n in found]
