from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from core.testing import TEST_PASSWORD, PolarFixtures


class UserRoleTests(PolarFixtures, TestCase):
    def test_hq_admin_is_hq(self):
        self.assertTrue(self.hq.is_hq)
        self.assertTrue(self.hq.can_manage)

    def test_superuser_is_hq_whatever_the_role(self):
        su = get_user_model().objects.create_superuser("root", "root@example.org", TEST_PASSWORD)
        self.assertTrue(su.is_hq)

    def test_station_staff_are_not_hq(self):
        self.assertFalse(self.mai_leader.is_hq)
        self.assertTrue(self.mai_leader.can_manage)
        self.assertFalse(self.mai_scientist.can_manage)


class AuthFlowTests(PolarFixtures, TestCase):
    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, "Sign in")
        self.assertContains(response, reverse("core:landing"))   # "Back to home" link

    def test_wrong_password_shows_error(self):
        response = self.client.post(reverse("accounts:login"), {"username": "hq", "password": "nope"})
        self.assertContains(response, "Incorrect username or password")

    def test_login_redirects_to_dashboard(self):
        response = self.client.post(reverse("accounts:login"), {"username": "hq", "password": TEST_PASSWORD})
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_logged_in_user_skips_login_page(self):
        self.login(self.hq)
        self.assertRedirects(self.client.get(reverse("accounts:login")), reverse("core:dashboard"))

    def test_logout_requires_post_and_returns_to_landing_page(self):
        self.login(self.hq)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("core:landing"))
        self.assertNotIn("_auth_user_id", self.client.session)


class DemoAccountSwitchTests(PolarFixtures, TestCase):
    """One-click switching between seeded demo accounts (accounts/views.switch_account)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        User = get_user_model()
        cls.demo_hq = User.objects.create_user("hq_admin", password=TEST_PASSWORD, first_name="Anita",
                                               role=User.Role.HQ_ADMIN)
        cls.demo_eng = User.objects.create_user("bharati_engineer", password=TEST_PASSWORD, first_name="Vikram",
                                                role=User.Role.ENGINEER, station=cls.bha)

    def switch(self, username):
        return self.client.post(reverse("accounts:switch"), {"username": username})

    def current_user_id(self):
        return int(self.client.session["_auth_user_id"])

    @override_settings(DEMO_MODE=True)
    def test_switch_between_roles(self):
        self.login(self.demo_eng)
        response = self.switch("hq_admin")
        self.assertRedirects(response, reverse("core:dashboard"), fetch_redirect_response=False)
        self.assertEqual(self.current_user_id(), self.demo_hq.pk)
        dashboard = self.client.get(reverse("core:dashboard"))
        self.assertContains(dashboard, "You are now signed in as Anita: HQ Administrator (NCPOR), all stations.")
        self.assertEqual(len(dashboard.context["cards"]), 3)          # HQ sees every station

        self.switch("bharati_engineer")
        self.assertEqual(self.current_user_id(), self.demo_eng.pk)
        cards = self.client.get(reverse("core:dashboard")).context["cards"]
        self.assertEqual([c["station"].code for c in cards], ["BHA"])

    @override_settings(DEMO_MODE=True)
    def test_one_click_sign_in_from_login_page(self):
        page = self.client.get(reverse("accounts:login"))
        self.assertContains(page, "Or try a demo account")
        self.assertContains(page, 'value="bharati_engineer"')
        self.switch("bharati_engineer")
        self.assertEqual(self.current_user_id(), self.demo_eng.pk)

    @override_settings(DEMO_MODE=True)
    def test_profile_menu_lists_demo_accounts_and_marks_current(self):
        self.login(self.demo_hq)
        html = self.client.get(reverse("core:dashboard")).content.decode()
        self.assertIn("Switch demo account", html)
        self.assertRegex(html, r'value="hq_admin" class="switch-item current" disabled')
        self.assertIn('value="bharati_engineer" class="switch-item"', html)
        self.assertNotIn('value="hq"', html)                           # non-demo users are never listed

    @override_settings(DEMO_MODE=True)
    def test_cannot_switch_to_non_demo_account(self):
        self.login(self.demo_eng)
        self.assertEqual(self.switch("hq").status_code, 403)           # real admin, not a demo account
        self.assertEqual(self.switch("mai_sensor").status_code, 403)
        self.assertEqual(self.current_user_id(), self.demo_eng.pk)

    @override_settings(DEMO_MODE=True)
    def test_inactive_demo_account_is_refused(self):
        get_user_model().objects.filter(pk=self.demo_hq.pk).update(is_active=False)
        self.assertEqual(self.switch("hq_admin").status_code, 404)

    @override_settings(DEMO_MODE=True)
    def test_switch_requires_post(self):
        self.assertEqual(self.client.get(reverse("accounts:switch"), {"username": "hq_admin"}).status_code, 405)

    @override_settings(DEMO_MODE=True)
    def test_switch_requires_csrf_token(self):
        from django.test import Client

        strict = Client(enforce_csrf_checks=True)
        response = strict.post(reverse("accounts:switch"), {"username": "hq_admin"})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("_auth_user_id", strict.session)

    @override_settings(DEMO_MODE=False)
    def test_switcher_is_off_outside_demo_mode(self):
        self.login(self.demo_eng)
        self.assertEqual(self.switch("hq_admin").status_code, 404)
        self.assertEqual(self.current_user_id(), self.demo_eng.pk)
        self.assertNotContains(self.client.get(reverse("core:dashboard")), "Switch demo account")
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("accounts:login")), "Or try a demo account")


class SignUpTests(PolarFixtures, TestCase):
    """Self sign-up creates an inactive account that HQ approves or rejects."""

    def data(self, **extra):
        return {
            "first_name": "Meera", "last_name": "Iyer", "username": "meera", "email": "meera@example.org",
            "phone": "", "station": self.mai.pk, "role": "SCIENTIST",
            "password1": "Glacier-Core-2026!", "password2": "Glacier-Core-2026!", **extra,
        }

    def signup(self, **extra):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("accounts:signup"), self.data(**extra))

    def test_page_offers_only_station_roles_and_open_stations(self):
        form = self.client.get(reverse("accounts:signup")).context["form"]
        roles = [value for value, _ in form.fields["role"].choices]
        self.assertNotIn("HQ_ADMIN", roles)
        self.assertNotIn("SENSOR", roles)
        self.assertIn("STATION_LEADER", roles)
        self.assertEqual(set(form.fields["station"].queryset), {self.mai, self.bha})   # not decommissioned DKG

    def test_signup_creates_a_pending_inactive_account_and_tells_hq(self):
        response = self.signup()
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        user = get_user_model().objects.get(username="meera")
        self.assertFalse(user.is_active)
        self.assertTrue(user.pending_approval)
        self.assertEqual((user.station, user.role), (self.mai, "SCIENTIST"))
        self.assertTrue(user.check_password("Glacier-Core-2026!"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Account request: Meera Iyer", mail.outbox[0].subject)
        self.assertIn("hq@example.org", mail.outbox[0].to)
        self.assertContains(self.client.get(reverse("accounts:login")), "has been sent to NCPOR HQ")

    def test_cannot_request_hq_or_sensor_roles(self):
        for role in ("HQ_ADMIN", "SENSOR"):
            with self.subTest(role=role):
                response = self.signup(role=role)
                self.assertEqual(response.status_code, 200)
                self.assertIn("role", response.context["form"].errors)
        self.assertFalse(get_user_model().objects.filter(username="meera").exists())

    def test_duplicate_username_or_email_is_rejected(self):
        self.assertIn("username", self.signup(username="HQ").context["form"].errors)          # case-insensitive
        self.assertIn("email", self.signup(email="HQ@example.org").context["form"].errors)    # case-insensitive

    def test_weak_or_mismatched_passwords_are_rejected(self):
        self.assertIn("password2", self.signup(password2="different-pass-99").context["form"].errors)
        self.assertIn("password2", self.signup(password1="password", password2="password").context["form"].errors)

    def test_pending_account_cannot_sign_in_and_is_told_why(self):
        self.signup()
        response = self.client.post(reverse("accounts:login"), {"username": "meera", "password": "Glacier-Core-2026!"})
        self.assertContains(response, "waiting for approval by NCPOR HQ")
        self.assertNotIn("_auth_user_id", self.client.session)
        # a wrong password never reveals that the account exists
        response = self.client.post(reverse("accounts:login"), {"username": "meera", "password": "wrong-one-123"})
        self.assertContains(response, "Incorrect username or password")
        self.assertNotContains(response, "waiting for approval")

    def test_signed_in_users_skip_the_signup_page(self):
        self.login(self.mai_leader)
        self.assertRedirects(self.client.get(reverse("accounts:signup")), reverse("core:dashboard"))

    def test_only_hq_can_review_requests(self):
        self.signup()
        url = reverse("accounts:requests")
        self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")
        self.login(self.mai_leader)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.login(self.hq)
        response = self.client.get(url)
        self.assertContains(response, "Meera Iyer")
        self.assertEqual(response.context["nav_pending_signups"], 1)
        self.assertContains(self.client.get(reverse("core:dashboard")), "1 account request waiting")

    def test_approving_activates_with_the_role_and_station_hq_chose(self):
        self.signup()
        user = get_user_model().objects.get(username="meera")
        self.login(self.hq)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("accounts:approve", args=[user.pk]),
                                        {"role": "ENGINEER", "station": self.bha.pk})
        self.assertRedirects(response, reverse("accounts:requests"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertFalse(user.pending_approval)
        self.assertEqual((user.role, user.station), ("ENGINEER", self.bha))
        self.assertEqual(mail.outbox[-1].to, ["meera@example.org"])
        self.client.logout()
        response = self.client.post(reverse("accounts:login"), {"username": "meera", "password": "Glacier-Core-2026!"})
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_approval_cannot_grant_hq(self):
        self.signup()
        user = get_user_model().objects.get(username="meera")
        self.login(self.hq)
        self.client.post(reverse("accounts:approve", args=[user.pk]), {"role": "HQ_ADMIN", "station": self.mai.pk})
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertTrue(user.pending_approval)

    def test_rejecting_deletes_only_pending_requests(self):
        self.signup()
        user = get_user_model().objects.get(username="meera")
        self.login(self.hq)
        self.assertEqual(self.client.get(reverse("accounts:reject", args=[user.pk])).status_code, 405)   # POST only
        self.client.post(reverse("accounts:reject", args=[user.pk]))
        self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())
        # a real, active account can't be deleted through this page
        self.assertEqual(self.client.post(reverse("accounts:reject", args=[self.mai_scientist.pk])).status_code, 404)
        self.assertTrue(get_user_model().objects.filter(pk=self.mai_scientist.pk).exists())

    def test_station_staff_cannot_approve(self):
        self.signup()
        user = get_user_model().objects.get(username="meera")
        self.login(self.mai_leader)
        response = self.client.post(reverse("accounts:approve", args=[user.pk]),
                                    {"role": "SCIENTIST", "station": self.mai.pk})
        self.assertEqual(response.status_code, 403)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_admin_action_approves(self):
        from unittest import mock

        from django.contrib import admin

        self.signup()
        model_admin = admin.site._registry[get_user_model()]
        with mock.patch.object(model_admin, "message_user"):
            model_admin.approve_signups(mock.Mock(user=self.hq), get_user_model().objects.filter(username="meera"))
        user = get_user_model().objects.get(username="meera")
        self.assertTrue(user.is_active)
        self.assertFalse(user.pending_approval)
