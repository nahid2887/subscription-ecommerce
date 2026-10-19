from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class SuperuserAuthTests(APITestCase):
    def setUp(self):
        # Create a superuser
        self.superuser = User.objects.create_superuser(
            username='admin_test',
            email='admin@example.com',
            password='Password123!'
        )

        # Create a regular non-superuser
        self.regular_user = User.objects.create_user(
            username='regular_test',
            email='regular@example.com',
            password='Password123!'
        )

        self.login_url = reverse('superuser:superuser-login')
        self.profile_url = reverse('superuser:superuser-profile')

    def test_superuser_login_success(self):
        payload = {
            'username': 'admin_test',
            'password': 'Password123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertEqual(response.data.get('token_type'), 'Bearer')
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'admin_test')
        self.assertTrue(response.data['user']['is_superuser'])

    def test_superuser_login_with_email_success(self):
        payload = {
            'email': 'admin@example.com',
            'password': 'Password123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertEqual(response.data.get('token_type'), 'Bearer')
        self.assertEqual(response.data['user']['email'], 'admin@example.com')
        self.assertTrue(response.data['user']['is_superuser'])

    def test_regular_user_cannot_login_as_superuser(self):
        payload = {
            'username': 'regular_test',
            'password': 'Password123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Access denied', str(response.data))

    def test_access_protected_profile_with_bearer_token(self):
        # Log in first
        login_res = self.client.post(self.login_url, {
            'username': 'admin_test',
            'password': 'Password123!'
        }, format='json')
        access_token = login_res.data['access_token']

        # Access profile with Bearer header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_res = self.client.get(self.profile_url)
        self.assertEqual(profile_res.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_res.data['user']['username'], 'admin_test')

    def test_patch_profile_name_success(self):
        login_res = self.client.post(self.login_url, {
            'username': 'admin_test',
            'password': 'Password123!'
        }, format='json')
        access_token = login_res.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        patch_res = self.client.patch(self.profile_url, {
            'first_name': 'Super',
            'last_name': 'Commander'
        }, format='json')
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data['user']['first_name'], 'Super')
        self.assertEqual(patch_res.data['user']['last_name'], 'Commander')

    def test_patch_profile_cannot_change_username_or_email(self):
        login_res = self.client.post(self.login_url, {
            'username': 'admin_test',
            'password': 'Password123!'
        }, format='json')
        access_token = login_res.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Attempt to change username
        patch_res1 = self.client.patch(self.profile_url, {
            'username': 'hacked_admin'
        }, format='json')
        self.assertEqual(patch_res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Username cannot be changed', str(patch_res1.data))

        # Attempt to change email
        patch_res2 = self.client.patch(self.profile_url, {
            'email': 'hacked@example.com'
        }, format='json')
        self.assertEqual(patch_res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Email address cannot be changed', str(patch_res2.data))

    def test_patch_profile_change_password_success(self):
        login_res = self.client.post(self.login_url, {
            'username': 'admin_test',
            'password': 'Password123!'
        }, format='json')
        access_token = login_res.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        patch_res = self.client.patch(self.profile_url, {
            'current_password': 'Password123!',
            'new_password': 'NewSecretPassword456!',
            'confirm_password': 'NewSecretPassword456!'
        }, format='json')
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertTrue(patch_res.data.get('password_changed'))
        self.assertIn('access_token', patch_res.data)

        # Verify new password can log in
        new_login = self.client.post(self.login_url, {
            'username': 'admin_test',
            'password': 'NewSecretPassword456!'
        }, format='json')
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)

    def test_patch_profile_upload_avatar_multipart(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Log in
        login_res = self.client.post(self.login_url, {
            'username': 'admin_test',
            'password': 'Password123!'
        }, format='json')
        access_token = login_res.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Create dummy image
        file_obj = io.BytesIO()
        img = Image.new('RGB', (64, 64), color='green')
        img.save(file_obj, format='PNG')
        file_obj.seek(0)
        uploaded_image = SimpleUploadedFile('my_avatar.png', file_obj.read(), content_type='image/png')

        patch_res = self.client.patch(
            self.profile_url,
            {'avatar': uploaded_image, 'first_name': 'AvatarUser'},
            format='multipart'
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(patch_res.data['user']['avatar'])
        self.assertIn('.png', patch_res.data['user']['avatar'])
        self.assertEqual(patch_res.data['user']['first_name'], 'AvatarUser')

        # Check GET also reflects the avatar
        get_res = self.client.get(self.profile_url)
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(get_res.data['user']['avatar'])

    def test_patch_profile_upload_avatar_base64(self):
        import io
        import base64
        from PIL import Image

        login_res = self.client.post(self.login_url, {
            'username': 'admin_test',
            'password': 'Password123!'
        }, format='json')
        access_token = login_res.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Create dummy image in base64
        file_obj = io.BytesIO()
        img = Image.new('RGB', (64, 64), color='purple')
        img.save(file_obj, format='JPEG')
        file_obj.seek(0)
        b64_str = f"data:image/jpeg;base64,{base64.b64encode(file_obj.read()).decode('utf-8')}"

        patch_res = self.client.patch(
            self.profile_url,
            {'avatar': b64_str, 'last_name': 'Base64Tester'},
            format='json'
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(patch_res.data['user']['avatar'])
        self.assertEqual(patch_res.data['user']['last_name'], 'Base64Tester')

    def test_super_admin_products_page_renders_html_and_json(self):
        """
        Verify that /super-admin/products/ renders HTML in browser and JSON for API clients.
        """
        url = reverse('super-admin-products')
        # Test HTML render
        html_res = self.client.get(url, HTTP_ACCEPT='text/html')
        self.assertEqual(html_res.status_code, status.HTTP_200_OK)
        self.assertIn('Products & Subscription Plans', html_res.content.decode('utf-8'))

        # Test JSON render
        json_res = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(json_res.status_code, status.HTTP_200_OK)
        self.assertIn('products', json_res.data)
