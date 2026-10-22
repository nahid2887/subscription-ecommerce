from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from .models import TermsAndConditions
from .permissions import IsSuperUserOrReadOnly
from .serializers import (
    TermsAndConditionsSerializer,
    TermsAndConditionsCreateUpdateSerializer,
    TermsMessageResponseSerializer,
)

DEFAULT_INITIAL_TERMS_CONTENT = (
    "Welcome to Subverse Marketplace.\n\n"
    "1. Acceptance of Terms: By accessing or purchasing subscriptions through our platform, "
    "you agree to be bound by these Terms and Conditions.\n\n"
    "2. Subscriptions & Billing: All recurring subscriptions are processed automatically. "
    "Delivery of digital credentials or service access occurs upon verified payment.\n\n"
    "3. Replacement & Warranty: Products covered under warranty are eligible for instant replacement "
    "subject to our replacement policies.\n\n"
    "4. Conduct: Unauthorized sharing, resale, or abuse of account credentials is strictly prohibited.\n\n"
    "5. Amendments: We reserve the right to revise these terms. Continued usage implies acceptance "
    "of updated terms."
)


def get_or_initialize_active_terms(user=None):
    """
    Helper to fetch the current active TermsAndConditions.
    If none exists in the database, automatically bootstraps an initial active version.
    """
    terms = TermsAndConditions.get_active()
    if not terms:
        terms = TermsAndConditions.objects.create(
            title="Terms and Conditions",
            content=DEFAULT_INITIAL_TERMS_CONTENT,
            version="1.0",
            is_active=True,
            created_by=user if (user and user.is_authenticated) else None,
            updated_by=user if (user and user.is_authenticated) else None,
        )
    return terms


class ActiveTermsAndConditionsView(APIView):
    """
    API endpoint for viewing and managing the primary active Terms and Conditions.
    - All users (guest visitors, customers, admins) can view (show) it.
    - Only Super Admin users can edit or create it.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsSuperUserOrReadOnly]

    @extend_schema(
        tags=['Terms and Conditions'],
        operation_id='terms_get_active',
        summary='Get Active Terms and Conditions',
        description=(
            "Retrieves the currently published/active Terms and Conditions.\n\n"
            "**Access:** Public (all users, unauthenticated visitors, and customers can view)."
        ),
        responses={
            200: OpenApiResponse(
                response=TermsAndConditionsSerializer,
                description="The active Terms and Conditions document."
            ),
        },
        examples=[
            OpenApiExample(
                'Active Terms Example',
                value={
                    "id": 1,
                    "title": "Terms and Conditions",
                    "content": DEFAULT_INITIAL_TERMS_CONTENT,
                    "version": "1.0",
                    "is_active": True,
                    "effective_date": "2026-01-01T00:00:00Z",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "created_by": {"id": 1, "username": "admin", "email": "admin@subverse.io"},
                    "updated_by": {"id": 1, "username": "admin", "email": "admin@subverse.io"}
                },
                response_only=True,
            )
        ]
    )
    def get(self, request):
        terms = get_or_initialize_active_terms(request.user if request.user.is_authenticated else None)
        serializer = TermsAndConditionsSerializer(terms)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Terms and Conditions'],
        operation_id='terms_create',
        summary='Create New Terms and Conditions',
        description=(
            "Creates a new Terms and Conditions version.\n\n"
            "**Access:** Super Admin only (Bearer JWT or active Super Admin session required).\n"
            "If `is_active` is true (default), this version will automatically become the active version."
        ),
        request=TermsAndConditionsCreateUpdateSerializer,
        responses={
            201: OpenApiResponse(
                response=TermsAndConditionsSerializer,
                description="New Terms and Conditions record created successfully."
            ),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            403: OpenApiResponse(description="Permission denied. Only Super Admin can perform this action."),
        },
        examples=[
            OpenApiExample(
                'Create Terms Request',
                value={
                    "title": "Terms of Service & License Agreement",
                    "content": "All sales are final. Digital goods are delivered immediately...",
                    "version": "1.1",
                    "is_active": True
                },
                request_only=True,
            )
        ]
    )
    def post(self, request):
        serializer = TermsAndConditionsCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        terms = TermsAndConditions.objects.create(
            title=validated_data.get('title', 'Terms and Conditions'),
            content=validated_data['content'],
            version=validated_data.get('version', '1.0'),
            is_active=validated_data.get('is_active', True),
            effective_date=validated_data.get('effective_date', timezone.now()),
            created_by=request.user,
            updated_by=request.user,
        )
        return Response(
            TermsAndConditionsSerializer(terms).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        tags=['Terms and Conditions'],
        operation_id='terms_update_active',
        summary='Edit Active Terms and Conditions (Full Update)',
        description=(
            "Replaces/updates the currently active Terms and Conditions.\n\n"
            "**Access:** Super Admin only (Bearer JWT or active Super Admin session required)."
        ),
        request=TermsAndConditionsCreateUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=TermsAndConditionsSerializer,
                description="Active Terms and Conditions updated successfully."
            ),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            403: OpenApiResponse(description="Permission denied. Only Super Admin can perform this action."),
        }
    )
    def put(self, request):
        terms = get_or_initialize_active_terms(request.user)
        serializer = TermsAndConditionsCreateUpdateSerializer(terms, data=request.data)
        serializer.is_valid(raise_exception=True)
        terms.title = serializer.validated_data.get('title', terms.title)
        terms.content = serializer.validated_data.get('content', terms.content)
        terms.version = serializer.validated_data.get('version', terms.version)
        if 'is_active' in serializer.validated_data:
            terms.is_active = serializer.validated_data['is_active']
        if 'effective_date' in serializer.validated_data:
            terms.effective_date = serializer.validated_data['effective_date']
        terms.updated_by = request.user
        terms.save()
        return Response(TermsAndConditionsSerializer(terms).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Terms and Conditions'],
        operation_id='terms_partial_update_active',
        summary='Edit Active Terms and Conditions (Partial Update)',
        description=(
            "Partially edits the currently active Terms and Conditions.\n\n"
            "**Access:** Super Admin only (Bearer JWT or active Super Admin session required)."
        ),
        request=TermsAndConditionsCreateUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=TermsAndConditionsSerializer,
                description="Active Terms and Conditions partially updated successfully."
            ),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            403: OpenApiResponse(description="Permission denied. Only Super Admin can perform this action."),
        }
    )
    def patch(self, request):
        terms = get_or_initialize_active_terms(request.user)
        serializer = TermsAndConditionsCreateUpdateSerializer(terms, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for attr, value in serializer.validated_data.items():
            setattr(terms, attr, value)
        terms.updated_by = request.user
        terms.save()
        return Response(TermsAndConditionsSerializer(terms).data, status=status.HTTP_200_OK)


class TermsAndConditionsHistoryView(APIView):
    """
    Endpoint for listing all versions/history of Terms and Conditions.
    - All users can show/view it.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsSuperUserOrReadOnly]

    @extend_schema(
        tags=['Terms and Conditions'],
        operation_id='terms_get_history',
        summary='List Terms and Conditions History / Versions',
        description=(
            "Retrieves all recorded versions of Terms and Conditions, ordered by active status and creation date.\n\n"
            "**Access:** Public (all users can view)."
        ),
        responses={
            200: OpenApiResponse(
                response=TermsAndConditionsSerializer(many=True),
                description="List of all Terms and Conditions versions."
            ),
        }
    )
    def get(self, request):
        # Auto-initialize if empty
        get_or_initialize_active_terms(request.user if request.user.is_authenticated else None)
        queryset = TermsAndConditions.objects.all().order_by('-is_active', '-created_at')
        serializer = TermsAndConditionsSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TermsAndConditionsDetailView(APIView):
    """
    Endpoint for retrieving, editing, or deleting a specific Terms and Conditions record by ID.
    - All users can show/view it (GET).
    - Only Super Admin can edit (PUT, PATCH) or delete (DELETE) it.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsSuperUserOrReadOnly]

    def get_object(self, pk):
        try:
            return TermsAndConditions.objects.get(pk=pk)
        except TermsAndConditions.DoesNotExist:
            return None

    @extend_schema(
        tags=['Terms and Conditions'],
        operation_id='terms_get_by_id',
        summary='Get Terms and Conditions by ID',
        description=(
            "Retrieves a specific Terms and Conditions document by its unique ID.\n\n"
            "**Access:** Public (all users can view)."
        ),
        responses={
            200: OpenApiResponse(
                response=TermsAndConditionsSerializer,
                description="Terms and Conditions details."
            ),
            404: OpenApiResponse(description="Terms and Conditions not found."),
        }
    )
    def get(self, request, pk):
        terms = self.get_object(pk)
        if not terms:
            return Response({"detail": "Terms and Conditions not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TermsAndConditionsSerializer(terms)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Terms and Conditions'],
        operation_id='terms_update_by_id',
        summary='Edit Terms and Conditions by ID (Full Update)',
        description=(
            "Replaces/updates a specific Terms and Conditions document by its ID.\n\n"
            "**Access:** Super Admin only (Bearer JWT or active Super Admin session required)."
        ),
        request=TermsAndConditionsCreateUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=TermsAndConditionsSerializer,
                description="Terms and Conditions updated successfully."
            ),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            403: OpenApiResponse(description="Permission denied. Only Super Admin can perform this action."),
            404: OpenApiResponse(description="Terms and Conditions not found."),
        }
    )
    def put(self, request, pk):
        terms = self.get_object(pk)
        if not terms:
            return Response({"detail": "Terms and Conditions not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TermsAndConditionsCreateUpdateSerializer(terms, data=request.data)
        serializer.is_valid(raise_exception=True)
        terms.title = serializer.validated_data.get('title', terms.title)
        terms.content = serializer.validated_data.get('content', terms.content)
        terms.version = serializer.validated_data.get('version', terms.version)
        if 'is_active' in serializer.validated_data:
            terms.is_active = serializer.validated_data['is_active']
        if 'effective_date' in serializer.validated_data:
            terms.effective_date = serializer.validated_data['effective_date']
        terms.updated_by = request.user
        terms.save()
        return Response(TermsAndConditionsSerializer(terms).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Terms and Conditions'],
        operation_id='terms_partial_update_by_id',
        summary='Edit Terms and Conditions by ID (Partial Update)',
        description=(
            "Partially edits fields of a specific Terms and Conditions document by its ID.\n\n"
            "**Access:** Super Admin only (Bearer JWT or active Super Admin session required)."
        ),
        request=TermsAndConditionsCreateUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=TermsAndConditionsSerializer,
                description="Terms and Conditions partially updated successfully."
            ),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            403: OpenApiResponse(description="Permission denied. Only Super Admin can perform this action."),
            404: OpenApiResponse(description="Terms and Conditions not found."),
        }
    )
    def patch(self, request, pk):
        terms = self.get_object(pk)
        if not terms:
            return Response({"detail": "Terms and Conditions not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TermsAndConditionsCreateUpdateSerializer(terms, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for attr, value in serializer.validated_data.items():
            setattr(terms, attr, value)
        terms.updated_by = request.user
        terms.save()
        return Response(TermsAndConditionsSerializer(terms).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Terms and Conditions'],
        operation_id='terms_delete_by_id',
        summary='Delete Terms and Conditions by ID',
        description=(
            "Deletes a specific Terms and Conditions document.\n\n"
            "**Access:** Super Admin only (Bearer JWT or active Super Admin session required)."
        ),
        responses={
            200: OpenApiResponse(
                response=TermsMessageResponseSerializer,
                description="Terms and Conditions deleted successfully."
            ),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            403: OpenApiResponse(description="Permission denied. Only Super Admin can perform this action."),
            404: OpenApiResponse(description="Terms and Conditions not found."),
        }
    )
    def delete(self, request, pk):
        terms = self.get_object(pk)
        if not terms:
            return Response({"detail": "Terms and Conditions not found."}, status=status.HTTP_404_NOT_FOUND)
        was_active = terms.is_active
        terms.delete()

        # If deleted terms was active, activate the next most recent one if available
        if was_active:
            next_terms = TermsAndConditions.objects.order_by('-created_at').first()
            if next_terms:
                next_terms.is_active = True
                next_terms.save(update_fields=['is_active'])

        return Response(
            {"detail": "Terms and Conditions deleted successfully."},
            status=status.HTTP_200_OK
        )
