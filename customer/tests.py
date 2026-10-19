from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class CustomerAuthTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('customer:register')
        self.login_url = reverse('customer:login')
        self.profile_url = reverse('customer:profile')
        self.refresh_url = reverse('customer:token-refresh')

        self.valid_email = "customer.test@gmail.com"
        self.valid_password = "SecurePassword123!"

    def test_customer_can_register_with_gmail_and_password(self):
        """
        Verify that a customer can register with email (gmail) and password,
        and receive Bearer access and refresh tokens.
        """
        payload = {
            "email": self.valid_email,
            "password": self.valid_password,
            "password_confirm": self.valid_password,
            "first_name": "Test",
            "last_name": "Customer",
            "phone_number": "+8801700000000"
        }

        response = self.client.post(self.register_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('token_type'), 'Bearer')
        self.assertTrue('access_token' in response.data)
        self.assertTrue('refresh_token' in response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], self.valid_email)
        self.assertEqual(response.data['user']['first_name'], "Test")
        self.assertEqual(response.data['user']['phone_number'], "+8801700000000")

        # Verify user was created in DB
        user = User.objects.filter(email=self.valid_email).first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password(self.valid_password))

    def test_customer_registration_duplicate_email_fails(self):
        """Verify that registering with an already existing email returns HTTP 400."""
        # Create existing user
        User.objects.create_user(
            username="existing_user",
            email=self.valid_email,
            password="somePassword123!"
        )

        payload = {
            "email": self.valid_email,
            "password": self.valid_password
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_customer_registration_password_mismatch_fails(self):
        """Verify that mismatched password confirmation returns HTTP 400."""
        payload = {
            "email": "mismatch@gmail.com",
            "password": self.valid_password,
            "password_confirm": "DifferentPassword123!"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_registration_short_password_fails(self):
        """Verify that password less than 6 chars returns HTTP 400."""
        payload = {
            "email": "shortpass@gmail.com",
            "password": "123"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_can_login_with_gmail_and_password(self):
        """
        Verify that a registered customer can log in using their email and password,
        receiving Bearer access and refresh tokens.
        """
        # Register user first
        user = User.objects.create_user(
            username="testuser",
            email=self.valid_email,
            password=self.valid_password,
            first_name="Nahid",
            last_name="Hasan"
        )
        user.customer_profile.phone_number = "+8801811111111"
        user.customer_profile.save()

        login_payload = {
            "email": self.valid_email,
            "password": self.valid_password
        }
        response = self.client.post(self.login_url, login_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('token_type'), 'Bearer')
        self.assertTrue('access_token' in response.data)
        self.assertTrue('refresh_token' in response.data)
        self.assertEqual(response.data['user']['email'], self.valid_email)
        self.assertEqual(response.data['user']['first_name'], "Nahid")
        self.assertEqual(response.data['user']['phone_number'], "+8801811111111")

    def test_customer_login_with_invalid_credentials_fails(self):
        """Verify that invalid password returns HTTP 400."""
        User.objects.create_user(
            username="validuser",
            email=self.valid_email,
            password=self.valid_password
        )

        bad_payload = {
            "email": self.valid_email,
            "password": "WrongPassword!"
        }
        response = self.client.post(self.login_url, bad_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_profile_requires_authentication(self):
        """Verify unauthenticated request to profile endpoint returns HTTP 401."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_can_view_profile_with_bearer_token(self):
        """Verify authenticated customer can view profile using Bearer token."""
        user = User.objects.create_user(
            username="profileuser",
            email=self.valid_email,
            password=self.valid_password,
            first_name="Customer",
            last_name="One"
        )

        login_res = self.client.post(self.login_url, {
            "email": self.valid_email,
            "password": self.valid_password
        }, format='json')
        access_token = login_res.data['access_token']

        # Request profile with Bearer token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        profile_res = self.client.get(self.profile_url)

        self.assertEqual(profile_res.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_res.data['email'], self.valid_email)
        self.assertEqual(profile_res.data['first_name'], "Customer")

    def test_customer_can_update_profile(self):
        """Verify authenticated customer can update personal profile information."""
        user = User.objects.create_user(
            username="updateuser",
            email=self.valid_email,
            password=self.valid_password
        )

        login_res = self.client.post(self.login_url, {
            "email": self.valid_email,
            "password": self.valid_password
        }, format='json')
        access_token = login_res.data['access_token']

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        update_payload = {
            "first_name": "UpdatedName",
            "phone_number": "+8801999999999",
            "city": "Dhaka",
            "country": "Bangladesh"
        }
        res = self.client.patch(self.profile_url, update_payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['user']['first_name'], "UpdatedName")
        self.assertEqual(res.data['user']['phone_number'], "+8801999999999")
        self.assertEqual(res.data['user']['city'], "Dhaka")

    def test_customer_can_refresh_token(self):
        """Verify customer can refresh access token using refresh token."""
        User.objects.create_user(
            username="refreshuser",
            email=self.valid_email,
            password=self.valid_password
        )
        login_res = self.client.post(self.login_url, {
            "email": self.valid_email,
            "password": self.valid_password
        }, format='json')
        refresh_token = login_res.data['refresh_token']

        refresh_res = self.client.post(self.refresh_url, {"refresh": refresh_token}, format='json')
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertTrue('access' in refresh_res.data)

    def test_customer_profile_web_page_renders(self):
        """Verify that the dedicated /profile/ page loads with HTTP 200."""
        res = self.client.get('/profile/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertContains(res, "Customer Profile & Account Details")

    def test_customer_email_cannot_be_changed_and_password_can_be_updated(self):
        """Verify authenticated customer email cannot be changed while password/username can."""
        initial_email = "initial.email@gmail.com"
        user = User.objects.create_user(
            username="creduser",
            email=initial_email,
            password=self.valid_password
        )
        self.client.force_authenticate(user=user)

        attempted_new_email = "hacker.email@gmail.com"
        new_password = "NewSecurePassword456!"

        res = self.client.patch(self.profile_url, {
            "email": attempted_new_email,
            "username": "updated_username",
            "password": new_password
        }, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        # Email MUST remain unchanged
        self.assertEqual(user.email, initial_email)
        # Username and password MUST be updated
        self.assertEqual(user.username, "updated_username")
        self.assertTrue(user.check_password(new_password))
