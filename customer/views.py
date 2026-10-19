from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import (
    CustomerRegistrationSerializer,
    CustomerLoginSerializer,
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    CustomerAuthResponseSerializer,
)


class CustomerProfilePageView(TemplateView):
    """
    Renders the dedicated Customer Profile and Account Details web page.
    """
    template_name = 'customer/profile.html'


class CustomerRegisterView(APIView):
    """
    Customer Registration Endpoint.
    Allows customers to register using their Email (e.g. Gmail) and Password.
    Returns Bearer access and refresh tokens upon successful registration.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Customer Authentication'],
        summary='Register Customer Account',
        description='Register a new customer account using Email (e.g. yourname@gmail.com) and Password. Returns Bearer access and refresh tokens.',
        request=CustomerRegistrationSerializer,
        responses={
            201: CustomerAuthResponseSerializer,
            400: OpenApiResponse(description='Validation error (e.g., email already exists or password mismatch)'),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = CustomerRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        result = serializer.save()
        user = result['user']
        user_data = CustomerProfileSerializer(user, context={'request': request}).data

        response_data = {
            "message": "Customer registered successfully.",
            "token_type": result['token_type'],
            "access_token": result['access_token'],
            "refresh_token": result['refresh_token'],
            "user": user_data,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class CustomerLoginView(APIView):
    """
    Customer Login Endpoint.
    Authenticates a customer via Email (Gmail) and Password.
    Returns Bearer access token, refresh token, and customer profile details.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Customer Authentication'],
        summary='Customer Login',
        description='Authenticate with your registered Email (e.g. Gmail) and Password to receive Bearer access and refresh tokens.',
        request=CustomerLoginSerializer,
        responses={
            200: CustomerAuthResponseSerializer,
            400: OpenApiResponse(description='Invalid email or password credentials'),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = CustomerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        user = validated_data['user']
        user_data = CustomerProfileSerializer(user, context={'request': request}).data

        response_data = {
            "message": "Login successful.",
            "token_type": validated_data['token_type'],
            "access_token": validated_data['access_token'],
            "refresh_token": validated_data['refresh_token'],
            "user": user_data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class CustomerProfileView(APIView):
    """
    Customer Profile Endpoint.
    Requires Bearer Token in Authorization header:
    Authorization: Bearer <access_token>
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=['Customer Profile'],
        summary='Get Current Customer Profile',
        description='Retrieve the profile details of the currently authenticated customer using Bearer token.',
        responses={
            200: CustomerProfileSerializer,
            401: OpenApiResponse(description='Unauthorized: Invalid or missing Bearer token'),
        }
    )
    def get(self, request, *args, **kwargs):
        serializer = CustomerProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Customer Profile'],
        summary='Update Customer Profile',
        description='Update personal information, phone number, address, and profile avatar (file or Base64).',
        request=CustomerProfileUpdateSerializer,
        responses={
            200: CustomerProfileSerializer,
            400: OpenApiResponse(description='Validation error in update data'),
            401: OpenApiResponse(description='Unauthorized: Invalid or missing Bearer token'),
        }
    )
    def put(self, request, *args, **kwargs):
        return self._update_profile(request)

    @extend_schema(
        tags=['Customer Profile'],
        summary='Partial Update Customer Profile',
        description='Partially update customer profile fields.',
        request=CustomerProfileUpdateSerializer,
        responses={
            200: CustomerProfileSerializer,
            400: OpenApiResponse(description='Validation error in update data'),
            401: OpenApiResponse(description='Unauthorized: Invalid or missing Bearer token'),
        }
    )
    def patch(self, request, *args, **kwargs):
        return self._update_profile(request)

    def _update_profile(self, request):
        serializer = CustomerProfileUpdateSerializer(
            instance=request.user,
            data=request.data,
            partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_user = serializer.save()
        response_serializer = CustomerProfileSerializer(updated_user, context={'request': request})
        return Response({
            "message": "Profile updated successfully.",
            "user": response_serializer.data
        }, status=status.HTTP_200_OK)
