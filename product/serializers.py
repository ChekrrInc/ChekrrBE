from .models import Product
from rest_framework import serializers

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model=Product
        fields = [
            'id',
            'title',
            'description',
            'image',
            'price',
            'quantity',
            'owner_name',
            'store_name',
            'product_hash',
            'is_paid',
        ]
