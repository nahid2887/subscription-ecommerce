import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "category"
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    sku = models.CharField(max_length=100, unique=True, blank=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    # Features list stored as JSON array: ["24/7 Support", "100GB Storage", ...]
    features = models.JSONField(
        default=list,
        blank=True,
        help_text="List of product features"
    )
    # Multi-lingual description supporting all languages, e.g. {"en": "...", "es": "...", "bn": "...", "ar": "..."}
    description = models.JSONField(
        default=dict,
        blank=True,
        help_text="Multi-lingual description dictionary supporting any ISO language code (e.g. {'en': '...', 'es': '...'})"
    )
    warranty = models.TextField(
        blank=True,
        null=True,
        help_text="Warranty or money-back guarantee terms"
    )
    delivery = models.TextField(
        blank=True,
        null=True,
        help_text="Delivery terms, e.g. Instant Digital Access or 2-3 business days"
    )
    # Selected plan that dictates the current/default displayed price
    selected_plan = models.ForeignKey(
        'ProductPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_for_products',
        help_text="Selected plan defining the primary price for this product"
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_products'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "product"
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        if not self.sku:
            self.sku = f"PRD-{uuid.uuid4().hex[:8].upper()}"

        super().save(*args, **kwargs)

    @property
    def price(self):
        """
        Price is dependent on the selected plan.
        Returns the price of the selected plan or default plan, or None if no plan is selected.
        """
        if self.selected_plan:
            return self.selected_plan.price
        default_plan = self.plans.filter(is_default=True).first() or self.plans.first()
        return default_plan.price if default_plan else None

    @property
    def currency(self):
        if self.selected_plan:
            return self.selected_plan.currency
        default_plan = self.plans.filter(is_default=True).first() or self.plans.first()
        return default_plan.currency if default_plan else 'BDT'

    @property
    def currency_symbol(self):
        if self.selected_plan:
            return self.selected_plan.currency_symbol
        default_plan = self.plans.filter(is_default=True).first() or self.plans.first()
        return default_plan.currency_symbol if default_plan else '৳'

    def get_localized_description(self, lang='en'):
        """
        Helper method to retrieve description in requested language or fall back gracefully.
        Supports both single multi-language strings and translation dictionaries.
        """
        if not isinstance(self.description, dict):
            return str(self.description) if self.description else ""
        if lang in self.description:
            return self.description[lang]
        if 'text' in self.description:
            return self.description['text']
        if 'en' in self.description:
            return self.description['en']
        if self.description:
            return next(iter(self.description.values()))
        return ""

    def __str__(self):
        return self.name


class ProductPlan(models.Model):
    BILLING_CYCLE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('biannual', 'Bi-annual'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime / One-Time'),
        ('custom', 'Custom'),
    ]

    CURRENCY_CHOICES = [
        ('BDT', 'BDT (৳ - Taka)'),
        ('USD', 'USD ($ - US Dollar)'),
        ('EUR', 'EUR (€ - Euro)'),
        ('GBP', 'GBP (£ - British Pound)'),
        ('INR', 'INR (₹ - Indian Rupee)'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='plans'
    )
    name = models.CharField(
        max_length=100,
        help_text="Plan tier name (e.g., 1 Device Plan, 2 Devices Plan, Monthly Starter, Annual Pro)"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price for this plan"
    )
    currency = models.CharField(
        max_length=10,
        default='BDT',
        choices=CURRENCY_CHOICES,
        help_text="Currency code (e.g. BDT ৳, USD $, EUR €, GBP £)"
    )
    devices = models.PositiveIntegerField(
        default=1,
        null=True,
        blank=True,
        help_text="Number of devices allowed for this plan (e.g. 1 device, 2 devices, 5 devices)"
    )
    billing_cycle = models.CharField(
        max_length=30,
        choices=BILLING_CYCLE_CHOICES,
        default='monthly',
        help_text="Billing interval / cycle"
    )
    duration_in_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in days if applicable (e.g., 30 for monthly, 365 for annual)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Additional plan specifics or limits"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this plan is selected by default for the product"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Plan"
        verbose_name_plural = "Product Plans"
        ordering = ['price']

    @property
    def currency_symbol(self):
        curr = (self.currency or 'BDT').upper()
        if curr in ('BDT', 'TK', 'TAKA'):
            return '৳'
        if curr == 'EUR':
            return '€'
        if curr == 'GBP':
            return '£'
        if curr == 'INR':
            return '₹'
        return '$'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # If marked as default or if product has no selected plan yet, update product.selected_plan
        if self.is_default or not self.product.selected_plan_id:
            Product.objects.filter(pk=self.product_id).update(selected_plan=self)
            if self.is_default:
                # Ensure other plans of same product are not marked as default
                ProductPlan.objects.filter(product_id=self.product_id).exclude(pk=self.pk).update(is_default=False)

    def __str__(self):
        dev_str = f" - {self.devices} Device{'s' if self.devices != 1 else ''}" if self.devices else ""
        return f"{self.product.name} - {self.name} ({self.currency_symbol}{self.price} / {self.billing_cycle}{dev_str})"
