from datetime import datetime, time
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.decorators import method_decorator
from django.utils.timezone import get_current_timezone, make_aware
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.orders.models import Order
from apps.orders.permissions import CanCreateOrder, IsCeoOrCashier, IsCeoOrReadOnly
from apps.orders.serializers import OrderSerializer
from apps.orders.table_status import sync_order_table_status
from apps.payments.models import PaymentPart


class PaymentPartInputSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=PaymentPart.Method.choices)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))


class CompletePaymentSerializer(serializers.Serializer):
    payments = PaymentPartInputSerializer(many=True, min_length=1, max_length=3)

    def validate_payments(self, parts):
        if len({part['method'] for part in parts}) != len(parts):
            raise serializers.ValidationError('Bir xil to‘lov usulini ikki marta yubormang.')
        return parts


@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        operation_summary='Orderlar ro‘yxati',
        tags=('Orders',),
        manual_parameters=[
            openapi.Parameter(
                'created_at_from',
                openapi.IN_QUERY,
                description='Filter orders created on or after this date/time (YYYY-MM-DD or ISO 8601).',
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATETIME,
            ),
            openapi.Parameter(
                'created_at_to',
                openapi.IN_QUERY,
                description='Filter orders created on or before this date/time (YYYY-MM-DD or ISO 8601).',
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATETIME,
            ),
        ],
    ),
)
@method_decorator(name='retrieve', decorator=swagger_auto_schema(operation_summary='Order detail va payment ma’lumoti', tags=('Orders',)))
@method_decorator(name='create', decorator=swagger_auto_schema(operation_summary='Yangi order yaratish', tags=('Orders',)))
@method_decorator(name='update', decorator=swagger_auto_schema(operation_summary='Orderni to‘liq yangilash', tags=('Orders',)))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(operation_summary='Orderni qisman yangilash', tags=('Orders',)))
@method_decorator(name='destroy', decorator=swagger_auto_schema(operation_summary='Orderni o‘chirish', tags=('Orders',)))
class OrderViewSet(ModelViewSet):
    """
    Zakaz CRUD API.
    GET hamma uchun ochiq. Order yaratish CEO, kassir va ofitsiant uchun;
    qolgan CRUD amallari faqat CEO uchun.
    """
    queryset = Order.objects.select_related(
        'table',
        'payment__received_by',
    ).prefetch_related(
        'items__product__category',
        'items__product__images',
        'payment__items',
        'payment__parts',
    ).order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = (IsCeoOrReadOnly,)

    def get_permissions(self):
        if self.action == 'create':
            return (CanCreateOrder(),)
        if self.action in ('update', 'partial_update', 'destroy'):
            return (CanCreateOrder(),)
        if self.action == 'close':
            return (IsCeoOrCashier(),)
        return super().get_permissions()

    def _parse_created_at_param(self, value, *, start_of_day=False, end_of_day=False):
        parsed = parse_datetime(value)
        if parsed is None:
            parsed_date = parse_date(value)
            if parsed_date is None:
                raise ParseError(
                    'created_at_from/created_at_to must be a valid date or datetime string.'
                )
            if start_of_day:
                parsed = datetime.combine(parsed_date, time.min)
            elif end_of_day:
                parsed = datetime.combine(parsed_date, time.max)
            else:
                parsed = datetime.combine(parsed_date, time.min)
        if parsed.tzinfo is None:
            parsed = make_aware(parsed, get_current_timezone())
        return parsed

    def get_queryset(self):
        queryset = super().get_queryset()
        created_at_from = self.request.query_params.get('created_at_from')
        created_at_to = self.request.query_params.get('created_at_to')

        if created_at_from:
            queryset = queryset.filter(
                created_at__gte=self._parse_created_at_param(created_at_from, start_of_day=True),
            )
        if created_at_to:
            queryset = queryset.filter(
                created_at__lte=self._parse_created_at_param(created_at_to, end_of_day=True),
            )
        return queryset

    def _complete_payment(self, request):
        serializer = CompletePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.get_object()

        try:
            with transaction.atomic():
                order.complete_payment(
                    serializer.validated_data['payments'], request.user,
                )
                sync_order_table_status(order)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        return Response(self.get_serializer(order).data)

    def perform_destroy(self, instance):
        table_id = instance.table_id
        instance.delete()
        sync_order_table_status(instance, previous_table_id=table_id)

    @swagger_auto_schema(
        method='post',
        operation_summary='Zakazni multi-payment bilan yopish',
        operation_description=(
            'Kassir yoki CEO payments ro‘yxatida cash, click va terminal summalarini yuboradi. '
            'Mavjud payment bo‘lsa to‘liq yangilanadi; '
            'order itemlari tarixiy PaymentItem snapshotlariga saqlanadi va order detail payment '
            'ma’lumoti bilan qaytadi.'
        ),
        request_body=CompletePaymentSerializer,
        responses={200: OrderSerializer},
        tags=('Orders',),
    )
    @action(detail=True, methods=('post',), url_path='close')
    def close(self, request, pk=None):
        return self._complete_payment(request)

# Create your views here.
