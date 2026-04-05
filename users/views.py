import jwt
import bcrypt
import logging
from botocore.exceptions import ClientError
from rest_framework import status
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser
from drf_spectacular.utils import extend_schema

from config.s3 import s3_service
from config.serializers import FileUploadSerializer

from users.documents import User
from users.serializers import (
    UserSerializer,
    RegisterSerializer,
    ProfileUpdateSerializer,
    LoginSerializer,
    TokenRefreshSerializer,
    ChangePasswordSerializer,
)
from users.tokens import generate_tokens, decode_token

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Check if user already exists
        if User.objects(email=data['email']).first():
            return Response(
                {'success': False, 'error': 'Email already registered.'},
                status=status.HTTP_409_CONFLICT,
            )

        # Hash password
        hashed_password = bcrypt.hashpw(
            data['password'].encode('utf-8'),
            bcrypt.gensalt(),
        ).decode('utf-8')

        user = User(
            email=data['email'],
            password=hashed_password,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone=data.get('phone', ''),
            role=data.get('role', 'customer'),
        )
        user.save()

        tokens = generate_tokens(str(user.id))

        return Response(
            {
                'success': True,
                'data': {
                    'user': UserSerializer(user).data,
                    'tokens': tokens,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        user = User.objects(email=data['email']).first()
        if not user:
            return Response(
                {'success': False, 'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not bcrypt.checkpw(data['password'].encode('utf-8'), user.password.encode('utf-8')):
            return Response(
                {'success': False, 'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {'success': False, 'error': 'Account is deactivated.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        tokens = generate_tokens(str(user.id))

        return Response(
            {
                'success': True,
                'data': {
                    'user': UserSerializer(user).data,
                    'tokens': tokens,
                },
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=TokenRefreshSerializer)
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = decode_token(serializer.validated_data['refresh_token'])
        except jwt.ExpiredSignatureError:
            return Response(
                {'success': False, 'error': 'Refresh token has expired.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except jwt.InvalidTokenError:
            return Response(
                {'success': False, 'error': 'Invalid refresh token.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if payload.get('type') != 'refresh':
            return Response(
                {'success': False, 'error': 'Invalid token type.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            return Response(
                {'success': False, 'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        tokens = generate_tokens(str(user.id))

        return Response(
            {'success': True, 'data': {'tokens': tokens}},
            status=status.HTTP_200_OK,
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(
            {'success': True, 'data': UserSerializer(request.user).data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=ProfileUpdateSerializer, responses={200: UserSerializer})
    def patch(self, request: Request) -> Response:
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        for field, value in serializer.validated_data.items():
            setattr(user, field, value)

        user.save()

        return Response(
            {'success': True, 'data': UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer)
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        data = serializer.validated_data

        if not bcrypt.checkpw(data['old_password'].encode('utf-8'), user.password.encode('utf-8')):
            return Response(
                {'success': False, 'error': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.password = bcrypt.hashpw(
            data['new_password'].encode('utf-8'),
            bcrypt.gensalt(),
        ).decode('utf-8')
        user.save()

        return Response(
            {'success': True, 'message': 'Password changed successfully.'},
            status=status.HTTP_200_OK,
        )


class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    @extend_schema(
        request=FileUploadSerializer,
        responses={200: UserSerializer},
        description='Upload avatar image (JPEG, PNG, WebP, 5–25 MB).',
    )
    def post(self, request: Request) -> Response:
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user_id = str(user.id)

        # Delete old avatar from S3 if one exists
        if user.avatar_url:
            s3_service.delete_file_by_url(user.avatar_url)

        try:
            result = s3_service.upload_image(
                serializer.validated_data['file'],
                f"avatars/{user_id}",
            )
        except ValueError as exc:
            return Response(
                {'success': False, 'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ClientError:
            logger.exception("S3 avatar upload failed for user %s", user_id)
            return Response(
                {'success': False, 'error': 'File upload failed. Try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        user.avatar_url = result['url']
        user.save()

        return Response(
            {'success': True, 'data': UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={200: UserSerializer}, description='Remove avatar.')
    def delete(self, request: Request) -> Response:
        user = request.user

        if not user.avatar_url:
            return Response(
                {'success': False, 'error': 'No avatar to remove.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        s3_service.delete_file_by_url(user.avatar_url)

        user.avatar_url = ''
        user.save()

        return Response(
            {'success': True, 'data': UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )
