from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .demo import demo_usernames


@require_POST
def switch_account(request):
    """Demo mode only: sign in as one of the seeded demo accounts without a password."""
    if not settings.DEMO_MODE:
        raise Http404
    username = request.POST.get("username", "")
    if username not in demo_usernames():
        raise PermissionDenied("Only the demo accounts can be switched to.")
    user = get_object_or_404(get_user_model(), username=username, is_active=True)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    where = "all stations" if user.is_hq else (user.station.name if user.station else "no station")
    messages.success(request, f"You are now signed in as {user}: {user.get_role_display()}, {where}.")
    return redirect("core:dashboard")
