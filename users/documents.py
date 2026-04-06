import mongoengine
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc)


class User(mongoengine.Document):
    email = mongoengine.EmailField(required=True, unique=True)
    password = mongoengine.StringField(required=True)
    first_name = mongoengine.StringField(max_length=100)
    last_name = mongoengine.StringField(max_length=100)
    phone = mongoengine.StringField(max_length=20)
    role = mongoengine.StringField(
        default='customer',
        choices=['customer', 'merchant', 'rider', 'admin'],
    )
    is_active = mongoengine.BooleanField(default=True)
    avatar_url = mongoengine.StringField(default='')
    created_at = mongoengine.DateTimeField(default=_utcnow)
    updated_at = mongoengine.DateTimeField(default=_utcnow)

    meta = {
        'collection': 'users',
        'indexes': ['email', 'role'],
        'ordering': ['-created_at'],
    }

    @property
    def is_authenticated(self) -> bool:
        return True

    def save(self, *args, **kwargs):
        self.updated_at = _utcnow()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.role})"
