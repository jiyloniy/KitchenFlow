from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.serializers import PaymentSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'unit_price', 'total_price')
        read_only_fields = ('unit_price',)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    payment = PaymentSerializer(read_only=True)
    payment_method = serializers.ChoiceField(
        choices=Payment.Method.choices,
        write_only=True,
        required=False,
    )
    payment_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('0.01'),
        write_only=True,
        required=False,
    )
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
            'payment',
            'payment_method',
            'payment_amount',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('code', 'total_amount', 'created_at', 'updated_at')

    def validate(self, attrs):
        order_type = attrs.get('order_type', getattr(self.instance, 'order_type', None))
        table = attrs.get('table', getattr(self.instance, 'table', None))
        status = attrs.get('status', getattr(self.instance, 'status', Order.Status.OPEN))
        payment_method = attrs.get('payment_method')
        payment_amount = attrs.get('payment_amount')
        has_payment = bool(self.instance and self.instance.is_paid)
        items = attrs.get('items')

        if order_type == Order.Type.DINE_IN and table is None:
            raise serializers.ValidationError({'table': 'Oshxonani o‘zida zakaz uchun stol tanlang.'})
        if order_type == Order.Type.SABOY and table is not None:
            raise serializers.ValidationError({'table': 'Saboy zakaz uchun stol tanlanmaydi.'})
        if status == Order.Status.CLOSED and not payment_method and not has_payment:
            raise serializers.ValidationError({
                'payment_method': 'Zakazni yopish uchun to‘lov turini tanlang.'
            })
        if status == Order.Status.CLOSED and payment_amount is None and not has_payment:
            raise serializers.ValidationError({
                'payment_amount': 'Zakazni yopish uchun to‘lov summasini kiriting.'
            })
        if not has_payment and payment_method and payment_amount is None:
            raise serializers.ValidationError({'payment_amount': 'To‘lov summasini kiriting.'})
        if not has_payment and payment_amount is not None and not payment_method:
            raise serializers.ValidationError({'payment_method': 'To‘lov turini tanlang.'})
        if has_payment and status != Order.Status.CLOSED:
            raise serializers.ValidationError({
                'status': 'To‘lov qilingan zakaz yopiq holatda qolishi kerak.'
            })
        if self.instance is None and not items:
            raise serializers.ValidationError({'items': 'Kamida bitta mahsulot qo‘shing.'})
        if items is not None and not items:
            raise serializers.ValidationError({'items': 'Kamida bitta mahsulot qo‘shing.'})
        return attrs

    def _request_user(self):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user
        return None

    @transaction.atomic
    def create(self, validated_data):
        payment_method = validated_data.pop('payment_method', None)
        payment_amount = validated_data.pop('payment_amount', None)
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
        if payment_method:
            order.complete_payment(payment_method, payment_amount, self._request_user())
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        payment_method = validated_data.pop('payment_method', None)
        payment_amount = validated_data.pop('payment_amount', None)
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
        if payment_method or payment_amount is not None:
            method = payment_method or instance.payment.method
            amount = payment_amount if payment_amount is not None else instance.payment.amount
            instance.complete_payment(method, amount, self._request_user())
        return instance
