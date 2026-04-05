import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings


def generate_access_token(user_id: str) -> str:
    payload = {
        'user_id': str(user_id),
        'type': 'access',
        'exp': datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_LIFETIME_MINUTES),
        'iat': datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def generate_refresh_token(user_id: str) -> str:
    payload = {
        'user_id': str(user_id),
        'type': 'refresh',
        'exp': datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_LIFETIME_DAYS),
        'iat': datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def generate_tokens(user_id: str) -> dict:
    return {
        'access_token': generate_access_token(user_id),
        'refresh_token': generate_refresh_token(user_id),
    }
