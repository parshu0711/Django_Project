import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .demo import demo_usernames
from .forms import ApproveForm, SignUpForm

log = logging.getLogger(__name__)
User = get_user_model()


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


# ------------------------------------------------------------------- sign-up
def _mail(subject, body, recipients):
    """Send a notification without ever blocking or breaking the request (satellite mail links drop)."""
    if not recipients:
        return
    try:
        send_mail(subject, body, None, recipients)
    except Exception:
        log.exception("Could not send account email: %s", subject)


def signup(request):
    """Request an account. It is created inactive and HQ approves it on the account requests page."""
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            review_url = request.build_absolute_uri(reverse("accounts:requests"))
            hq = list(
                User.objects.filter(is_active=True).filter(Q(is_superuser=True) | Q(role=User.Role.HQ_ADMIN))
                .exclude(email="").values_list("email", flat=True)
            )
            body = (
                f"{user.get_full_name()} ({user.username}, {user.email}) asked for a PolarOps account.\n\n"
                f"Requested role:  {user.get_role_display()}\n"
                f"Station:         {user.station}\n\n"
                f"Review it here: {review_url}\n"
            )
            transaction.on_commit(lambda: _mail(f"[PolarOps] Account request: {user.get_full_name()}", body, hq))
            messages.success(
                request,
                f"Thanks, {user.first_name}. Your request for {user.station} has been sent to NCPOR HQ. "
                "You can sign in once it is approved.",
            )
            return redirect("accounts:login")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


def _require_hq(request):
    if not request.user.is_hq:
        raise PermissionDenied("Only HQ administrators can review account requests.")


@login_required
def account_requests(request):
    """HQ: list the sign-ups waiting for approval."""
    _require_hq(request)
    pending = User.objects.filter(pending_approval=True).select_related("station").order_by("date_joined")
    return render(request, "accounts/requests.html", {
        "title": "Account requests",
        "pending": pending,
        "role_choices": ApproveForm.base_fields["role"].choices,
        "stations": ApproveForm.base_fields["station"].queryset,
    })


@login_required
@require_POST
def approve_request(request, pk):
    _require_hq(request)
    user = get_object_or_404(User, pk=pk, pending_approval=True)
    form = ApproveForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a valid role and station before approving.")
        return redirect("accounts:requests")
    user.role = form.cleaned_data["role"]
    user.station = form.cleaned_data["station"]
    user.is_active = True
    user.pending_approval = False
    user.save(update_fields=["role", "station", "is_active", "pending_approval"])
    login_url = request.build_absolute_uri(reverse("accounts:login"))
    body = (
        f"Hello {user.first_name},\n\nYour PolarOps account has been approved: "
        f"{user.get_role_display()} at {user.station}.\nSign in as '{user.username}' at {login_url}\n"
    )
    transaction.on_commit(lambda: _mail("[PolarOps] Your account is ready", body, [user.email] if user.email else []))
    messages.success(request, f"Approved {user.get_full_name()} as {user.get_role_display()} at {user.station}.")
    return redirect("accounts:requests")


@login_required
@require_POST
def reject_request(request, pk):
    _require_hq(request)
    user = get_object_or_404(User, pk=pk, pending_approval=True)
    name = user.get_full_name() or user.username
    user.delete()        # never active, owns no records
    messages.success(request, f"Rejected the account request from {name}.")
    return redirect("accounts:requests")
