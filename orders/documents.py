import mongoengine # type: ignore
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc)


class OrderItem(mongoengine.EmbeddedDocument):
    product_id = mongoengine.StringField(required=True)
    product_name = mongoengine.StringField(required=True)
    quantity = mongoengine.IntField(required=True, min_value=1)
    price = mongoengine.DecimalField(required=True, min_value=0, precision=2)
    subtotal = mongoengine.DecimalField(precision=2)


class Order(mongoengine.Document):
    customer_id = mongoengine.StringField(required=True)
    merchant_id = mongoengine.StringField(required=True)
    rider_id = mongoengine.StringField()
    items = mongoengine.EmbeddedDocumentListField(OrderItem, required=True)
    total_amount = mongoengine.DecimalField(required=True, min_value=0, precision=2)
    delivery_fee = mongoengine.DecimalField(default=0, precision=2)
    status = mongoengine.StringField(
        default='pending',
        choices=[
            'pending',
            'confirmed',
            'preparing',
            'ready_for_pickup',
            'picked_up',
            'delivering',
            'delivered',
            'cancelled',
        ],
    )
    delivery_address = mongoengine.StringField()
    notes = mongoengine.StringField()
    receipt_url = mongoengine.StringField(default='')
    created_at = mongoengine.DateTimeField(default=_utcnow)
    updated_at = mongoengine.DateTimeField(default=_utcnow)

    meta = {
        'collection': 'orders',
        'indexes': ['customer_id', 'merchant_id', 'rider_id', 'status'],
        'ordering': ['-created_at'],
    }

    def save(self, *args, **kwargs):
        self.updated_at = _utcnow()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.id} - {self.status} (₱{self.total_amount})"
