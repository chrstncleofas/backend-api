import mongoengine
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(mongoengine.Document):
    name = mongoengine.StringField(required=True, max_length=200)
    description = mongoengine.StringField()
    price = mongoengine.DecimalField(required=True, min_value=0, precision=2)
    category = mongoengine.StringField(max_length=100)
    stock = mongoengine.IntField(default=0, min_value=0)
    images = mongoengine.ListField(mongoengine.StringField())
    merchant_id = mongoengine.StringField(required=True)
    is_available = mongoengine.BooleanField(default=True)
    tags = mongoengine.ListField(mongoengine.StringField(max_length=50))
    created_at = mongoengine.DateTimeField(default=_utcnow)
    updated_at = mongoengine.DateTimeField(default=_utcnow)

    meta = {
        'collection': 'products',
        'indexes': ['category', 'merchant_id', 'is_available', 'tags'],
        'ordering': ['-created_at'],
    }

    def save(self, *args: object, **kwargs: object) -> 'Product':
        self.updated_at = _utcnow()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} - ₱{self.price}"
