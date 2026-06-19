from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment, PaymentItem
from apps.products.models import Category, Product
from apps.tables.models import Table, TableCategory
from apps.users.models import User


class PaymentFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ceo',
            password='strong-password',
            name='Direktor',
            role=User.Role.CEO,
        )
        self.cashier = User.objects.create_user(
            username='cashier',
            password='strong-password',
            name='Kassir',
            role=User.Role.CASHIER,
        )
        category = Category.objects.create(name='Taomlar', slug='taomlar')
        self.product = Product.objects.create(
            category=category,
            name='Osh',
            slug='osh',
            price=Decimal('25000'),
        )
        table_category = TableCategory.objects.create(name='Zal', slug='zal')
        self.table = Table.objects.create(
            category=table_category,
            name='Birinchi stol',
            number=1,
        )
        self.order = Order.objects.create(table=self.table)
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit_price=self.product.price,
        )
        self.order.recalculate_total()
        self.client.force_authenticate(self.user)

    def test_close_action_closes_order_and_creates_payment(self):
        response = self.client.post(
            reverse('api-order-close', args=(self.order.pk,)),
            {'payment_type': Payment.Method.CLICK, 'amount': '48000.00'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CLOSED)
        self.assertEqual(self.order.payment.method, Payment.Method.CLICK)
        self.assertEqual(self.order.payment.amount, Decimal('48000'))
        self.assertEqual(response.data['payment']['difference_amount'], '-2000.00')
        self.assertEqual(response.data['payment']['method_display'], 'Click')
        self.assertEqual(len(response.data['payment']['items']), 1)
        self.assertEqual(response.data['payment']['items'][0]['product_name'], 'Osh')
        self.assertEqual(response.data['payment']['items'][0]['total_price'], '50000.00')

    def test_cashier_can_close_order_and_update_payment_type(self):
        self.client.force_authenticate(self.cashier)
        close_url = reverse('api-order-close', args=(self.order.pk,))

        first_response = self.client.post(
            close_url,
            {'payment_type': Payment.Method.CLICK, 'amount': '50000.00'},
            format='json',
        )
        second_response = self.client.post(
            close_url,
            {'payment_type': Payment.Method.CARD, 'amount': '49000.00'},
            format='json',
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 1)
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.method, Payment.Method.CARD)
        self.assertEqual(payment.received_by, self.cashier)

    def test_cashier_cannot_edit_order_through_crud_endpoint(self):
        self.client.force_authenticate(self.cashier)
        response = self.client.patch(
            reverse('api-order-detail', args=(self.order.pk,)),
            {'customer_name': 'Changed'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_order_detail_returns_absolute_product_image_url(self):
        self.product.banner_image = 'products/banners/order-test.jpg'
        self.product.save(update_fields=('banner_image', 'updated_at'))

        response = self.client.get(reverse('api-order-detail', args=(self.order.pk,)))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['items'][0]['product_image_url'],
            'http://testserver/media/products/banners/order-test.jpg',
        )

    def test_payment_amount_updates_when_order_items_change(self):
        self.order.complete_payment(Payment.Method.CASH, Decimal('50000'), self.user)
        item = self.order.items.get()
        item.quantity = 3
        item.save()
        self.order.recalculate_total()

        self.order.payment.refresh_from_db()
        self.assertEqual(self.order.total_amount, Decimal('75000'))
        self.assertEqual(self.order.payment.amount, Decimal('75000'))

    def test_custom_payment_amount_is_preserved_when_order_total_changes(self):
        self.order.complete_payment(Payment.Method.CASH, Decimal('47000'), self.user)
        item = self.order.items.get()
        item.quantity = 3
        item.save()
        self.order.recalculate_total()

        payment = Payment.objects.get(order=self.order)
        self.assertEqual(self.order.total_amount, Decimal('75000'))
        self.assertEqual(payment.amount, Decimal('47000'))

    def test_payment_item_snapshot_is_not_changed_by_product_price(self):
        self.order.complete_payment(Payment.Method.CARD, Decimal('50000'), self.user)
        snapshot = PaymentItem.objects.get(payment=self.order.payment)

        self.product.price = Decimal('40000')
        self.product.save(update_fields=('price', 'updated_at'))
        snapshot.refresh_from_db()

        self.assertEqual(snapshot.product_name, 'Osh')
        self.assertEqual(snapshot.unit_price, Decimal('25000'))
        self.assertEqual(snapshot.quantity, 2)
        self.assertEqual(snapshot.total_price, Decimal('50000'))

    def test_closing_order_requires_payment_method(self):
        response = self.client.patch(
            reverse('api-order-detail', args=(self.order.pk,)),
            {'status': Order.Status.CLOSED},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('payment_method', response.data)

    def test_paid_order_items_can_be_updated_through_api(self):
        self.order.complete_payment(Payment.Method.CARD, Decimal('50000'), self.user)
        response = self.client.patch(
            reverse('api-order-detail', args=(self.order.pk,)),
            {
                'items': [{
                    'product': self.product.pk,
                    'quantity': 4,
                }],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.order.payment.refresh_from_db()
        self.assertEqual(self.order.total_amount, Decimal('100000'))
        self.assertEqual(self.order.payment.amount, Decimal('100000'))

    def test_payment_crud_update_and_delete_reopens_order(self):
        create_response = self.client.post(
            reverse('api-payment-list'),
            {
                'order': self.order.pk,
                'payment_type': Payment.Method.CASH,
                'amount': '46000.00',
            },
            format='json',
        )
        payment_id = create_response.data['id']
        update_response = self.client.patch(
            reverse('api-payment-detail', args=(payment_id,)),
            {'payment_type': Payment.Method.CLICK, 'amount': '45500.00'},
            format='json',
        )
        delete_response = self.client.delete(
            reverse('api-payment-detail', args=(payment_id,)),
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['method'], Payment.Method.CLICK)
        self.assertEqual(update_response.data['amount'], '45500.00')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.OPEN)
        self.assertFalse(Payment.objects.filter(pk=payment_id).exists())
