import base64
import uuid
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema_field
from product.models import Product, ProductPlan
from product.serializers import ProductDetailSerializer, ProductPlanItemSerializer
from .models import CustomerProfile, SavedProduct, CustomerCartItem, Order, OrderItem





class CustomerAvatarField(serializers.ImageField):
    """
    Accepts:
    1. Standard uploaded file via multipart/form-data.
    2. Base64 data URI string via JSON (e.g., 'data:image/png;base64,...').
    3. None/empty/'remove' to clear the avatar.
    """
    def to_internal_value(self, data):
        if data is None or data == '' or data == 'null':
            return None

        if isinstance(data, str):
            if data.startswith('data:image'):
                try:
                    format_part, imgstr = data.split(';base64,')
                    ext = format_part.split('/')[-1].lower()
                    if ext == 'jpeg':
                        ext = 'jpg'
                    file_name = f"cust_avatar_{uuid.uuid4().hex[:10]}.{ext}"
                    data = ContentFile(base64.b64decode(imgstr), name=file_name)
                except Exception:
                    raise serializers.ValidationError("Invalid Base64 image payload.")
            elif data.lower() in ('remove', 'none', 'clear'):
                return None
            elif data.startswith('http://') or data.startswith('https://'):
                return None
            else:
                raise serializers.ValidationError("Invalid image format. Provide a file upload or base64 data URI.")

        return super().to_internal_value(data)


class CustomerProfileSerializer(serializers.ModelSerializer):
    """
    Serializes a Customer's full profile information.
    """
    phone_number = serializers.CharField(source='customer_profile.phone_number', read_only=True)
    avatar = serializers.SerializerMethodField()
    address = serializers.CharField(source='customer_profile.address', read_only=True)
    city = serializers.CharField(source='customer_profile.city', read_only=True)
    country = serializers.CharField(source='customer_profile.country', read_only=True)
    postal_code = serializers.CharField(source='customer_profile.postal_code', read_only=True)
    is_verified = serializers.BooleanField(source='customer_profile.is_verified', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone_number',
            'avatar',
            'address',
            'city',
            'country',
            'postal_code',
            'is_verified',
            'date_joined',
            'last_login',
        ]
        read_only_fields = ['id', 'username', 'email', 'date_joined', 'last_login']

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_avatar(self, obj):
        try:
            profile = getattr(obj, 'customer_profile', None)
            if profile and profile.avatar:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.avatar.url)
                return profile.avatar.url
        except Exception:
            pass
        return None


class CustomerRegistrationSerializer(serializers.Serializer):
    """
    Customer Registration with Email (e.g. Gmail) & Password.
    Returns Bearer access and refresh tokens upon successful creation.
    """
    email = serializers.EmailField(required=True, help_text="Valid email address (e.g. yourname@gmail.com)")
    password = serializers.CharField(write_only=True, required=True, min_length=6, help_text="Password (min 6 characters)")
    password_confirm = serializers.CharField(write_only=True, required=False, help_text="Optional password confirmation")
    username = serializers.CharField(required=False, allow_blank=True, help_text="Optional username. Auto-generated from email if omitted.")
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    phone_number = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return normalized

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        if password_confirm and password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        first_name = validated_data.get('first_name', '').strip()
        last_name = validated_data.get('last_name', '').strip()
        phone_number = validated_data.get('phone_number', '').strip()

        # Generate unique username from email if not provided or collision
        raw_username = validated_data.get('username')
        if raw_username and raw_username.strip():
            username_base = raw_username.strip().lower()
        else:
            username_base = email.split('@')[0].lower()

        username = username_base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{username_base}_{counter}"
            counter += 1

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Update or create profile with phone_number
        profile, _ = CustomerProfile.objects.get_or_create(user=user)
        if phone_number:
            profile.phone_number = phone_number
            profile.save()
        user.customer_profile = profile

        # Generate JWT Tokens
        refresh = RefreshToken.for_user(user)

        return {
            'user': user,
            'token_type': 'Bearer',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
        }


class CustomerLoginSerializer(serializers.Serializer):
    """
    Customer Login using Email (Gmail) and Password.
    Returns Bearer access token, refresh token, and user details.
    """
    email = serializers.EmailField(required=True, help_text="Registered email address (e.g. yourname@gmail.com)")
    password = serializers.CharField(write_only=True, required=True, help_text="Account password")

    def validate(self, attrs):
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password', '')

        # Lookup user by email
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            # Fallback check username in case email was passed as username
            user = User.objects.filter(username__iexact=email).first()

        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("This customer account is inactive. Please contact support.")

        # Generate JWT Tokens
        refresh = RefreshToken.for_user(user)

        attrs['user'] = user
        attrs['token_type'] = 'Bearer'
        attrs['access_token'] = str(refresh.access_token)
        attrs['refresh_token'] = str(refresh)
        return attrs


class CustomerProfileUpdateSerializer(serializers.Serializer):
    """
    Update Customer profile details including name, username, email, password, phone, address, and avatar.
    """
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=6)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    avatar = CustomerAvatarField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    postal_code = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, value):
        val = value.strip()
        if not val:
            return val
        user = self.instance
        if User.objects.filter(username__iexact=val).exclude(pk=user.pk if user else None).exists():
            raise serializers.ValidationError("This username is already taken.")
        return val

    def update(self, instance, validated_data):
        # Update User model fields
        if 'first_name' in validated_data:
            instance.first_name = validated_data['first_name']
        if 'last_name' in validated_data:
            instance.last_name = validated_data['last_name']
        if 'username' in validated_data and validated_data['username']:
            instance.username = validated_data['username']
        # Email cannot be changed (immutable account identity)
        if 'password' in validated_data and validated_data['password']:
            instance.set_password(validated_data['password'])
        instance.save()

        # Update CustomerProfile model fields
        profile, _ = CustomerProfile.objects.get_or_create(user=instance)

        if 'phone_number' in validated_data:
            profile.phone_number = validated_data['phone_number']
        if 'avatar' in validated_data:
            profile.avatar = validated_data['avatar']
        if 'address' in validated_data:
            profile.address = validated_data['address']
        if 'city' in validated_data:
            profile.city = validated_data['city']
        if 'country' in validated_data:
            profile.country = validated_data['country']
        if 'postal_code' in validated_data:
            profile.postal_code = validated_data['postal_code']
        profile.save()

        return instance


# Response Schemas for OpenAPI / Swagger Documentation
class CustomerAuthResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    token_type = serializers.CharField(default="Bearer")
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = CustomerProfileSerializer()


class SavedProductSerializer(serializers.ModelSerializer):
    """
    Detailed representation of a saved product item for the customer.
    Includes full nested Product details for rendering and interaction.
    """
    product = ProductDetailSerializer(read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)

    class Meta:
        model = SavedProduct
        fields = [
            'id',
            'product_id',
            'product',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'product_id', 'product', 'created_at', 'updated_at']


class SavedProductCreateSerializer(serializers.Serializer):
    """
    Serializer to save a product to customer's saved items.
    Accepts:
    - product_id (int) OR product (int) OR slug (string)
    - notes (optional string)
    """
    product_id = serializers.IntegerField(required=False, help_text="ID of the product to save")
    product = serializers.IntegerField(required=False, help_text="Alternative parameter for product_id")
    slug = serializers.CharField(required=False, allow_blank=True, help_text="Slug of the product to save")
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="Optional customer notes")

    def validate(self, attrs):
        prod_id = attrs.get('product_id') or attrs.get('product')
        slug = attrs.get('slug')

        if not prod_id and not slug:
            raise serializers.ValidationError("Either 'product_id' or 'slug' must be provided.")

        product_obj = None
        if prod_id:
            product_obj = Product.objects.filter(pk=prod_id).first()
        elif slug:
            product_obj = Product.objects.filter(slug=slug.strip()).first()

        if not product_obj:
            raise serializers.ValidationError({"product_id": "Product not found."})

        attrs['product_instance'] = product_obj
        return attrs


class SavedProductToggleSerializer(serializers.Serializer):
    """
    Serializer to toggle the saved state of a product for the customer.
    """
    product_id = serializers.IntegerField(required=False, help_text="ID of the product to toggle")
    product = serializers.IntegerField(required=False, help_text="Alternative parameter for product_id")
    slug = serializers.CharField(required=False, allow_blank=True, help_text="Slug of the product to toggle")
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="Optional notes when saving")

    def validate(self, attrs):
        prod_id = attrs.get('product_id') or attrs.get('product')
        slug = attrs.get('slug')

        if not prod_id and not slug:
            raise serializers.ValidationError("Either 'product_id' or 'slug' must be provided.")

        product_obj = None
        if prod_id:
            product_obj = Product.objects.filter(pk=prod_id).first()
        elif slug:
            product_obj = Product.objects.filter(slug=slug.strip()).first()

        if not product_obj:
            raise serializers.ValidationError({"product_id": "Product not found."})

        attrs['product_instance'] = product_obj
        return attrs


class SavedProductActionResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    is_saved = serializers.BooleanField()
    product_id = serializers.IntegerField()
    saved_product = SavedProductSerializer(allow_null=True, required=False)


class SavedProductListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    saved_products = SavedProductSerializer(many=True)


class SavedProductCheckResponseSerializer(serializers.Serializer):
    is_saved = serializers.BooleanField()
    product_id = serializers.IntegerField()
    saved_product_id = serializers.IntegerField(allow_null=True)


# ==============================================================================
# CUSTOMER SHOPPING CART SERIALIZERS
# ==============================================================================
class CustomerCartItemSerializer(serializers.ModelSerializer):
    """
    Representation of an item in the customer user's shopping cart.
    Includes full product and plan details, calculated unit and total prices.
    """
    product = ProductDetailSerializer(read_only=True)
    plan = ProductPlanItemSerializer(read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    currency_symbol = serializers.CharField(read_only=True)

    class Meta:
        model = CustomerCartItem
        fields = [
            'id',
            'product',
            'plan',
            'quantity',
            'unit_price',
            'total_price',
            'currency',
            'currency_symbol',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'unit_price', 'total_price', 'currency', 'currency_symbol', 'created_at', 'updated_at']


class CustomerCartAddSerializer(serializers.Serializer):
    """
    Add a product and optional plan tier to the customer's cart.
    """
    product_id = serializers.IntegerField(required=True, help_text="ID of the product to add to cart")
    plan_id = serializers.IntegerField(required=False, allow_null=True, help_text="ID of the selected plan tier (optional)")
    quantity = serializers.IntegerField(required=False, default=1, min_value=1, help_text="Quantity (defaults to 1)")

    def validate(self, attrs):
        product_id = attrs.get('product_id')
        plan_id = attrs.get('plan_id')

        product_obj = Product.objects.filter(pk=product_id, is_active=True).first()
        if not product_obj:
            raise serializers.ValidationError({"product_id": "Active product not found."})

        plan_obj = None
        if plan_id:
            plan_obj = ProductPlan.objects.filter(pk=plan_id, product=product_obj, is_active=True).first()
            if not plan_obj:
                raise serializers.ValidationError({"plan_id": "Selected plan tier not found for this product."})
        else:
            plan_obj = product_obj.selected_plan or product_obj.plans.filter(is_default=True).first() or product_obj.plans.first()

        attrs['product_instance'] = product_obj
        attrs['plan_instance'] = plan_obj
        return attrs


class CustomerCartUpdateSerializer(serializers.Serializer):
    """
    Update the quantity of an item in the cart.
    """
    quantity = serializers.IntegerField(required=True, min_value=0, help_text="New quantity. Set to 0 to remove item.")


class CustomerCartResponseSerializer(serializers.Serializer):
    items_count = serializers.IntegerField()
    total_quantity = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency_symbol = serializers.CharField()
    items = CustomerCartItemSerializer(many=True)
    cart_items = CustomerCartItemSerializer(many=True, required=False)
    cart_count = serializers.IntegerField(required=False)
    cart_total = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class CustomerCartActionResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    cart = CustomerCartResponseSerializer()
    item = CustomerCartItemSerializer(allow_null=True, required=False)


# ==============================================================================
# CUSTOMER ORDER & PAYMENT SERIALIZERS
# ==============================================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Representation of an item inside an order.
    """
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'plan',
            'plan_name',
            'quantity',
            'unit_price',
            'total_price',
            'devices',
            'billing_cycle',
            'product_image',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    """
    Full representation of a customer order with MFS verification and license.
    """
    items = OrderItemSerializer(many=True, read_only=True)
    customer_username = serializers.CharField(source='user.username', read_only=True)
    customer_email = serializers.CharField(source='user.email', read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True, default=None)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'user',
            'customer_username',
            'customer_email',
            'delivery_email',
            'sender_number',
            'payment_method',
            'payment_method_display',
            'transaction_id',
            'total_amount',
            'currency',
            'currency_symbol',
            'status',
            'status_display',
            'license_key',
            'customer_notes',
            'admin_notes',
            'approved_by',
            'approved_by_username',
            'approved_at',
            'created_at',
            'updated_at',
            'items',
        ]
        read_only_fields = [
            'id',
            'order_number',
            'user',
            'customer_username',
            'customer_email',
            'payment_method_display',
            'total_amount',
            'currency',
            'currency_symbol',
            'status',
            'status_display',
            'license_key',
            'admin_notes',
            'approved_by',
            'approved_by_username',
            'approved_at',
            'created_at',
            'updated_at',
            'items',
        ]


class CustomerOrderCreateSerializer(serializers.Serializer):
    """
    Serializer to place an order either from the customer's cart or directly for a product.
    Requires MFS payment details: payment_method, sender_number, transaction_id.
    """
    payment_method = serializers.ChoiceField(
        choices=Order.PAYMENT_CHOICES,
        default=Order.PAYMENT_BKASH,
        help_text="Payment method selected: bkash, nagad, rocket, bangla_qr"
    )
    sender_number = serializers.CharField(
        max_length=30,
        required=True,
        help_text="The phone/MFS account number used to send money"
    )
    transaction_id = serializers.CharField(
        max_length=100,
        required=True,
        help_text="The Transaction ID (TrxID) received from MFS SMS/receipt"
    )
    delivery_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text="Email for receiving license/credentials (defaults to customer email)"
    )
    customer_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional customer notes"
    )
    source = serializers.ChoiceField(
        choices=['cart', 'direct'],
        default='cart',
        help_text="Order source: 'cart' checks out current cart items, 'direct' checks out specified product"
    )
    # Direct purchase fields (used if source == 'direct')
    product_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Product ID if ordering directly"
    )
    plan_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Plan ID if ordering directly"
    )
    quantity = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        help_text="Quantity if ordering directly"
    )

    def validate(self, attrs):
        user = self.context['request'].user
        source = attrs.get('source', 'cart')
        trx_id = attrs.get('transaction_id', '').strip()
        sender_num = attrs.get('sender_number', '').strip()

        if not trx_id:
            raise serializers.ValidationError({"transaction_id": "Transaction number (TrxID) is strictly required."})
        if not sender_num:
            raise serializers.ValidationError({"sender_number": "Sender phone number is required."})

        # Check for duplicate pending/approved order with same transaction ID
        if Order.objects.filter(transaction_id__iexact=trx_id).exclude(status=Order.STATUS_REJECTED).exists():
            raise serializers.ValidationError({
                "transaction_id": "This Transaction ID has already been submitted. Please check your order history or provide a valid unique TrxID."
            })

        attrs['transaction_id'] = trx_id
        attrs['sender_number'] = sender_num

        # Auto-detect direct checkout if product_id is passed
        product_id = attrs.get('product_id') or self.initial_data.get('product_id')
        if product_id:
            source = 'direct'
            attrs['source'] = 'direct'
            attrs['product_id'] = int(product_id)
        else:
            source = attrs.get('source', 'cart')

        if source == 'cart':
            cart_items = CustomerCartItem.objects.filter(user=user).select_related('product', 'plan')
            if not cart_items.exists():
                raise serializers.ValidationError({"source": "Your shopping cart is empty. Please add items to your cart before confirming order."})
            attrs['cart_items'] = list(cart_items)
        else:
            if not product_id:
                raise serializers.ValidationError({"product_id": "Product ID is required for direct checkout."})
            product = Product.objects.filter(pk=product_id, is_active=True).first()

            if not product:
                raise serializers.ValidationError({"product_id": "Active product not found."})

            plan_id = attrs.get('plan_id')
            plan = None
            if plan_id:
                plan = ProductPlan.objects.filter(pk=plan_id, product=product, is_active=True).first()
                if not plan:
                    raise serializers.ValidationError({"plan_id": "Selected plan not found for this product."})
            else:
                plan = product.selected_plan or product.plans.filter(is_default=True).first() or product.plans.first()

            attrs['product_obj'] = product
            attrs['plan_obj'] = plan

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        source = validated_data.get('source', 'cart')
        delivery_email = validated_data.get('delivery_email') or user.email or ""
        sender_number = validated_data['sender_number']
        payment_method = validated_data['payment_method']
        transaction_id = validated_data['transaction_id']
        customer_notes = validated_data.get('customer_notes', '')

        if source == 'cart':
            cart_items = validated_data['cart_items']
            total_amount = sum((it.total_price or 0) for it in cart_items)
            sym = cart_items[0].currency_symbol if cart_items else '৳'
            curr = cart_items[0].currency if cart_items else 'BDT'

            order = Order.objects.create(
                user=user,
                delivery_email=delivery_email,
                sender_number=sender_number,
                payment_method=payment_method,
                transaction_id=transaction_id,
                total_amount=total_amount,
                currency=curr,
                currency_symbol=sym,
                status=Order.STATUS_PENDING,
                customer_notes=customer_notes
            )

            for it in cart_items:
                product_img = None
                if it.product and it.product.image:
                    try:
                        product_img = it.product.image.url
                    except Exception:
                        product_img = None

                OrderItem.objects.create(
                    order=order,
                    product=it.product,
                    product_name=it.product.name,
                    plan=it.plan,
                    plan_name=it.plan.name if it.plan else "",
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    total_price=it.total_price,
                    devices=it.plan.devices if it.plan else 1,
                    billing_cycle=it.plan.billing_cycle if it.plan else "monthly",
                    product_image=product_img
                )

            # Clear cart items upon successful order creation
            CustomerCartItem.objects.filter(user=user).delete()

            return order
        else:
            product = validated_data['product_obj']
            plan = validated_data['plan_obj']
            quantity = validated_data.get('quantity', 1)

            unit_price = plan.price if (plan and plan.price is not None) else (product.price or 0)
            total_price = unit_price * quantity
            sym = plan.currency_symbol if (plan and plan.currency_symbol) else (product.currency_symbol or '৳')
            curr = plan.currency if (plan and plan.currency) else (product.currency or 'BDT')

            order = Order.objects.create(
                user=user,
                delivery_email=delivery_email,
                sender_number=sender_number,
                payment_method=payment_method,
                transaction_id=transaction_id,
                total_amount=total_price,
                currency=curr,
                currency_symbol=sym,
                status=Order.STATUS_PENDING,
                customer_notes=customer_notes
            )

            product_img = None
            if product.image:
                try:
                    product_img = product.image.url
                except Exception:
                    product_img = None

            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                plan=plan,
                plan_name=plan.name if plan else "",
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                devices=plan.devices if plan else 1,
                billing_cycle=plan.billing_cycle if plan else "monthly",
                product_image=product_img
            )

            return order


class AdminOrderApprovalSerializer(serializers.Serializer):
    """
    Serializer for Super Admin to approve an order.
    """
    license_key = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Custom digital license activation key (auto-generated if omitted)"
    )
    admin_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Verification message, access instructions, or account credentials for the customer"
    )


class AdminOrderRejectionSerializer(serializers.Serializer):
    """
    Serializer for Super Admin to reject an order.
    """
    reason = serializers.CharField(
        required=True,
        help_text="Reason for rejection (e.g. 'Invalid Transaction ID', 'Amount mismatch')"
    )


class OrderActionResponseSerializer(serializers.Serializer):
    """
    Standard response for order actions.
    """
    message = serializers.CharField()
    order = OrderSerializer()


