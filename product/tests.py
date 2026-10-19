import io
from PIL import Image
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Category, Product, ProductPlan


def create_test_image_file():
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='blue')
    image.save(file, 'jpeg')
    file.name = 'test_image.jpg'
    file.seek(0)
    return file


class ProductAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create Super Admin
        self.superuser = User.objects.create_superuser(
            username='admin_boss',
            email='admin@example.com',
            password='AdminPassword123!',
            first_name='Super',
            last_name='Admin'
        )
        refresh = RefreshToken.for_user(self.superuser)
        self.superuser_token = str(refresh.access_token)

        # Create Normal (Regular) User
        self.normal_user = User.objects.create_user(
            username='regular_user',
            email='user@example.com',
            password='UserPassword123!',
            first_name='John',
            last_name='Doe'
        )
        normal_refresh = RefreshToken.for_user(self.normal_user)
        self.normal_user_token = str(normal_refresh.access_token)

        # Pre-create a Category
        self.category = Category.objects.create(
            name="Developer Tools",
            description="Software and cloud tools for developers"
        )

    def test_super_admin_can_create_product_with_all_fields(self):
        """
        Tests that a super admin can create a product with:
        name, category, features, multi-lingual description, warranty, delivery, and plans.
        Price must depend on the selected plan.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.superuser_token}')
        url = reverse('product:product-list-create')

        payload = {
            "name": "Cloud Workspace Suite",
            "category": self.category.name,
            "features": [
                "100GB Fast Storage",
                "Automated Nightly Backups",
                "24/7 Priority Support"
            ],
            "description": {
                "en": "Enterprise cloud workspace with multi-user collaboration.",
                "es": "Espacio de trabajo en la nube empresarial con colaboración.",
                "bn": "এন্টারপ্রাইজ ক্লাউড ওয়ার্কস্পেস মাল্টি-ইউজার সহযোগিতা সহ।",
                "fr": "Espace de travail cloud d'entreprise."
            },
            "warranty": "30-day full money-back guarantee",
            "delivery": "Instant digital provisioning within 30 seconds",
            "plans": [
                {
                    "name": "Monthly Starter",
                    "price": 29.99,
                    "currency": "USD",
                    "billing_cycle": "monthly",
                    "is_default": True
                },
                {
                    "name": "Annual Pro",
                    "price": 299.00,
                    "currency": "USD",
                    "billing_cycle": "yearly",
                    "is_default": False
                }
            ]
        }

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data['product']

        self.assertEqual(data['name'], "Cloud Workspace Suite")
        self.assertEqual(data['category']['name'], "Developer Tools")
        self.assertEqual(len(data['features']), 3)
        self.assertEqual(data['warranty'], "30-day full money-back guarantee")
        self.assertEqual(data['delivery'], "Instant digital provisioning within 30 seconds")
        self.assertEqual(len(data['plans']), 2)

        # Verify that price depends on selected plan (default plan is Monthly Starter = 29.99)
        self.assertEqual(float(data['price']), 29.99)
        self.assertEqual(data['selected_plan']['name'], "Monthly Starter")
        self.assertEqual(float(data['selected_plan']['price']), 29.99)

        # Verify multi-lingual description
        self.assertIn("bn", data['description'])
        self.assertIn("es", data['description'])
        self.assertEqual(data['localized_description'], "Enterprise cloud workspace with multi-user collaboration.")

        # Verify created_by attribution
        self.assertEqual(data['created_by']['username'], 'admin_boss')

    def test_super_admin_create_with_multipart_image_upload(self):
        """
        Tests multipart/form-data creation with uploaded image file.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.superuser_token}')
        url = reverse('product:product-list-create')

        image_file = create_test_image_file()
        payload = {
            'name': 'Hardware Security Key',
            'category': 'Security Hardware',
            'features': '["FIDO2 Certified", "NFC Enabled", "Waterproof"]',
            'description': '{"en": "Ultra secure hardware security token"}',
            'warranty': '2-Year Manufacturer Warranty',
            'delivery': 'Express Courier delivery in 2 business days',
            'image': image_file,
            'plans': '[{"name": "One-time Purchase", "price": 49.95, "billing_cycle": "lifetime", "is_default": true}]'
        }

        response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['product']['image'])
        self.assertEqual(float(response.data['product']['price']), 49.95)

    def test_super_admin_create_with_base64_image(self):
        """
        Tests creating a product with Base64 image payload in JSON.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.superuser_token}')
        url = reverse('product:product-list-create')

        base64_img = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        payload = {
            "name": "AI Assistant Subscription",
            "category": "Artificial Intelligence",
            "image": base64_img,
            "features": ["GPT-5 API Access", "Infinite Context Window"],
            "description": "Next-gen intelligent assistant",
            "warranty": "99.99% uptime SLA",
            "delivery": "Immediate API token activation",
            "selected_plan": {
                "name": "Unlimited AI Plan",
                "price": 99.00,
                "billing_cycle": "monthly"
            }
        }

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['product']['image'])
        self.assertEqual(float(response.data['product']['price']), 99.00)
        self.assertEqual(response.data['product']['description'], {'en': 'Next-gen intelligent assistant'})

    def test_unauthenticated_user_cannot_create_product(self):
        """
        Unauthenticated requests must be rejected with 401 Unauthorized.
        """
        url = reverse('product:product-list-create')
        payload = {"name": "Unauthorized Product"}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_cannot_create_product(self):
        """
        Non-superuser authenticated requests must be rejected with 403 Forbidden.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.normal_user_token}')
        url = reverse('product:product-list-create')
        payload = {"name": "Hacker Attempt Product"}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], "You must be a superuser to access this endpoint.")

    def test_price_depends_on_selected_plan_and_plan_switching(self):
        """
        Verifies that product price depends on the selected plan,
        and switching the selected plan immediately updates the product price.
        """
        # Create product with 2 plans
        product = Product.objects.create(
            name="Streaming Service VIP",
            features=["4K Ultra HD", "Spatial Audio"],
            description={"en": "Watch unlimited movies in 4K", "es": "Mira películas ilimitadas en 4K"}
        )
        plan_monthly = ProductPlan.objects.create(
            product=product,
            name="Monthly Plan",
            price=14.99,
            billing_cycle="monthly",
            is_default=True
        )
        plan_annual = ProductPlan.objects.create(
            product=product,
            name="Annual Plan",
            price=120.00,
            billing_cycle="yearly",
            is_default=False
        )
        product.selected_plan = plan_monthly
        product.save()

        # Initial price should be monthly (14.99)
        self.assertEqual(float(product.price), 14.99)

        # Switch selected plan to Annual Plan (120.00)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.superuser_token}')
        switch_url = reverse('product:product-select-plan', kwargs={'pk': product.pk})
        response = self.client.post(switch_url, {"plan_id": plan_annual.pk}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['product']['price']), 120.00)
        self.assertEqual(response.data['product']['selected_plan']['id'], plan_annual.pk)

        # Refresh from db
        product.refresh_from_db()
        self.assertEqual(float(product.price), 120.00)
        self.assertEqual(product.selected_plan, plan_annual)

    def test_multi_language_description_accept_language_and_param(self):
        """
        Verifies that Accept-Language header and ?lang= query param return appropriate language.
        """
        product = Product.objects.create(
            name="Global VPN Proxy",
            description={
                "en": "Fast and private global internet access.",
                "es": "Acceso a internet global rápido y privado.",
                "fr": "Accès Internet mondial rapide et privé.",
                "bn": "দ্রুত এবং নিরাপদ বৈশ্বিক ইন্টারনেট সেবা।"
            }
        )
        detail_url = reverse('product:product-detail', kwargs={'pk': product.pk})

        # Test query parameter ?lang=es
        res_es = self.client.get(f"{detail_url}?lang=es")
        self.assertEqual(res_es.status_code, status.HTTP_200_OK)
        self.assertEqual(res_es.data['product']['localized_description'], "Acceso a internet global rápido y privado.")

        # Test query parameter ?lang=bn
        res_bn = self.client.get(f"{detail_url}?lang=bn")
        self.assertEqual(res_bn.status_code, status.HTTP_200_OK)
        self.assertEqual(res_bn.data['product']['localized_description'], "দ্রুত এবং নিরাপদ বৈশ্বিক ইন্টারনেট সেবা।")

        # Test HTTP Accept-Language: fr
        res_fr = self.client.get(detail_url, HTTP_ACCEPT_LANGUAGE='fr-FR,fr;q=0.9,en;q=0.8')
        self.assertEqual(res_fr.status_code, status.HTTP_200_OK)
        self.assertEqual(res_fr.data['product']['localized_description'], "Accès Internet mondial rapide et privé.")

    def test_super_admin_can_update_and_delete_product(self):
        """
        Verifies Super Admin can PATCH and DELETE products.
        """
        product = Product.objects.create(
            name="Legacy Product",
            warranty="Old Warranty",
            delivery="Standard Delivery"
        )
        detail_url = reverse('product:product-detail', kwargs={'pk': product.pk})

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.superuser_token}')

        # PATCH update
        update_res = self.client.patch(detail_url, {
            "name": "Updated Modern Product",
            "warranty": "Lifetime Warranty",
            "features": ["All Features Unlocked"]
        }, format='json')
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        self.assertEqual(update_res.data['product']['name'], "Updated Modern Product")
        self.assertEqual(update_res.data['product']['warranty'], "Lifetime Warranty")

        # DELETE
        delete_res = self.client.delete(detail_url)
        self.assertEqual(delete_res.status_code, status.HTTP_200_OK)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_product_with_multiple_plans_selection_and_update(self):
        """
        Verifies that a product can be created with multiple plans (e.g., Monthly, Quarterly, Yearly, Lifetime),
        and that updating the product retains multiple plans and accurately sets the primary selected plan.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.superuser_token}')
        url = reverse('product:product-list-create')

        payload = {
            "name": "Multi-Plan SaaS Suite",
            "category": "Software",
            "description": "Powerful SaaS product with multiple tiers.",
            "warranty": "30 Days Refund",
            "delivery": "Instant",
            "plans": [
                {"name": "Monthly Starter", "price": 19.99, "billing_cycle": "monthly", "is_default": True},
                {"name": "Quarterly Growth", "price": 49.99, "billing_cycle": "quarterly", "is_default": False},
                {"name": "Annual Pro", "price": 179.99, "billing_cycle": "yearly", "is_default": False},
                {"name": "Lifetime VIP", "price": 499.00, "billing_cycle": "lifetime", "is_default": False}
            ]
        }

        # Create product with 4 plans
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        product_data = res.data['product']
        self.assertEqual(len(product_data['plans']), 4)
        self.assertEqual(float(product_data['price']), 19.99)
        self.assertEqual(product_data['selected_plan']['name'], "Monthly Starter")

        product_id = product_data['id']
        detail_url = reverse('product:product-detail', kwargs={'pk': product_id})

        # Update: switch default to Annual Pro and update price of Quarterly
        quarterly_plan_id = [p['id'] for p in product_data['plans'] if p['name'] == 'Quarterly Growth'][0]
        annual_plan_id = [p['id'] for p in product_data['plans'] if p['name'] == 'Annual Pro'][0]

        update_payload = {
            "plans": [
                {"id": annual_plan_id, "name": "Annual Pro", "price": 169.99, "billing_cycle": "yearly", "is_default": True},
                {"id": quarterly_plan_id, "name": "Quarterly Plus", "price": 54.99, "billing_cycle": "quarterly", "is_default": False},
            ],
            "selected_plan_id": annual_plan_id
        }

        update_res = self.client.patch(detail_url, update_payload, format='json')
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        updated_data = update_res.data['product']

        # Verifies 2 plans retained and primary price mirrors Annual Pro ($169.99)
        self.assertEqual(len(updated_data['plans']), 2)
        self.assertEqual(float(updated_data['price']), 169.99)
        self.assertEqual(updated_data['selected_plan']['name'], "Annual Pro")

    def test_product_with_taka_currency_and_device_plans(self):
        """
        Verifies that a product can be created with 1 Device and 2 Devices plans
        priced in Bangladeshi Taka (BDT) with currency symbol '৳'.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.superuser_token}')
        url = reverse('product:product-list-create')

        payload = {
            "name": "Secure VPN Proxy",
            "category": "VPN Services",
            "description": "High-speed encrypted VPN service supporting 1 or 2 devices.",
            "warranty": "7 Days Money-Back Guarantee",
            "delivery": "Instant Activation via Email",
            "plans": [
                {
                    "name": "1 Device Plan",
                    "price": 350.00,
                    "currency": "BDT",
                    "devices": 1,
                    "billing_cycle": "monthly",
                    "is_default": True
                },
                {
                    "name": "2 Devices Plan",
                    "price": 600.00,
                    "currency": "BDT",
                    "devices": 2,
                    "billing_cycle": "monthly",
                    "is_default": False
                }
            ]
        }

        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        product = res.data['product']

        self.assertEqual(product['currency'], 'BDT')
        self.assertEqual(product['currency_symbol'], '৳')
        self.assertEqual(float(product['price']), 350.00)
        self.assertEqual(len(product['plans']), 2)

        plan_1_dev = [p for p in product['plans'] if p['name'] == '1 Device Plan'][0]
        plan_2_dev = [p for p in product['plans'] if p['name'] == '2 Devices Plan'][0]

        self.assertEqual(plan_1_dev['devices'], 1)
        self.assertEqual(plan_1_dev['currency_symbol'], '৳')
        self.assertEqual(float(plan_1_dev['price']), 350.00)

        self.assertEqual(plan_2_dev['devices'], 2)
        self.assertEqual(plan_2_dev['currency_symbol'], '৳')
        self.assertEqual(float(plan_2_dev['price']), 600.00)

    def test_public_user_can_view_product_list_and_details_by_id_and_slug(self):
        """
        Verifies that any unauthenticated/public user can:
        1. View product list via GET /api/products/
        2. View product details via GET /api/products/<int:pk>/
        3. View product details via GET /api/products/<slug:slug>/
        4. Inactive products are hidden from public users.
        """
        # Ensure client is completely unauthenticated (anonymous public user)
        self.client.credentials()

        active_product = Product.objects.create(
            name="Public Cloud Starter",
            slug="public-cloud-starter",
            description={"en": "Great starter cloud for everyone"},
            warranty="14 days refund",
            delivery="Instant",
            is_active=True
        )
        plan1 = ProductPlan.objects.create(
            product=active_product,
            name="Starter Monthly",
            price=9.99,
            currency="USD",
            is_default=True
        )
        active_product.selected_plan = plan1
        active_product.save()

        inactive_product = Product.objects.create(
            name="Draft Product",
            slug="draft-product",
            is_active=False
        )

        # 1. Test Public List endpoint
        list_url = reverse('product:product-list-create')
        res_list = self.client.get(list_url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        returned_ids = [p['id'] for p in res_list.data['products']]
        self.assertIn(active_product.id, returned_ids)
        self.assertNotIn(inactive_product.id, returned_ids)

        # 2. Test Public Detail by PK
        detail_pk_url = reverse('product:product-detail', kwargs={'pk': active_product.pk})
        res_detail_pk = self.client.get(detail_pk_url)
        self.assertEqual(res_detail_pk.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail_pk.data['product']['name'], "Public Cloud Starter")
        self.assertEqual(float(res_detail_pk.data['product']['price']), 9.99)
        self.assertEqual(len(res_detail_pk.data['product']['plans']), 1)

        # 3. Test Public Detail by Slug
        detail_slug_url = reverse('product:product-detail-slug', kwargs={'slug': active_product.slug})
        res_detail_slug = self.client.get(detail_slug_url)
        self.assertEqual(res_detail_slug.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail_slug.data['product']['id'], active_product.id)
        self.assertEqual(res_detail_slug.data['product']['slug'], "public-cloud-starter")

        # 4. Inactive product detail should return 404 for public users
        inactive_url = reverse('product:product-detail', kwargs={'pk': inactive_product.pk})
        res_inactive = self.client.get(inactive_url)
        self.assertEqual(res_inactive.status_code, status.HTTP_404_NOT_FOUND)
