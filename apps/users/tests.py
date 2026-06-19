from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User


class AuthFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier-auth',
            password='strong-password',
            name='Kassir Auth',
            role=User.Role.CASHIER,
        )

    def login(self):
        return self.client.post(reverse('users:login'), {
            'username': self.user.username,
            'password': 'strong-password',
        }, format='json')

    def test_login_and_getme_return_same_user_profile(self):
        login_response = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        getme_response = self.client.get(reverse('users:getme'))

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertEqual(getme_response.status_code, status.HTTP_200_OK)
        self.assertEqual(getme_response.data, login_response.data['user'])
        self.assertEqual(getme_response.data['role'], User.Role.CASHIER)
        self.assertEqual(getme_response.data['role_display'], 'Kassir')

    def test_getme_requires_access_token(self):
        response = self.client.get(reverse('users:getme'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        login_response = self.login()
        access = login_response.data['access']
        refresh = login_response.data['refresh']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        logout_response = self.client.post(
            reverse('users:logout'),
            {'refresh': refresh},
            format='json',
        )
        self.client.credentials()
        refresh_response = self.client.post(
            reverse('token_refresh'),
            {'refresh': refresh},
            format='json',
        )

        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_refresh_token(self):
        login_response = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = self.client.post(reverse('users:logout'), {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('refresh', response.data)
