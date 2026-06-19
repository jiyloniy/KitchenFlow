from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.orders.models import Order
from apps.orders.permissions import IsCeoOrCashier
from apps.payments.models import Payment
from apps.payments.serializers import PaymentSerializer, PaymentWriteSerializer


PAYMENT_CREATE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=('order', 'payment_type', 'amount'),
    properties={
        'order': openapi.Schema(type=openapi.TYPE_INTEGER, description='Order ID', example=12),
        'payment_type': openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=('cash', 'card', 'click'),
            example='click',
        ),
        'amount': openapi.Schema(
            type=openapi.TYPE_STRING,
            format='decimal',
            description='Real qabul qilingan summa',
            example='145000.00',
        ),
    },
)

PAYMENT_UPDATE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=('payment_type', 'amount'),
    properties={
        'payment_type': PAYMENT_CREATE_SCHEMA.properties['payment_type'],
        'amount': PAYMENT_CREATE_SCHEMA.properties['amount'],
    },
)

PAYMENT_PATCH_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties=PAYMENT_UPDATE_SCHEMA.properties,
)


class PaymentViewSet(ModelViewSet):
    """
    To‘lovlar CRUD API.

    Kassir va CEO to‘lov yaratishi, ko‘rishi, yangilashi va o‘chirishi mumkin.
    Har bir order uchun faqat bitta payment mavjud bo‘ladi.
    """

    queryset = Payment.objects.select_related('order', 'received_by').order_by('-paid_at')
    permission_classes = (IsCeoOrCashier,)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return PaymentWriteSerializer
        return PaymentSerializer

    @swagger_auto_schema(operation_summary='Paymentlar ro‘yxati', tags=('Payments',))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary='Payment detail', tags=('Payments',))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Payment yaratish va zakazni yopish',
        operation_description=(
            'Order ID, payment turi va real qabul qilingan summa yuboriladi. '
            'Payment yaratilgach order avtomatik yopiladi.'
        ),
        request_body=PAYMENT_CREATE_SCHEMA,
        responses={201: PaymentSerializer},
        tags=('Payments',),
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(received_by=request.user)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary='Paymentni to‘liq yangilash',
        request_body=PAYMENT_UPDATE_SCHEMA,
        responses={200: PaymentSerializer},
        tags=('Payments',),
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        payment = self.get_object()
        serializer = self.get_serializer(payment, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(received_by=request.user)
        return Response(PaymentSerializer(payment).data)

    @swagger_auto_schema(
        operation_summary='Paymentni qisman yangilash',
        request_body=PAYMENT_PATCH_SCHEMA,
        responses={200: PaymentSerializer},
        tags=('Payments',),
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Paymentni o‘chirish',
        operation_description='Payment o‘chiriladi va order qayta ochiq holatga o‘tkaziladi.',
        responses={204: 'Payment o‘chirildi'},
        tags=('Payments',),
    )
    def destroy(self, request, *args, **kwargs):
        payment = self.get_object()
        order = payment.order
        with transaction.atomic():
            payment.delete()
            if order.status == Order.Status.CLOSED:
                order.status = Order.Status.OPEN
                order.save(update_fields=('status', 'updated_at'))
        return Response(status=status.HTTP_204_NO_CONTENT)
