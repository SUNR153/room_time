from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_creates_user_with_hashed_password(self):
        response = self.client.post(reverse('auth_app:register'), {
            'email': 'new@example.com',
            'password': 'pass12345',
            'username': 'newuser',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(email='new@example.com')
        self.assertNotEqual(user.password, 'pass12345')
        self.assertTrue(user.check_password('pass12345'))

    def test_register_ignores_privilege_escalation_fields(self):
        """
        Regression test: RegisterSerializer previously had Meta.field/extra_kwards
        typos, so it accepted (and returned) every User field including
        is_staff/is_superuser/role.
        """
        response = self.client.post(reverse('auth_app:register'), {
            'email': 'attacker@example.com',
            'password': 'pass12345',
            'username': 'attacker',
            'is_staff': True,
            'is_superuser': True,
            'role': 'admin',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(email='attacker@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role, 'user')

    def test_register_does_not_return_password(self):
        response = self.client.post(reverse('auth_app:register'), {
            'email': 'new2@example.com',
            'password': 'pass12345',
            'username': 'newuser2',
        })
        self.assertNotIn('password', response.data)


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='pass12345')

    def test_login_with_correct_credentials_returns_tokens(self):
        response = self.client.post(reverse('auth_app:login'), {
            'email': 'user@example.com',
            'password': 'pass12345',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(reverse('auth_app:login'), {
            'email': 'user@example.com',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_unknown_email_fails(self):
        response = self.client.post(reverse('auth_app:login'), {
            'email': 'nobody@example.com',
            'password': 'pass12345',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='pass12345')

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('auth_app:me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('auth_app:me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'user@example.com')
        self.assertEqual(response.data['role'], 'user')


class LogoutViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='pass12345')

    def test_logout_blacklists_refresh_token(self):
        login = self.client.post(reverse('auth_app:login'), {
            'email': 'user@example.com',
            'password': 'pass12345',
        }).data

        response = self.client.post(reverse('auth_app:logout'), {'refresh': login['refresh']})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_with_invalid_token_returns_400(self):
        response = self.client.post(reverse('auth_app:logout'), {'refresh': 'not-a-real-token'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
