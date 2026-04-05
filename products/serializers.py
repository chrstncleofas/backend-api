from rest_framework import serializers


class ProductSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    stock = serializers.IntegerField(min_value=0, default=0)
    images = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    merchant_id = serializers.CharField(read_only=True)
    is_available = serializers.BooleanField(default=True)
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ProductCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    stock = serializers.IntegerField(min_value=0, default=0)
    images = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    is_available = serializers.BooleanField(default=True)
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list)


class ProductUpdateSerializer(serializers.Serializer):
    """All fields optional for partial updates — validated before save."""
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    stock = serializers.IntegerField(min_value=0, required=False)
    images = serializers.ListField(child=serializers.CharField(), required=False)
    is_available = serializers.BooleanField(required=False)
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False)
