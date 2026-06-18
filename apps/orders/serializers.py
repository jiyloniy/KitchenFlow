from django.db import transaction
from rest_framework import serializers

from apps.orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'unit_price', 'total_price')
        read_only_fields = ('unit_price',)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    table_name = serializers.CharField(source='table.name', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = (
            'id',
            'code',
            'order_type',
            'order_type_display',
            'status',
            'status_display',
            'table',
            'table_name',
            'customer_name',
            'note',
            'items',
            'total_amount',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('code', 'total_amount', 'created_at', 'updated_at')

    def validate(self, attrs):
        order_type = attrs.get('order_type', getattr(self.instance, 'order_type', None))
        table = attrs.get('table', getattr(self.instance, 'table', None))

        if order_type == Order.Type.DINE_IN and table is None:
            raise serializers.ValidationError({'table': 'Oshxonani o‘zida zakaz uchun stol tanlang.'})
        if order_type == Order.Type.SABOY and table is not None:
            raise serializers.ValidationError({'table': 'Saboy zakaz uchun stol tanlanmaydi.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            product = item_data['product']
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item_data.get('quantity', 1),
                unit_price=product.price,
            )
        order.recalculate_total()
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                product = item_data['product']
                OrderItem.objects.create(
                    order=instance,
                    product=product,
                    quantity=item_data.get('quantity', 1),
                    unit_price=product.price,
                )
        instance.recalculate_total()
        return instance
