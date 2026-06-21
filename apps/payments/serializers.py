from rest_framework import serializers

from apps.orders.models import Order
from apps.payments.models import Payment, PaymentItem, PaymentPart


class PaymentPartSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)

    class Meta:
        model = PaymentPart
        fields = ('id', 'method', 'method_display', 'amount')
        read_only_fields = ('id', 'method_display')


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
    payments = PaymentPartSerializer(source='parts', many=True, read_only=True)
    order_code = serializers.CharField(source='order.display_code', read_only=True)
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
            'amount',
            'payments',
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
    payments = PaymentPartSerializer(many=True, required=False)

    def validate(self, attrs):
        if self.instance is None:
            order = attrs.get('order')
            if order is None:
                raise serializers.ValidationError({'order': 'Order ID majburiy.'})
            if not attrs.get('payments'):
                raise serializers.ValidationError({'payments': 'Kamida bitta to‘lov kiriting.'})
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
                if not attrs.get('payments'):
                    raise serializers.ValidationError({'payments': 'Kamida bitta to‘lov kiriting.'})
        parts = attrs.get('payments')
        if parts and len({part['method'] for part in parts}) != len(parts):
            raise serializers.ValidationError({'payments': 'Bir usulni faqat bir marta kiriting.'})
        return attrs

    def create(self, validated_data):
        order = validated_data['order']
        return order.complete_payment(
            validated_data['payments'], validated_data.get('received_by'),
        )

    def update(self, instance, validated_data):
        return instance.order.complete_payment(
            validated_data.get('payments', list(instance.parts.values('method', 'amount'))),
            validated_data.get('received_by', instance.received_by),
        )
