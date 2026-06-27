from django.db import transaction
from rest_framework import serializers

from apps.orders.models import Order, OrderItem
from apps.orders.table_status import sync_order_table_status
from apps.payments.serializers import PaymentSerializer
from apps.products.models import Product
from apps.products.serializers import ProductSerializer


class OrderProductField(serializers.PrimaryKeyRelatedField):
    """Accept a product ID on write and return the complete product on read."""

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return ProductSerializer(value, context=self.context).data


class OrderItemSerializer(serializers.ModelSerializer):
    product = OrderProductField(queryset=Product.objects.all())
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image_url = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            'id',
            'product',
            'product_name',
            'product_image_url',
            'quantity',
            'unit_price',
            'total_price',
        )
        read_only_fields = ('unit_price',)

    def get_product_image_url(self, item):
        image = item.product.display_image
        if not image:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(image.url) if request else image.url


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    payment = PaymentSerializer(read_only=True)
    table_name = serializers.CharField(source='table.name', read_only=True)
    table_category_name = serializers.CharField(source='table.category.name', read_only=True)
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
            'table_category_name',
            'customer_name',
            'note',
            'items',
            'total_amount',
            'payment',
            'created_at',
            'updated_at',
        )
        # Order holatini oddiy CRUD orqali yopib bo‘lmaydi. Yopish va payment
        # yaratish faqat POST /api/orders/{id}/close/ orqali bajariladi.
        read_only_fields = ('code', 'status', 'total_amount', 'created_at', 'updated_at')

    def validate(self, attrs):
        order_type = attrs.get('order_type', getattr(self.instance, 'order_type', None))
        table = attrs.get('table', getattr(self.instance, 'table', None))
        items = attrs.get('items')

        if order_type == Order.Type.DINE_IN and table is None:
            raise serializers.ValidationError({'table': 'Oshxonani o‘zida zakaz uchun stol tanlang.'})
        if order_type == Order.Type.SABOY and table is not None:
            raise serializers.ValidationError({'table': 'Saboy zakaz uchun stol tanlanmaydi.'})
        if self.instance is None and not items:
            raise serializers.ValidationError({'items': 'Kamida bitta mahsulot qo‘shing.'})
        if items is not None and not items:
            raise serializers.ValidationError({'items': 'Kamida bitta mahsulot qo‘shing.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        # Client noto‘g‘ri status yuborsa ham yangi order doim ochiq yaratiladi.
        validated_data['status'] = Order.Status.OPEN
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
        sync_order_table_status(order)
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        previous_table_id = instance.table_id
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
        sync_order_table_status(instance, previous_table_id=previous_table_id)
        return instance
