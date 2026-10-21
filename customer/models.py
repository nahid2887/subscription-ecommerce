from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import uuid


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    phone_number = models.CharField(max_length=25, blank=True, null=True)
    avatar = models.ImageField(upload_to='customer_avatars/', null=True, blank=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, default='Bangladesh')
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"
        ordering = ['-created_at']

    def __str__(self):
        return f"Customer Profile for {self.user.email or self.user.username}"


@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        CustomerProfile.objects.get_or_create(user=instance)


class SavedProduct(models.Model):
    """
    Represents a product saved/bookmarked by a customer user.
    Enforces uniqueness per (user, product) pair.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_products',
        help_text="Customer user who saved the product"
    )
    product = models.ForeignKey(
        'product.Product',
        on_delete=models.CASCADE,
        related_name='saved_by_customers',
        help_text="The product saved by the customer"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Optional customer notes or reminder for this saved item"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Saved Product"
        verbose_name_plural = "Saved Products"
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        user_display = self.user.email or self.user.username
        product_name = self.product.name if self.product else "Unknown Product"
        return f"{user_display} saved {product_name}"


class CustomerCartItem(models.Model):
    """
    Represents an item in the customer user's shopping cart.
    Links a User with a Product and optionally a selected ProductPlan and quantity.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cart_items',
        help_text="Customer user who added this item to cart"
    )
    product = models.ForeignKey(
        'product.Product',
        on_delete=models.CASCADE,
        related_name='cart_items',
        help_text="Product added to cart"
    )
    plan = models.ForeignKey(
        'product.ProductPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cart_items',
        help_text="Selected plan tier (optional, defaults to product default plan)"
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ('user', 'product', 'plan')
        ordering = ['-created_at']

    @property
    def unit_price(self):
        if self.plan and self.plan.price is not None:
            return self.plan.price
        return self.product.price or 0

    @property
    def total_price(self):
        return (self.unit_price or 0) * self.quantity

    @property
    def currency(self):
        if self.plan and self.plan.currency:
            return self.plan.currency
        return self.product.currency or 'BDT'

    @property
    def currency_symbol(self):
        if self.plan and self.plan.currency_symbol:
            return self.plan.currency_symbol
        return self.product.currency_symbol or '৳'

    def __str__(self):
        user_name = self.user.email or self.user.username
        plan_str = f" ({self.plan.name})" if self.plan else ""
        return f"{user_name} - {self.product.name}{plan_str} x{self.quantity}"


class Order(models.Model):
    """
    Customer subscription purchase order with MFS payment verification.
    """
    PAYMENT_BKASH = 'bkash'
    PAYMENT_NAGAD = 'nagad'
    PAYMENT_ROCKET = 'rocket'
    PAYMENT_BANGLA_QR = 'bangla_qr'

    PAYMENT_CHOICES = [
        (PAYMENT_BKASH, 'bKash'),
        (PAYMENT_NAGAD, 'Nagad'),
        (PAYMENT_ROCKET, 'Rocket'),
        (PAYMENT_BANGLA_QR, 'Bangla QR'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Verification'),
        (STATUS_APPROVED, 'Approved / Completed'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    order_number = models.CharField(max_length=64, unique=True, blank=True, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='customer_orders',
        help_text="Customer user who placed the order"
    )
    delivery_email = models.EmailField(blank=True, null=True, help_text="Delivery email for credentials")
    sender_number = models.CharField(max_length=30, help_text="Customer sender MFS number (e.g. 017XXXXXXXX)")
    payment_method = models.CharField(max_length=30, choices=PAYMENT_CHOICES, default=PAYMENT_BKASH)
    transaction_id = models.CharField(max_length=100, help_text="MFS Transaction ID (TrxID / TxnID)")

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default='BDT')
    currency_symbol = models.CharField(max_length=10, default='৳')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    license_key = models.CharField(max_length=150, blank=True, null=True, help_text="Digital license activation key")
    customer_notes = models.TextField(blank=True, null=True, help_text="Customer instructions or note")
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin verification feedback or instructions")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_orders')
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer Order"
        verbose_name_plural = "Customer Orders"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            date_prefix = timezone.now().strftime('%Y%m%d')
            unique_suffix = uuid.uuid4().hex[:6].upper()
            self.order_number = f"ORD-{date_prefix}-{unique_suffix}"
        super().save(*args, **kwargs)

    def approve(self, admin_user=None, custom_license_key=None, admin_notes=None):
        """Approve the order and assign digital license activation key."""
        self.status = self.STATUS_APPROVED
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        if custom_license_key:
            self.license_key = custom_license_key
        elif not self.license_key:
            self.license_key = f"SUB-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
        if admin_notes:
            self.admin_notes = admin_notes
        self.save(update_fields=['status', 'approved_by', 'approved_at', 'license_key', 'admin_notes', 'updated_at'])

    def reject(self, admin_user=None, reason=None):
        """Reject the order."""
        self.status = self.STATUS_REJECTED
        self.approved_by = admin_user
        if reason:
            self.admin_notes = reason
        self.save(update_fields=['status', 'approved_by', 'admin_notes', 'updated_at'])

    def __str__(self):
        user_display = self.user.email or self.user.username
        return f"{self.order_number} ({user_display}) - {self.payment_method.upper()}: {self.transaction_id} [{self.status}]"


class OrderItem(models.Model):
    """
    Items included in a customer order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('product.Product', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_name = models.CharField(max_length=255)
    plan = models.ForeignKey('product.ProductPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    plan_name = models.CharField(max_length=255, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    devices = models.PositiveIntegerField(default=1)
    billing_cycle = models.CharField(max_length=50, default='monthly')
    product_image = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ['id']

    def __str__(self):
        plan_str = f" ({self.plan_name})" if self.plan_name else ""
        return f"{self.product_name}{plan_str} x{self.quantity}"


