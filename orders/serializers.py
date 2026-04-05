from rest_framework import serializers


class OrderItemSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    product_name = serializers.CharField(read_only=True)
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)


class OrderItemCreateSerializer(serializers.Serializer):
    """Only product_id + quantity needed — server looks up price from DB."""
    product_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class OrderSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    customer_id = serializers.CharField(read_only=True)
    merchant_id = serializers.CharField()
    rider_id = serializers.CharField(required=False, allow_blank=True)
    items = OrderItemSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = serializers.ChoiceField(
        choices=['pending', 'confirmed', 'preparing', 'ready_for_pickup', 'picked_up', 'delivering', 'delivered', 'cancelled'],
        read_only=True,
    )
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    receipt_url = serializers.CharField(read_only=True, default='')
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class OrderCreateSerializer(serializers.Serializer):
    merchant_id = serializers.CharField()
    items = OrderItemCreateSerializer(many=True)
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_address = serializers.CharField(max_length=500)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=['confirmed', 'preparing', 'ready_for_pickup', 'picked_up', 'delivering', 'delivered', 'cancelled'],
    )
