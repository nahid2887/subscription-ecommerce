from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from terms.models import TermsAndConditions


class TermsAndConditionsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Regular customer user (authenticated but NOT superuser)
        self.customer_user = User.objects.create_user(
            username='customer_jane',
            email='jane@example.com',
            password='Password123!',
            is_staff=False,
            is_superuser=False
        )

        # Super Admin user (authenticated AND superuser)
        self.super_admin = User.objects.create_superuser(
            username='super_admin',
            email='admin@subverse.io',
            password='AdminPassword123!',
            is_staff=True,
            is_superuser=True
        )

        # Pre-seed an initial Terms and Conditions document
        self.initial_terms = TermsAndConditions.objects.create(
            title="Initial Terms of Service",
            content="These are the initial terms and conditions of Subverse.",
            version="1.0",
            is_active=True,
            created_by=self.super_admin,
            updated_by=self.super_admin
        )

    # ==========================================
    # 1. ANONYMOUS / GUEST USERS (PUBLIC ACCESS)
    # ==========================================
    def test_anonymous_user_can_view_active_terms(self):
        """Any unauthenticated user can view/show the active terms."""
        response = self.client.get('/api/terms/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Initial Terms of Service")
        self.assertEqual(response.data['version'], "1.0")
        self.assertTrue(response.data['is_active'])

    def test_anonymous_user_can_view_via_alias_url(self):
        """Any user can also view terms via /api/terms-and-conditions/."""
        response = self.client.get('/api/terms-and-conditions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.initial_terms.id)

    def test_anonymous_user_can_view_terms_by_id(self):
        """Any unauthenticated user can show terms by specific ID."""
        response = self.client.get(f'/api/terms/{self.initial_terms.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.initial_terms.id)

    def test_anonymous_user_can_view_terms_history(self):
        """Any unauthenticated user can view terms history."""
        response = self.client.get('/api/terms/history/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_anonymous_user_cannot_create_terms(self):
        """Unauthenticated user cannot create terms (401 Unauthorized)."""
        payload = {
            "title": "Hacked Terms",
            "content": "Malicious content",
            "version": "9.9"
        }
        response = self.client.post('/api/terms/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_user_cannot_edit_active_terms(self):
        """Unauthenticated user cannot edit active terms via PUT or PATCH."""
        payload = {"title": "Updated by Anonymous", "content": "Updated content"}
        put_response = self.client.put('/api/terms/', payload, format='json')
        patch_response = self.client.patch('/api/terms/', payload, format='json')
        self.assertEqual(put_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(patch_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_user_cannot_delete_terms(self):
        """Unauthenticated user cannot delete terms."""
        response = self.client.delete(f'/api/terms/{self.initial_terms.id}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ==========================================
    # 2. REGULAR AUTHENTICATED CUSTOMER USERS
    # ==========================================
    def test_customer_user_can_view_active_terms(self):
        """Logged-in customer can show/view the active terms."""
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.get('/api/terms/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Initial Terms of Service")

    def test_customer_user_cannot_create_terms(self):
        """Regular customer cannot create terms (403 Forbidden)."""
        self.client.force_authenticate(user=self.customer_user)
        payload = {
            "title": "Customer Terms",
            "content": "Customer trying to create terms",
            "version": "2.0"
        }
        response = self.client.post('/api/terms/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_user_cannot_edit_active_terms(self):
        """Regular customer cannot edit terms via PUT or PATCH (403 Forbidden)."""
        self.client.force_authenticate(user=self.customer_user)
        payload = {"title": "Customer Edit", "content": "Updated content"}
        put_resp = self.client.put('/api/terms/', payload, format='json')
        patch_resp = self.client.patch('/api/terms/', payload, format='json')
        self.assertEqual(put_resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(patch_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_user_cannot_edit_terms_by_id(self):
        """Regular customer cannot edit terms by ID (403 Forbidden)."""
        self.client.force_authenticate(user=self.customer_user)
        payload = {"title": "Customer Attempt", "content": "Modified"}
        response = self.client.put(f'/api/terms/{self.initial_terms.id}/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_user_cannot_delete_terms(self):
        """Regular customer cannot delete terms (403 Forbidden)."""
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.delete(f'/api/terms/{self.initial_terms.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================
    # 3. SUPER ADMIN USERS (FULL ACCESS / EDIT)
    # ==========================================
    def test_super_admin_can_create_new_terms(self):
        """Super admin can create a new version of Terms and Conditions."""
        self.client.force_authenticate(user=self.super_admin)
        payload = {
            "title": "Subverse Platform Terms & Conditions 2026",
            "content": "All buyers agree to digital warranty and instant delivery policies.",
            "version": "2.0",
            "is_active": True
        }
        response = self.client.post('/api/terms/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], payload['title'])
        self.assertEqual(response.data['version'], "2.0")
        self.assertTrue(response.data['is_active'])
        self.assertEqual(response.data['created_by']['username'], self.super_admin.username)

        # Verify old terms are now marked inactive
        self.initial_terms.refresh_from_db()
        self.assertFalse(self.initial_terms.is_active)

    def test_super_admin_can_full_update_active_terms(self):
        """Super admin can perform PUT update on active terms."""
        self.client.force_authenticate(user=self.super_admin)
        payload = {
            "title": "Updated Super Admin Terms",
            "content": "Completely revamped terms and conditions.",
            "version": "1.2",
            "is_active": True
        }
        response = self.client.put('/api/terms/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Updated Super Admin Terms")
        self.assertEqual(response.data['content'], "Completely revamped terms and conditions.")
        self.assertEqual(response.data['version'], "1.2")
        self.assertEqual(response.data['updated_by']['username'], self.super_admin.username)

    def test_super_admin_can_partial_update_active_terms(self):
        """Super admin can perform PATCH update on active terms."""
        self.client.force_authenticate(user=self.super_admin)
        payload = {
            "content": "Surgically updated content without modifying title or version."
        }
        response = self.client.patch('/api/terms/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], payload['content'])
        self.assertEqual(response.data['title'], self.initial_terms.title)

    def test_super_admin_can_update_terms_by_id(self):
        """Super admin can update terms targeting specific ID."""
        self.client.force_authenticate(user=self.super_admin)
        payload = {
            "title": "Specific Terms Update",
            "content": "Specific content update.",
            "version": "1.0.1",
            "is_active": True
        }
        response = self.client.put(f'/api/terms/{self.initial_terms.id}/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Specific Terms Update")

    def test_super_admin_can_delete_terms_by_id(self):
        """Super admin can delete a terms document."""
        # Create a second terms record first
        older_terms = TermsAndConditions.objects.create(
            title="Archived Terms v0.9",
            content="Old content",
            version="0.9",
            is_active=False
        )

        self.client.force_authenticate(user=self.super_admin)
        response = self.client.delete(f'/api/terms/{self.initial_terms.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(TermsAndConditions.objects.filter(id=self.initial_terms.id).exists())

        # Older terms should now be promoted to active
        older_terms.refresh_from_db()
        self.assertTrue(older_terms.is_active)

    def test_auto_initialization_when_no_terms_exist(self):
        """When table is empty, GET /api/terms/ seamlessly bootstraps a default document."""
        TermsAndConditions.objects.all().delete()
        self.assertEqual(TermsAndConditions.objects.count(), 0)

        response = self.client.get('/api/terms/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Terms and Conditions")
        self.assertTrue(TermsAndConditions.objects.filter(is_active=True).exists())
