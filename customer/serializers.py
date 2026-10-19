import base64
import uuid
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomerProfile


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
    Update Customer profile details including name, phone, address, and avatar.
    """
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    avatar = CustomerAvatarField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    postal_code = serializers.CharField(required=False, allow_blank=True)

    def update(self, instance, validated_data):
        # Update User model fields
        if 'first_name' in validated_data:
            instance.first_name = validated_data['first_name']
        if 'last_name' in validated_data:
            instance.last_name = validated_data['last_name']
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
