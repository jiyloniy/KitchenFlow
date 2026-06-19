from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.orders.models import Order
from apps.orders.permissions import IsCeoOrCashier, IsCeoOrReadOnly
from apps.orders.serializers import OrderSerializer
from apps.payments.models import Payment


class CompletePaymentSerializer(serializers.Serializer):
    payment_type = serializers.ChoiceField(
        choices=Payment.Method.choices,
        help_text='cash, card yoki click',
    )
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('0.01'),
        help_text='Real qabul qilingan summa',
    )


@method_decorator(name='list', decorator=swagger_auto_schema(operation_summary='Orderlar ro‘yxati', tags=('Orders',)))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(operation_summary='Order detail va payment ma’lumoti', tags=('Orders',)))
@method_decorator(name='create', decorator=swagger_auto_schema(operation_summary='Yangi order yaratish', tags=('Orders',)))
@method_decorator(name='update', decorator=swagger_auto_schema(operation_summary='Orderni to‘liq yangilash', tags=('Orders',)))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(operation_summary='Orderni qisman yangilash', tags=('Orders',)))
@method_decorator(name='destroy', decorator=swagger_auto_schema(operation_summary='Orderni o‘chirish', tags=('Orders',)))
class OrderViewSet(ModelViewSet):
    """
    Zakaz CRUD API.
    GET hamma uchun ochiq, yozish faqat CEO uchun.
    """
    queryset = Order.objects.select_related(
        'table',
        'payment__received_by',
    ).prefetch_related('items__product__images').order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = (IsCeoOrReadOnly,)

    def get_permissions(self):
        if self.action == 'close':
            return (IsCeoOrCashier(),)
        return super().get_permissions()

    def _complete_payment(self, request):
        serializer = CompletePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.get_object()

        try:
            with transaction.atomic():
                order.complete_payment(
                    serializer.validated_data['payment_type'],
                    serializer.validated_data['amount'],
                    request.user,
                )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        return Response(self.get_serializer(order).data)

    @swagger_auto_schema(
        method='post',
        operation_summary='Zakazni yopish va payment yaratish yoki yangilash',
        operation_description=(
            'Kassir yoki CEO payment_type va amount yuboradi. Mavjud payment bo‘lsa yangilanadi; '
            'order detail payment ma’lumoti bilan qaytadi.'
        ),
        request_body=CompletePaymentSerializer,
        responses={200: OrderSerializer},
        tags=('Orders',),
    )
    @action(detail=True, methods=('post',), url_path='close')
    def close(self, request, pk=None):
        return self._complete_payment(request)

# Create your views here.
