from decimal import Decimal

from rest_framework import serializers

from apps.orders.models import Order
from apps.payments.models import Payment, PaymentItem


class PaymentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentItem
        fields = (
            'id',
            'product',
            'product_name',
            'category_name',
            'quantity',
            'unit_price',
            'total_price',
        )
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    items = PaymentItemSerializer(many=True, read_only=True)
    order_code = serializers.CharField(source='order.display_code', read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    received_by_name = serializers.CharField(source='received_by.name', read_only=True)
    order_amount = serializers.DecimalField(
        source='order.total_amount', max_digits=14, decimal_places=2, read_only=True
    )
    difference_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Payment
        fields = (
            'id',
            'order',
            'order_code',
            'method',
            'method_display',
            'amount',
            'order_amount',
            'difference_amount',
            'items',
            'received_by',
            'received_by_name',
            'paid_at',
            'updated_at',
        )
        read_only_fields = fields


class PaymentWriteSerializer(serializers.Serializer):
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(),
        required=False,
        help_text='To‘lov qilinadigan order ID. Create so‘rovida majburiy.',
    )
    payment_type = serializers.ChoiceField(
        choices=Payment.Method.choices,
        required=False,
        help_text='To‘lov turi: cash, card yoki click.',
    )
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('0.01'),
        required=False,
        help_text='Real qabul qilingan to‘lov summasi.',
    )

    def validate(self, attrs):
        if self.instance is None:
            order = attrs.get('order')
            if order is None:
                raise serializers.ValidationError({'order': 'Order ID majburiy.'})
            if 'payment_type' not in attrs:
                raise serializers.ValidationError({'payment_type': 'To‘lov turini tanlang.'})
            if 'amount' not in attrs:
                raise serializers.ValidationError({'amount': 'To‘lov summasini kiriting.'})
            if order.is_paid:
                raise serializers.ValidationError({
                    'order': 'Bu order uchun payment mavjud. PATCH orqali yangilang.'
                })
            if not order.items.exists():
                raise serializers.ValidationError({'order': 'Mahsulotsiz orderni yopib bo‘lmaydi.'})
        else:
            order = attrs.get('order')
            if order and order.pk != self.instance.order_id:
                raise serializers.ValidationError({'order': 'Payment orderini o‘zgartirib bo‘lmaydi.'})
            if not self.partial:
                if 'payment_type' not in attrs:
                    raise serializers.ValidationError({'payment_type': 'To‘lov turini tanlang.'})
                if 'amount' not in attrs:
                    raise serializers.ValidationError({'amount': 'To‘lov summasini kiriting.'})
        return attrs

    def create(self, validated_data):
        order = validated_data['order']
        return order.complete_payment(
            validated_data['payment_type'],
            validated_data['amount'],
            validated_data.get('received_by'),
        )

    def update(self, instance, validated_data):
        return instance.order.complete_payment(
            validated_data.get('payment_type', instance.method),
            validated_data.get('amount', instance.amount),
            validated_data.get('received_by'),
        )
