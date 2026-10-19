import base64
import json
import uuid
from rest_framework import serializers
from django.core.files.base import ContentFile
from drf_spectacular.utils import extend_schema_field
from .models import Category, Product, ProductPlan


class ProductImageField(serializers.ImageField):
    """
    Accepts:
    1. Standard uploaded file via multipart/form-data.
    2. Base64 data URI string via JSON (e.g., 'data:image/png;base64,...').
    3. None/empty string to leave empty.
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
                    file_name = f"product_{uuid.uuid4().hex[:10]}.{ext}"
                    data = ContentFile(base64.b64decode(imgstr), name=file_name)
                except Exception:
                    raise serializers.ValidationError("Invalid Base64 image payload.")
            elif data.startswith('http://') or data.startswith('https://'):
                # External URL or existing path passed as string
                return None
            elif data.lower() in ('remove', 'none'):
                return None
            else:
                raise serializers.ValidationError("Invalid image format. Provide a file upload or base64 data URI.")

        return super().to_internal_value(data)


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'products_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'products_count', 'created_at', 'updated_at']


class ProductPlanItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency_symbol = serializers.CharField(read_only=True)
    devices = serializers.IntegerField(required=False, default=1)

    class Meta:
        model = ProductPlan
        fields = [
            'id',
            'name',
            'price',
            'currency',
            'currency_symbol',
            'devices',
            'billing_cycle',
            'duration_in_days',
            'description',
            'is_default',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'currency_symbol', 'created_at']


class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Serializer used by Super Admin to create a Product with:
    - name
    - image (multipart file or base64)
    - category (ID or name string)
    - features (list or JSON string)
    - multi-lingual description supporting all languages
    - warranty
    - delivery
    - plans with pricing (selected plan determines displayed price)
    """
    image = ProductImageField(required=False, allow_null=True)
    category = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Category ID (integer) or category name (string). If category does not exist, it will be created."
    )
    features = serializers.JSONField(
        required=False,
        default=list,
        help_text="List of features, e.g. ['24/7 Support', 'Unlimited Storage'] or JSON array string"
    )
    description = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Multi-lingual description dict: {'en': '...', 'es': '...', 'bn': '...'} or plain text string"
    )
    plans = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True,
        help_text="List of plans with prices: [{'name': 'Monthly', 'price': 19.99, 'billing_cycle': 'monthly', 'is_default': True}]"
    )
    selected_plan = serializers.DictField(
        required=False,
        write_only=True,
        help_text="Optional single plan definition to create and mark as selected: {'name': 'Standard', 'price': 29.99, 'billing_cycle': 'monthly'}"
    )
    selected_plan_id = serializers.IntegerField(
        required=False,
        write_only=True,
        allow_null=True,
        help_text="ID of an existing plan to set as selected"
    )

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'sku',
            'image',
            'category',
            'features',
            'description',
            'warranty',
            'delivery',
            'plans',
            'selected_plan',
            'selected_plan_id',
            'is_active',
        ]
        read_only_fields = ['id', 'sku']

    def to_internal_value(self, data):
        # Support stringified JSON fields and file uploads in multipart/form-data
        if hasattr(data, 'getlist'):
            plain_data = {}
            for key in data.keys():
                plain_data[key] = data.get(key)
            data = plain_data
        elif isinstance(data, dict):
            data = data.copy()

        if isinstance(data.get('plans'), str):
            try:
                data['plans'] = json.loads(data['plans'])
            except Exception:
                pass

        if isinstance(data.get('selected_plan'), str):
            try:
                data['selected_plan'] = json.loads(data['selected_plan'])
            except Exception:
                pass

        if isinstance(data.get('features'), str):
            try:
                parsed = json.loads(data['features'])
                if isinstance(parsed, list):
                    data['features'] = parsed
            except Exception:
                pass

        if isinstance(data.get('description'), str):
            try:
                parsed = json.loads(data['description'])
                if isinstance(parsed, dict):
                    data['description'] = parsed
            except Exception:
                pass

        return super().to_internal_value(data)

    def validate_features(self, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                return [value]
            except Exception:
                # Comma separated fallback
                return [item.strip() for item in value.split(',') if item.strip()]
        if not isinstance(value, list):
            raise serializers.ValidationError("Features must be a list of strings or JSON array.")
        return value

    def validate_description(self, value):
        """
        Ensures multi-lingual description supports all languages.
        If a plain string is passed, converts it to {'en': value}.
        If a JSON string is passed, attempts parsing.
        """
        if isinstance(value, str):
            value = value.strip()
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
                return {'en': value}
            except Exception:
                return {'en': value}
        elif isinstance(value, dict):
            # Validate that keys are language codes (strings) and values are strings
            cleaned = {}
            for lang_code, text in value.items():
                cleaned[str(lang_code).lower()] = str(text)
            return cleaned
        elif value is None:
            return {}
        else:
            raise serializers.ValidationError("Description must be a dictionary of language codes to texts or a string.")

    def validate_plans(self, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    value = parsed
                else:
                    raise serializers.ValidationError("Plans must be a list of plan objects.")
            except Exception:
                raise serializers.ValidationError("Invalid JSON format for plans.")

        for plan_dict in value:
            if not isinstance(plan_dict, dict):
                raise serializers.ValidationError("Each plan must be an object with at least 'name' and 'price'.")
            if 'name' not in plan_dict or 'price' not in plan_dict:
                raise serializers.ValidationError("Each plan must include 'name' and 'price'.")
            try:
                float(plan_dict['price'])
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"Invalid price value for plan '{plan_dict.get('name')}'.")
        return value

    def create(self, validated_data):
        plans_data = validated_data.pop('plans', None)
        selected_plan_data = validated_data.pop('selected_plan', None)
        selected_plan_id = validated_data.pop('selected_plan_id', None)
        category_input = validated_data.pop('category', None)

        # Handle category resolution (ID or Name)
        category_instance = None
        if category_input:
            if isinstance(category_input, int) or (isinstance(category_input, str) and category_input.isdigit()):
                category_instance = Category.objects.filter(pk=int(category_input)).first()
            elif isinstance(category_input, str):
                category_name = category_input.strip()
                category_instance, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'description': f"Category for {category_name}"}
                )

        validated_data['category'] = category_instance

        # Set created_by if available in request
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['created_by'] = request.user

        product = Product.objects.create(**validated_data)

        # Create plans if provided
        created_plans = []
        if plans_data:
            for p_data in plans_data:
                plan = ProductPlan.objects.create(
                    product=product,
                    name=p_data.get('name'),
                    price=p_data.get('price'),
                    currency=p_data.get('currency', 'BDT'),
                    devices=p_data.get('devices', 1),
                    billing_cycle=p_data.get('billing_cycle', 'monthly'),
                    duration_in_days=p_data.get('duration_in_days'),
                    description=p_data.get('description', ''),
                    is_default=p_data.get('is_default', False),
                    is_active=p_data.get('is_active', True)
                )
                created_plans.append(plan)

        if selected_plan_data:
            plan = ProductPlan.objects.create(
                product=product,
                name=selected_plan_data.get('name'),
                price=selected_plan_data.get('price'),
                currency=selected_plan_data.get('currency', 'BDT'),
                devices=selected_plan_data.get('devices', 1),
                billing_cycle=selected_plan_data.get('billing_cycle', 'monthly'),
                duration_in_days=selected_plan_data.get('duration_in_days'),
                description=selected_plan_data.get('description', ''),
                is_default=True,
                is_active=True
            )
            created_plans.append(plan)
            product.selected_plan = plan
            product.save(update_fields=['selected_plan'])

        elif selected_plan_id:
            target_plan = ProductPlan.objects.filter(pk=selected_plan_id, product=product).first()
            if target_plan:
                product.selected_plan = target_plan
                product.save(update_fields=['selected_plan'])

        elif created_plans:
            # Set default or first plan as selected
            default_p = next((p for p in created_plans if p.is_default), created_plans[0])
            product.selected_plan = default_p
            product.save(update_fields=['selected_plan'])

        return product


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive representation of a Product with:
    - Dynamic price based on selected plan
    - All available plans with prices
    - Category details
    - Multi-lingual description & localized description
    - Image URL
    - Creator metadata
    """
    image = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    plans = ProductPlanItemSerializer(many=True, read_only=True)
    selected_plan = ProductPlanItemSerializer(read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    currency_symbol = serializers.CharField(read_only=True)
    localized_description = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'sku',
            'image',
            'category',
            'features',
            'description',
            'localized_description',
            'warranty',
            'delivery',
            'price',
            'currency',
            'currency_symbol',
            'selected_plan',
            'plans',
            'is_active',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    @extend_schema_field(serializers.CharField(allow_blank=True))
    def get_localized_description(self, obj):
        request = self.context.get('request')
        lang = 'en'
        if request:
            lang = request.query_params.get('lang')
            if not lang and 'HTTP_ACCEPT_LANGUAGE' in request.META:
                # Parse first preferred language from Accept-Language header
                header_val = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
                lang = header_val.split(',')[0].split(';')[0].split('-')[0].strip().lower()
        return obj.get_localized_description(lang=lang or 'en')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_created_by(self, obj):
        if not obj.created_by:
            return None
        return {
            'id': obj.created_by.id,
            'username': obj.created_by.username,
            'email': obj.created_by.email
        }


class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for Super Admin to update existing product details,
    plans, selected plan, description, features, warranty, delivery, etc.
    """
    image = ProductImageField(required=False, allow_null=True)
    category = serializers.CharField(required=False, allow_null=True)
    features = serializers.JSONField(required=False)
    description = serializers.JSONField(required=False)
    plans = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    selected_plan_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Product
        fields = [
            'name',
            'image',
            'category',
            'features',
            'description',
            'warranty',
            'delivery',
            'plans',
            'selected_plan_id',
            'is_active',
        ]

    def to_internal_value(self, data):
        if hasattr(data, 'getlist'):
            plain_data = {}
            for key in data.keys():
                plain_data[key] = data.get(key)
            data = plain_data
        elif isinstance(data, dict):
            data = data.copy()

        if isinstance(data.get('plans'), str):
            try:
                data['plans'] = json.loads(data['plans'])
            except Exception:
                pass

        if isinstance(data.get('features'), str):
            try:
                parsed = json.loads(data['features'])
                if isinstance(parsed, list):
                    data['features'] = parsed
            except Exception:
                pass

        if isinstance(data.get('description'), str):
            try:
                parsed = json.loads(data['description'])
                if isinstance(parsed, dict):
                    data['description'] = parsed
            except Exception:
                pass

        return super().to_internal_value(data)

    def validate_features(self, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                return [value]
            except Exception:
                return [item.strip() for item in value.split(',') if item.strip()]
        return value

    def validate_description(self, value):
        if isinstance(value, str):
            value = value.strip()
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
                return {'en': value}
            except Exception:
                return {'en': value}
        elif isinstance(value, dict):
            return {str(k).lower(): str(v) for k, v in value.items()}
        return value

    def validate_plans(self, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    value = parsed
                else:
                    raise serializers.ValidationError("Plans must be a list of plan objects.")
            except Exception:
                raise serializers.ValidationError("Invalid JSON format for plans.")

        for plan_dict in value:
            if not isinstance(plan_dict, dict):
                raise serializers.ValidationError("Each plan must be an object with at least 'name' and 'price'.")
            if 'name' not in plan_dict or 'price' not in plan_dict:
                raise serializers.ValidationError("Each plan must include 'name' and 'price'.")
            try:
                float(plan_dict['price'])
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"Invalid price value for plan '{plan_dict.get('name')}'.")
        return value

    def update(self, instance, validated_data):
        plans_data = validated_data.pop('plans', None)
        selected_plan_id = validated_data.pop('selected_plan_id', None)
        category_input = validated_data.pop('category', None)

        if category_input is not None:
            if isinstance(category_input, int) or (isinstance(category_input, str) and category_input.isdigit()):
                instance.category = Category.objects.filter(pk=int(category_input)).first()
            elif isinstance(category_input, str) and category_input.strip():
                category_name = category_input.strip()
                cat, _ = Category.objects.get_or_create(name=category_name)
                instance.category = cat
            elif category_input == '':
                instance.category = None

        if plans_data is not None:
            retained_plan_ids = []
            default_plan_instance = None

            for p_data in plans_data:
                p_id = p_data.get('id')
                is_def = p_data.get('is_default', False)
                is_act = p_data.get('is_active', True)

                if p_id:
                    plan = ProductPlan.objects.filter(pk=p_id, product=instance).first()
                    if plan:
                        plan.name = p_data.get('name', plan.name)
                        plan.price = p_data.get('price', plan.price)
                        plan.currency = p_data.get('currency', plan.currency)
                        if 'devices' in p_data and p_data.get('devices') is not None:
                            plan.devices = p_data.get('devices')
                        plan.billing_cycle = p_data.get('billing_cycle', plan.billing_cycle)
                        plan.duration_in_days = p_data.get('duration_in_days', plan.duration_in_days)
                        plan.is_default = is_def
                        plan.is_active = is_act
                        plan.save()
                        retained_plan_ids.append(plan.id)
                        if is_def:
                            default_plan_instance = plan
                else:
                    plan = ProductPlan.objects.create(
                        product=instance,
                        name=p_data.get('name'),
                        price=p_data.get('price'),
                        currency=p_data.get('currency', 'BDT'),
                        devices=p_data.get('devices', 1),
                        billing_cycle=p_data.get('billing_cycle', 'monthly'),
                        duration_in_days=p_data.get('duration_in_days'),
                        is_default=is_def,
                        is_active=is_act
                    )
                    retained_plan_ids.append(plan.id)
                    if is_def:
                        default_plan_instance = plan

            if default_plan_instance:
                instance.selected_plan = default_plan_instance
            elif retained_plan_ids and (not instance.selected_plan or instance.selected_plan_id not in retained_plan_ids):
                instance.selected_plan = ProductPlan.objects.filter(id__in=retained_plan_ids).first()

            if retained_plan_ids:
                ProductPlan.objects.filter(product=instance).exclude(id__in=retained_plan_ids).delete()

        if selected_plan_id is not None:
            target_plan = ProductPlan.objects.filter(pk=selected_plan_id, product=instance).first()
            if target_plan:
                instance.selected_plan = target_plan

        return super().update(instance, validated_data)


class ProductResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    product = ProductDetailSerializer()
