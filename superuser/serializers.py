import base64
import uuid
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema_field

from .models import SuperuserProfile


class AvatarField(serializers.ImageField):
    """
    Accepts image file uploads (via multipart/form-data)
    and Base64 data URI strings (via JSON).
    Also accepts None/empty to remove/clear the avatar.
    """
    def to_internal_value(self, data):
        if data is None or data == '':
            return None

        # Base64 data URI support
        if isinstance(data, str):
            if data.startswith('data:image'):
                try:
                    format_part, imgstr = data.split(';base64,')
                    ext = format_part.split('/')[-1].lower()
                    if ext == 'jpeg':
                        ext = 'jpg'
                    file_name = f"avatar_{uuid.uuid4().hex[:8]}.{ext}"
                    data = ContentFile(base64.b64decode(imgstr), name=file_name)
                except Exception:
                    raise serializers.ValidationError("Invalid base64 image data.")
            elif data.lower() in ('remove', 'null', 'none'):
                return None
            else:
                raise serializers.ValidationError("Invalid image format. Provide a file upload or base64 data URI.")

        return super().to_internal_value(data)


class SuperuserDetailSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_superuser',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
            'avatar',
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_avatar(self, obj):
        profile = getattr(obj, 'profile', None)
        if not profile:
            profile = SuperuserProfile.objects.filter(user=obj).first()
        if profile and profile.avatar:
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.avatar.url)
                return profile.avatar.url
            except Exception:
                return None
        return None


class SuperuserProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        help_text="User's first name"
    )
    last_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        help_text="User's last name"
    )
    avatar = AvatarField(
        required=False,
        allow_null=True,
        help_text="Upload a new profile picture (file or base64), or null to remove"
    )
    current_password = serializers.CharField(
        required=False,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Current password (required when setting a new password)"
    )
    new_password = serializers.CharField(
        required=False,
        write_only=True,
        min_length=6,
        style={'input_type': 'password'},
        help_text="New password (minimum 6 characters)"
    )
    confirm_password = serializers.CharField(
        required=False,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmation of new password"
    )

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        # Disallow username and email changes
        initial_data = getattr(self, 'initial_data', {})
        if 'username' in initial_data:
            if user and initial_data.get('username') != user.username:
                raise serializers.ValidationError({"username": "Username cannot be changed."})
        if 'email' in initial_data:
            if user and initial_data.get('email') != user.email:
                raise serializers.ValidationError({"email": "Email address cannot be changed."})

        new_password = attrs.get('new_password')
        current_password = attrs.get('current_password')
        confirm_password = attrs.get('confirm_password')

        if new_password:
            if not current_password:
                raise serializers.ValidationError({"current_password": "Current password is required to set a new password."})
            if user and not user.check_password(current_password):
                raise serializers.ValidationError({"current_password": "The current password entered is incorrect."})
            if confirm_password and new_password != confirm_password:
                raise serializers.ValidationError({"confirm_password": "New passwords do not match."})

        return attrs

    def update(self, instance, validated_data):
        if 'first_name' in validated_data:
            instance.first_name = validated_data['first_name']
        if 'last_name' in validated_data:
            instance.last_name = validated_data['last_name']

        new_password = validated_data.get('new_password')
        if new_password:
            instance.set_password(new_password)

        instance.save()

        # Handle profile picture update
        if 'avatar' in validated_data:
            avatar_val = validated_data['avatar']
            profile, _ = SuperuserProfile.objects.get_or_create(user=instance)
            if avatar_val:
                profile.avatar = avatar_val
                profile.save()
            else:
                if profile.avatar:
                    profile.avatar.delete(save=False)
                profile.avatar = None
                profile.save()

        return instance


class SuperuserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=False,
        help_text="Superuser email address (e.g. nahid2887@gmail.com)"
    )
    username = serializers.CharField(
        required=False,
        help_text="Superuser username (optional if email is provided)"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        email = attrs.get('email')
        username = attrs.get('username')
        password = attrs.get('password')

        if not email and not username:
            raise serializers.ValidationError({"detail": "Please provide an email or username."})

        # Resolve user by email or username
        user_obj = None
        if email:
            # Check superusers first with this email
            user_obj = User.objects.filter(email__iexact=email, is_superuser=True).first()
            if not user_obj:
                user_obj = User.objects.filter(email__iexact=email).first()
            if not user_obj:
                raise serializers.ValidationError({"detail": "No account found with this email."})
        elif username:
            user_obj = User.objects.filter(username__iexact=username).first()
            if not user_obj:
                raise serializers.ValidationError({"detail": "No account found with this username."})

        # Authenticate using resolved username
        user = authenticate(username=user_obj.username, password=password)

        if not user:
            raise serializers.ValidationError({"detail": "Invalid credentials."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "User account is disabled."})

        if not user.is_superuser:
            raise serializers.ValidationError({"detail": "Access denied. Only superusers are allowed to log in here."})

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Include custom claims
        refresh['username'] = user.username
        refresh['email'] = user.email
        refresh['is_superuser'] = user.is_superuser

        return {
            'user': user,
            'token_type': 'Bearer',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
        }


class SuperuserLoginResponseSerializer(serializers.Serializer):
    message = serializers.CharField(default="Superuser login successful.")
    token_type = serializers.CharField(default="Bearer")
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = SuperuserDetailSerializer()


class DashboardMetricSerializer(serializers.Serializer):
    monthly_revenue = serializers.FloatField(default=38420.0, help_text="Total Monthly Recurring Revenue (USD)")
    active_subscriptions = serializers.IntegerField(default=1428, help_text="Total active subscribers")
    arpu = serializers.FloatField(default=64.50, help_text="Average Revenue Per User (USD)")
    system_health = serializers.CharField(default="99.98%", help_text="API system availability")


class SubscriberItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    plan = serializers.CharField()
    billing = serializers.CharField()
    status = serializers.CharField()
    joined_date = serializers.CharField()


class SuperAdminDashboardResponseSerializer(serializers.Serializer):
    message = serializers.CharField(default="Dashboard data retrieved successfully.")
    metrics = DashboardMetricSerializer()
    recent_subscribers = SubscriberItemSerializer(many=True)


class SuperAdminCustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    orders_count = serializers.SerializerMethodField()
    pending_orders_count = serializers.SerializerMethodField()
    approved_orders_count = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    last_order_date = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone_number',
            'avatar',
            'city',
            'country',
            'is_verified',
            'is_active',
            'orders_count',
            'pending_orders_count',
            'approved_orders_count',
            'total_spent',
            'last_order_date',
            'date_joined',
            'last_login',
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.username

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_phone_number(self, obj):
        profile = getattr(obj, 'customer_profile', None)
        return profile.phone_number if profile else None

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_avatar(self, obj):
        profile = getattr(obj, 'customer_profile', None)
        if profile and profile.avatar:
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.avatar.url)
                return profile.avatar.url
            except Exception:
                return None
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_city(self, obj):
        profile = getattr(obj, 'customer_profile', None)
        return profile.city if profile else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_country(self, obj):
        profile = getattr(obj, 'customer_profile', None)
        return profile.country if profile else 'Bangladesh'

    @extend_schema_field(serializers.BooleanField())
    def get_is_verified(self, obj):
        profile = getattr(obj, 'customer_profile', None)
        return profile.is_verified if profile else False

    @extend_schema_field(serializers.IntegerField())
    def get_orders_count(self, obj):
        return obj.customer_orders.count()

    @extend_schema_field(serializers.IntegerField())
    def get_pending_orders_count(self, obj):
        return obj.customer_orders.filter(status='PENDING').count()

    @extend_schema_field(serializers.IntegerField())
    def get_approved_orders_count(self, obj):
        return obj.customer_orders.filter(status='APPROVED').count()

    @extend_schema_field(serializers.FloatField())
    def get_total_spent(self, obj):
        from django.db.models import Sum
        val = obj.customer_orders.filter(status='APPROVED').aggregate(total=Sum('total_amount'))['total']
        return float(val or 0.0)

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_last_order_date(self, obj):
        latest = obj.customer_orders.order_by('-created_at').first()
        return latest.created_at if latest else None


class SuperAdminCustomerListResponseSerializer(serializers.Serializer):
    total_customers = serializers.IntegerField(help_text="Total number of registered customer accounts")
    verified_customers = serializers.IntegerField(help_text="Number of verified customer accounts")
    customers = SuperAdminCustomerSerializer(many=True)



