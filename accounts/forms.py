from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from stations.models import Station

User = get_user_model()


def signup_role_choices():
    return [(value, label) for value, label in User.Role.choices if value in User.SIGNUP_ROLES]


def _style(form):
    """Apply the PolarOps field classes (the same ones core.mixins.style_form uses)."""
    for field in form.fields.values():
        css = "field-select" if isinstance(field.widget, (forms.Select, forms.SelectMultiple)) else "field"
        field.widget.attrs["class"] = css


class SignUpForm(UserCreationForm):
    """Request an account. The new user stays inactive until HQ approves it."""

    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(help_text="HQ will tell you here when your account is approved.")
    station = forms.ModelChoiceField(
        queryset=Station.objects.exclude(status=Station.Status.INACTIVE),
        empty_label="Choose your station",
        help_text="You will only see this station's data.",
    )
    role = forms.ChoiceField(choices=signup_role_choices, label="Requested role")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email", "phone", "station", "role")
        labels = {"phone": "Phone / sat-phone (optional)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = "At least 8 characters, not too common and not only numbers."
        _style(self)
        self.fields["first_name"].widget.attrs["autocomplete"] = "given-name"
        self.fields["last_name"].widget.attrs["autocomplete"] = "family-name"
        self.fields["email"].widget.attrs["autocomplete"] = "email"

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists or is waiting for approval.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False
        user.pending_approval = True
        if commit:
            user.save()
        return user


class AccessAuthenticationForm(AuthenticationForm):
    """Sign-in form that tells a person when their account is still waiting for approval,
    instead of the generic "incorrect username or password"."""

    pending = False
    error_messages = {
        **AuthenticationForm.error_messages,
        "pending": "Your account request is waiting for approval by NCPOR HQ.",
    }

    def clean(self):
        try:
            return super().clean()
        except ValidationError:
            username, password = self.cleaned_data.get("username"), self.cleaned_data.get("password")
            if username and password:
                user = User._default_manager.filter(**{f"{User.USERNAME_FIELD}__iexact": username}).first()
                # only reveal "pending" to someone who knows the account's password
                if user and user.pending_approval and user.check_password(password):
                    self.pending = True
                    raise ValidationError(self.error_messages["pending"], code="pending") from None
            raise


class ApproveForm(forms.Form):
    """HQ confirms (or corrects) the role and station before activating an account."""

    role = forms.ChoiceField(choices=signup_role_choices)
    station = forms.ModelChoiceField(queryset=Station.objects.all())
