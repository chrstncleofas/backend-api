import jwt
from rest_framework import authentication, exceptions
from rest_framework.request import Request
from django.conf import settings
from users.documents import User


class JWTAuthentication(authentication.BaseAuthentication):
    """Custom JWT authentication for mongoengine User documents."""

    keyword = 'Bearer'

    def authenticate(self, request: Request) -> tuple[User, str] | None:
        auth_header = authentication.get_authorization_header(request).split()

        if not auth_header or auth_header[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth_header) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No token provided.')
        if len(auth_header) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header. Token should not contain spaces.')

        token = auth_header[1].decode('utf-8')

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Access token has expired.')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid access token.')

        if payload.get('type') != 'access':
            raise exceptions.AuthenticationFailed('Invalid token type. Expected access token.')

        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found.')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User account is deactivated.')

        return (user, token)
