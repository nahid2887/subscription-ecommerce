from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from customer.models import SavedProduct, CustomerCartItem
from product.models import Category, Product, ProductPlan




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


class CustomerSavedProductTests(APITestCase):
    def setUp(self):
        # Create Category
        self.category = Category.objects.create(
            name="Productivity & AI",
            description="Tools for work and AI"
        )
        self.category2 = Category.objects.create(
            name="Streaming & Entertainment",
            description="Media and video platforms"
        )

        # Create Products
        self.product1 = Product.objects.create(
            name="ChatGPT Plus Subscription",
            category=self.category,
            description={"en": "GPT-4o access and high-speed processing"},
            features=["24/7 Access", "Plugins"]
        )
        self.plan1 = ProductPlan.objects.create(
            product=self.product1,
            name="Monthly Plan",
            price=2400.00,
            currency="BDT",
            billing_cycle="monthly",
            is_default=True
        )

        self.product2 = Product.objects.create(
            name="Netflix 4K Ultra HD",
            category=self.category2,
            description={"en": "4 screens simultaneous streaming"},
            features=["4K HDR", "4 Screens"]
        )
        self.plan2 = ProductPlan.objects.create(
            product=self.product2,
            name="1 Screen Profile",
            price=350.00,
            currency="BDT",
            billing_cycle="monthly",
            is_default=True
        )

        # Create Customers
        self.customer1 = User.objects.create_user(
            username="customer_one",
            email="cust1@gmail.com",
            password="Password123!"
        )
        self.customer2 = User.objects.create_user(
            username="customer_two",
            email="cust2@gmail.com",
            password="Password123!"
        )

        # Saved Products URLs
        self.saved_products_url = reverse('customer:saved-product-list-create')
        self.saved_toggle_url = reverse('customer:saved-product-toggle')

    def test_unauthenticated_request_is_rejected(self):
        """Unauthenticated customer cannot view or save products."""
        # GET
        get_res = self.client.get(self.saved_products_url)
        self.assertEqual(get_res.status_code, status.HTTP_401_UNAUTHORIZED)

        # POST
        post_res = self.client.post(self.saved_products_url, {"product_id": self.product1.id})
        self.assertEqual(post_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_can_save_product_successfully(self):
        """Authenticated customer can save a product and gets back full product details."""
        self.client.force_authenticate(user=self.customer1)

        payload = {
            "product_id": self.product1.id,
            "notes": "Interested in renewing next week"
        }
        res = self.client.post(self.saved_products_url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['is_saved'])
        self.assertEqual(res.data['product_id'], self.product1.id)
        self.assertIn('saved_product', res.data)
        self.assertEqual(res.data['saved_product']['notes'], "Interested in renewing next week")
        self.assertEqual(res.data['saved_product']['product']['name'], "ChatGPT Plus Subscription")
        self.assertEqual(float(res.data['saved_product']['product']['price']), 2400.00)

        # Verify record in DB
        self.assertTrue(
            SavedProduct.objects.filter(user=self.customer1, product=self.product1).exists()
        )

    def test_customer_can_save_product_by_slug(self):
        """Customer can also save using the product slug."""
        self.client.force_authenticate(user=self.customer1)

        payload = {
            "slug": self.product2.slug
        }
        res = self.client.post(self.saved_products_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['product_id'], self.product2.id)

    def test_customer_saving_duplicate_product_is_idempotent(self):
        """Saving the same product twice does not throw an error and updates notes if provided."""
        self.client.force_authenticate(user=self.customer1)

        # First save
        res1 = self.client.post(self.saved_products_url, {"product_id": self.product1.id}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Second save with updated notes
        res2 = self.client.post(self.saved_products_url, {
            "product_id": self.product1.id,
            "notes": "Updated note"
        }, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data['is_saved'])
        self.assertEqual(res2.data['saved_product']['notes'], "Updated note")

        # Ensure only 1 record exists in DB
        count = SavedProduct.objects.filter(user=self.customer1, product=self.product1).count()
        self.assertEqual(count, 1)

    def test_customer_can_view_his_own_saved_products(self):
        """
        Customer can see his own saved products, with complete nested product & pricing details.
        Ensures strict data isolation between different customer users.
        """
        # Save product 1 and 2 for customer 1
        SavedProduct.objects.create(user=self.customer1, product=self.product1, notes="Note 1")
        SavedProduct.objects.create(user=self.customer1, product=self.product2, notes="Note 2")

        # Save product 2 for customer 2
        SavedProduct.objects.create(user=self.customer2, product=self.product2, notes="Customer 2 private note")

        # Authenticate as customer 1
        self.client.force_authenticate(user=self.customer1)
        res = self.client.get(self.saved_products_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 2)
        saved_items = res.data['saved_products']
        self.assertEqual(len(saved_items), 2)

        returned_product_ids = [item['product']['id'] for item in saved_items]
        self.assertIn(self.product1.id, returned_product_ids)
        self.assertIn(self.product2.id, returned_product_ids)

        # Verify customer 1 cannot see customer 2's notes
        returned_notes = [item['notes'] for item in saved_items]
        self.assertNotIn("Customer 2 private note", returned_notes)

        # Authenticate as customer 2
        self.client.force_authenticate(user=self.customer2)
        res2 = self.client.get(self.saved_products_url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['count'], 1)
        self.assertEqual(res2.data['saved_products'][0]['product']['id'], self.product2.id)

    def test_customer_saved_products_search_and_filter(self):
        """Customer can filter saved products by search keyword and category."""
        SavedProduct.objects.create(user=self.customer1, product=self.product1)
        SavedProduct.objects.create(user=self.customer1, product=self.product2)

        self.client.force_authenticate(user=self.customer1)

        # Search by name
        res = self.client.get(self.saved_products_url, {'search': 'ChatGPT'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['saved_products'][0]['product']['name'], "ChatGPT Plus Subscription")

        # Filter by category
        res_cat = self.client.get(self.saved_products_url, {'category': self.category2.slug})
        self.assertEqual(res_cat.status_code, status.HTTP_200_OK)
        self.assertEqual(res_cat.data['count'], 1)
        self.assertEqual(res_cat.data['saved_products'][0]['product']['name'], "Netflix 4K Ultra HD")

    def test_customer_can_delete_saved_product(self):
        """Customer can remove a product from their saved items list."""
        SavedProduct.objects.create(user=self.customer1, product=self.product1)
        self.client.force_authenticate(user=self.customer1)

        delete_url = reverse('customer:saved-product-detail', kwargs={'product_id': self.product1.id})
        res = self.client.delete(delete_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['is_saved'])
        self.assertFalse(
            SavedProduct.objects.filter(user=self.customer1, product=self.product1).exists()
        )

        # Deleting again returns 404
        res_again = self.client.delete(delete_url)
        self.assertEqual(res_again.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_can_toggle_saved_product(self):
        """Customer can toggle saved state using the toggle endpoint."""
        self.client.force_authenticate(user=self.customer1)

        # 1. Toggle ON
        res1 = self.client.post(self.saved_toggle_url, {"product_id": self.product1.id}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res1.data['is_saved'])
        self.assertTrue(SavedProduct.objects.filter(user=self.customer1, product=self.product1).exists())

        # 2. Toggle OFF
        res2 = self.client.post(self.saved_toggle_url, {"product_id": self.product1.id}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertFalse(res2.data['is_saved'])
        self.assertFalse(SavedProduct.objects.filter(user=self.customer1, product=self.product1).exists())

    def test_check_product_saved_status(self):
        """Customer can query whether a specific product is in their saved list."""
        self.client.force_authenticate(user=self.customer1)

        check_url = reverse('customer:saved-product-check', kwargs={'product_id': self.product1.id})

        # Initially false
        res1 = self.client.get(check_url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertFalse(res1.data['is_saved'])

        # Save product
        SavedProduct.objects.create(user=self.customer1, product=self.product1)

        # Now true
        res2 = self.client.get(check_url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data['is_saved'])
        self.assertIsNotNone(res2.data['saved_product_id'])

    def test_product_save_toggle_endpoint(self):
        """Verify the direct product save endpoint /api/products/<pk>/save/."""
        self.client.force_authenticate(user=self.customer1)

        prod_save_url = reverse('product:product-save-toggle', kwargs={'pk': self.product1.id})
        res = self.client.post(prod_save_url, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['is_saved'])

        # Toggle off
        res_off = self.client.post(prod_save_url, format='json')
        self.assertEqual(res_off.status_code, status.HTTP_200_OK)
        self.assertFalse(res_off.data['is_saved'])

    def test_saving_non_existent_product_returns_400(self):
        """Attempting to save an invalid product ID returns HTTP 400."""
        self.client.force_authenticate(user=self.customer1)
        res = self.client.post(self.saved_products_url, {"product_id": 999999}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class CustomerCartTests(APITestCase):
    def setUp(self):
        # Create Category
        self.category = Category.objects.create(
            name="Cloud Storage & Backup",
            description="Secure file storage"
        )

        # Create Product & Plans
        self.product = Product.objects.create(
            name="Google One 2TB Cloud",
            category=self.category,
            description={"en": "2TB Google Drive, Gmail, and Photos storage"},
            features=["2TB Storage", "Family Sharing"]
        )
        self.plan_monthly = ProductPlan.objects.create(
            product=self.product,
            name="Monthly Plan",
            price=250.00,
            currency="BDT",
            billing_cycle="monthly",
            is_default=True
        )
        self.plan_yearly = ProductPlan.objects.create(
            product=self.product,
            name="Yearly Plan (Save 15%)",
            price=2500.00,
            currency="BDT",
            billing_cycle="yearly",
            is_default=False
        )

        # Customers
        self.customer1 = User.objects.create_user(
            username="buyer1",
            email="buyer1@gmail.com",
            password="SecurePassword123!"
        )
        self.customer2 = User.objects.create_user(
            username="buyer2",
            email="buyer2@gmail.com",
            password="SecurePassword123!"
        )

        self.cart_url = reverse('customer:cart')

    def test_unauthenticated_cart_access_rejected(self):
        """Unauthenticated customer cannot view or modify cart."""
        res_get = self.client.get(self.cart_url)
        self.assertEqual(res_get.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Authentication credentials were not provided", res_get.data['detail'])

        res_post = self.client.post(self.cart_url, {"product_id": self.product.id})
        self.assertEqual(res_post.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Authentication credentials were not provided", res_post.data['detail'])

        # Detail endpoint also rejected
        detail_url = reverse('customer:cart-item-detail', kwargs={'item_id': 1})
        res_patch = self.client.patch(detail_url, {"quantity": 2})
        self.assertEqual(res_patch.status_code, status.HTTP_401_UNAUTHORIZED)
        res_delete = self.client.delete(detail_url)
        self.assertEqual(res_delete.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_customer_can_add_item_to_cart(self):
        """Authenticated customer can add a product with specific plan tier to cart."""
        self.client.force_authenticate(user=self.customer1)

        payload = {
            "product_id": self.product.id,
            "plan_id": self.plan_monthly.id,
            "quantity": 1
        }
        res = self.client.post(self.cart_url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("added to your cart", res.data['message'])
        self.assertEqual(res.data['cart']['items_count'], 1)
        self.assertEqual(res.data['cart']['total_quantity'], 1)
        self.assertEqual(float(res.data['cart']['total_amount']), 250.00)

        # Verify DB
        item = CustomerCartItem.objects.filter(user=self.customer1, product=self.product).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.plan.id, self.plan_monthly.id)

    def test_adding_same_product_and_plan_increments_quantity(self):
        """Adding the exact same item with same plan increments the existing item quantity."""
        self.client.force_authenticate(user=self.customer1)

        payload = {
            "product_id": self.product.id,
            "plan_id": self.plan_monthly.id,
            "quantity": 1
        }
        self.client.post(self.cart_url, payload, format='json')

        # Add again with quantity 2
        payload['quantity'] = 2
        res2 = self.client.post(self.cart_url, payload, format='json')

        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['cart']['items_count'], 1)
        self.assertEqual(res2.data['cart']['total_quantity'], 3)
        self.assertEqual(float(res2.data['cart']['total_amount']), 750.00)

    def test_customer_can_view_own_cart_with_data_isolation(self):
        """Customer A only sees their own cart items, never Customer B's cart items."""
        # Customer 1 adds monthly
        CustomerCartItem.objects.create(
            user=self.customer1,
            product=self.product,
            plan=self.plan_monthly,
            quantity=2
        )
        # Customer 2 adds yearly
        CustomerCartItem.objects.create(
            user=self.customer2,
            product=self.product,
            plan=self.plan_yearly,
            quantity=1
        )

        # View as Customer 1
        self.client.force_authenticate(user=self.customer1)
        res1 = self.client.get(self.cart_url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['items_count'], 1)
        self.assertEqual(res1.data['total_quantity'], 2)
        self.assertEqual(float(res1.data['total_amount']), 500.00)
        self.assertEqual(res1.data['items'][0]['plan']['id'], self.plan_monthly.id)

        # View as Customer 2
        self.client.force_authenticate(user=self.customer2)
        res2 = self.client.get(self.cart_url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['items_count'], 1)
        self.assertEqual(res2.data['total_quantity'], 1)
        self.assertEqual(float(res2.data['total_amount']), 2500.00)
        self.assertEqual(res2.data['items'][0]['plan']['id'], self.plan_yearly.id)

    def test_customer_can_update_cart_quantity(self):
        """Customer can update the quantity of a cart item."""
        item = CustomerCartItem.objects.create(
            user=self.customer1,
            product=self.product,
            plan=self.plan_monthly,
            quantity=1
        )
        self.client.force_authenticate(user=self.customer1)

        detail_url = reverse('customer:cart-item-detail', kwargs={'item_id': item.id})
        res = self.client.patch(detail_url, {"quantity": 4}, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['cart']['total_quantity'], 4)
        self.assertEqual(float(res.data['cart']['total_amount']), 1000.00)

        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)

    def test_customer_can_remove_item_from_cart(self):
        """Customer can delete a cart item."""
        item = CustomerCartItem.objects.create(
            user=self.customer1,
            product=self.product,
            plan=self.plan_monthly,
            quantity=1
        )
        self.client.force_authenticate(user=self.customer1)

        detail_url = reverse('customer:cart-item-detail', kwargs={'item_id': item.id})
        res = self.client.delete(detail_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['cart']['items_count'], 0)
        self.assertEqual(res.data['cart']['total_quantity'], 0)
        self.assertFalse(CustomerCartItem.objects.filter(pk=item.id).exists())

    def test_customer_can_clear_entire_cart(self):
        """Customer can clear all items from cart with a single request."""
        CustomerCartItem.objects.create(
            user=self.customer1,
            product=self.product,
            plan=self.plan_monthly,
            quantity=1
        )
        CustomerCartItem.objects.create(
            user=self.customer1,
            product=self.product,
            plan=self.plan_yearly,
            quantity=1
        )
        self.client.force_authenticate(user=self.customer1)

        res = self.client.delete(self.cart_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['cart']['items_count'], 0)
        self.assertEqual(CustomerCartItem.objects.filter(user=self.customer1).count(), 0)


class CustomerOrderTests(APITestCase):
    def setUp(self):
        # Create Category, Product & Plans
        self.category = Category.objects.create(name="AI & Tools", description="AI apps")
        self.product = Product.objects.create(
            name="ChatGPT Plus License",
            category=self.category,
            description={"en": "GPT-4o Subscription"},
            features=["GPT-4o", "DALL-E"]
        )
        self.plan = ProductPlan.objects.create(
            product=self.product,
            name="Pro Plan",
            price=2500.00,
            currency="BDT",
            billing_cycle="monthly",
            devices=2,
            is_default=True
        )

        # Customers
        self.customer = User.objects.create_user(
            username="buyer_mfs",
            email="buyer.mfs@gmail.com",
            password="SecurePassword123!"
        )
        self.other_customer = User.objects.create_user(
            username="other_mfs",
            email="other.mfs@gmail.com",
            password="SecurePassword123!"
        )

        # Super Admin
        self.superadmin = User.objects.create_superuser(
            username="superadmin_test",
            email="superadmin.test@gmail.com",
            password="AdminPassword123!"
        )

        self.payment_methods_url = reverse('customer:payment-methods')
        self.orders_url = reverse('customer:order-list-create')
        self.my_subs_url = reverse('customer:my-subscriptions')
        self.cart_url = reverse('customer:cart')
        self.admin_orders_url = reverse('superuser:superuser-orders-list')

    def test_get_supported_mfs_payment_methods(self):
        """Verify endpoint returns bKash, Nagad, Rocket, and Bangla QR details."""
        res = self.client.get(self.payment_methods_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        methods = res.data.get('payment_methods', [])
        self.assertEqual(len(methods), 4)

        method_ids = [m['id'] for m in methods]
        self.assertIn('bkash', method_ids)
        self.assertIn('nagad', method_ids)
        self.assertIn('rocket', method_ids)
        self.assertIn('bangla_qr', method_ids)

        bkash = next(m for m in methods if m['id'] == 'bkash')
        self.assertEqual(bkash['account_number'], '01712-345678')
        self.assertTrue(len(bkash['steps']) >= 5)

    def test_unauthenticated_cannot_place_order(self):
        """Unauthenticated user cannot place an order."""
        res = self.client.post(self.orders_url, {
            "payment_method": "bkash",
            "sender_number": "01700000000",
            "transaction_id": "TRX12345678"
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_can_place_order_from_cart(self):
        """Customer places order from cart items with bKash and TrxID."""
        # Add item to cart
        CustomerCartItem.objects.create(
            user=self.customer,
            product=self.product,
            plan=self.plan,
            quantity=1
        )
        self.client.force_authenticate(user=self.customer)

        payload = {
            "payment_method": "bkash",
            "sender_number": "01711223344",
            "transaction_id": "BKASH9928A",
            "customer_notes": "Please deliver quickly"
        }
        res = self.client.post(self.orders_url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("confirmed!", res.data['message'])

        order = res.data['order']
        self.assertEqual(order['status'], 'PENDING')
        self.assertEqual(order['payment_method'], 'bkash')
        self.assertEqual(order['transaction_id'], 'BKASH9928A')
        self.assertEqual(order['sender_number'], '01711223344')
        self.assertEqual(float(order['total_amount']), 2500.00)
        self.assertEqual(len(order['items']), 1)
        self.assertEqual(order['items'][0]['product_name'], self.product.name)

        # Ensure user's cart was cleared upon order creation
        self.assertEqual(CustomerCartItem.objects.filter(user=self.customer).count(), 0)

    def test_customer_can_place_direct_order_with_nagad(self):
        """Customer places direct instant buy order with Nagad."""
        self.client.force_authenticate(user=self.customer)
        payload = {
            "payment_method": "nagad",
            "sender_number": "01911223344",
            "transaction_id": "NAGAD7733B",
            "product_id": self.product.id,
            "plan_id": self.plan.id
        }
        res = self.client.post(self.orders_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order = res.data['order']
        self.assertEqual(order['payment_method'], 'nagad')
        self.assertEqual(order['transaction_id'], 'NAGAD7733B')

    def test_duplicate_transaction_id_rejected(self):
        """Submitting an already used TrxID returns HTTP 400."""
        self.client.force_authenticate(user=self.customer)
        payload = {
            "payment_method": "rocket",
            "sender_number": "01811223344",
            "transaction_id": "DUPLICATE123",
            "product_id": self.product.id,
            "plan_id": self.plan.id
        }
        res1 = self.client.post(self.orders_url, payload, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Same TrxID again
        res2 = self.client.post(self.orders_url, payload, format='json')
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been submitted", str(res2.data['transaction_id'][0]))


    def test_customer_order_data_isolation(self):
        """Customer A only sees Customer A's orders, not Customer B's."""
        self.client.force_authenticate(user=self.customer)
        self.client.post(self.orders_url, {
            "payment_method": "bkash",
            "sender_number": "01711111111",
            "transaction_id": "USERA999",
            "product_id": self.product.id,
            "plan_id": self.plan.id
        }, format='json')

        self.client.force_authenticate(user=self.other_customer)
        res = self.client.get(self.orders_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 0)

    def test_super_admin_can_approve_order_and_activates_digital_license(self):
        """
        Super Admin inspects order with TrxID and approves it.
        The product purchase is confirmed and digital license is activated for the user.
        """
        # Customer places order
        self.client.force_authenticate(user=self.customer)
        place_res = self.client.post(self.orders_url, {
            "payment_method": "bkash",
            "sender_number": "01711223344",
            "transaction_id": "VERIFYME123",
            "product_id": self.product.id,
            "plan_id": self.plan.id
        }, format='json')
        order_id = place_res.data['order']['id']

        # Super Admin checks orders list
        self.client.force_authenticate(user=self.superadmin)
        list_res = self.client.get(self.admin_orders_url)
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(list_res.data['metrics']['pending_orders'], 1)
        self.assertEqual(list_res.data['orders'][0]['transaction_id'], "VERIFYME123")

        # Super Admin approves order
        approve_url = reverse('superuser:superuser-order-approve', kwargs={'order_id': order_id})
        approve_res = self.client.post(approve_url, {
            "license_key": "CHATGPT-PLUS-PRO-KEY-2026",
            "admin_notes": "Verified against bKash merchant statement"
        }, format='json')
        self.assertEqual(approve_res.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_res.data['order']['status'], 'APPROVED')
        self.assertEqual(approve_res.data['order']['license_key'], 'CHATGPT-PLUS-PRO-KEY-2026')

        # Customer now checks my-subscriptions and sees confirmed product purchase
        self.client.force_authenticate(user=self.customer)
        subs_res = self.client.get(self.my_subs_url)
        self.assertEqual(subs_res.status_code, status.HTTP_200_OK)
        self.assertEqual(subs_res.data['count'], 1)
        sub = subs_res.data['subscriptions'][0]
        self.assertEqual(sub['product_name'], self.product.name)
        self.assertEqual(sub['license_key'], 'CHATGPT-PLUS-PRO-KEY-2026')
        self.assertTrue(sub['is_active'])

    def test_super_admin_can_reject_order(self):
        """Super Admin can reject an order with invalid TrxID."""
        self.client.force_authenticate(user=self.customer)
        place_res = self.client.post(self.orders_url, {
            "payment_method": "nagad",
            "sender_number": "01999999999",
            "transaction_id": "FAKETRX999",
            "product_id": self.product.id,
            "plan_id": self.plan.id
        }, format='json')
        order_id = place_res.data['order']['id']

        # Super Admin rejects
        self.client.force_authenticate(user=self.superadmin)
        reject_url = reverse('superuser:superuser-order-reject', kwargs={'order_id': order_id})
        reject_res = self.client.post(reject_url, {
            "reason": "Fake TrxID: Payment not received in Nagad account"
        }, format='json')
        self.assertEqual(reject_res.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_res.data['order']['status'], 'REJECTED')
        self.assertIn("Fake TrxID", reject_res.data['order']['admin_notes'])



