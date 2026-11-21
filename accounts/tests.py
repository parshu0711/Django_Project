from django.contrib.auth import get_user_model
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
