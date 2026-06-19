from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.products.models import Category, Product
from apps.tables.models import Table, TableCategory
from apps.users.models import User


class CeoOrderPaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='panel-ceo',
            password='strong-password',
            name='Panel CEO',
            role=User.Role.CEO,
        )
        category = Category.objects.create(name='Taomlar', slug='taomlar')
        self.product = Product.objects.create(
            category=category,
            name='Manti',
            slug='manti',
            price=Decimal('12000'),
        )
        table_category = TableCategory.objects.create(name='Zal', slug='zal')
        self.table = Table.objects.create(
            category=table_category,
            name='Stol 1',
            number=1,
        )
        self.order = Order.objects.create(table=self.table)
        self.item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit_price=self.product.price,
        )
        self.order.recalculate_total()
        self.client.force_login(self.user)

    def test_closing_order_from_panel_creates_payment(self):
        response = self.client.post(reverse('order-update', args=(self.order.pk,)), {
            'order_type': Order.Type.DINE_IN,
            'status': Order.Status.CLOSED,
            'table': self.table.pk,
            'customer_name': 'Ali',
            'note': '',
            'payment_method': Payment.Method.CARD,
            'payment_amount': '35000.00',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '1',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-id': self.item.pk,
            'items-0-order': self.order.pk,
            'items-0-product': self.product.pk,
            'items-0-quantity': '3',
        })

        self.assertRedirects(response, reverse('order-list'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment.method, Payment.Method.CARD)
        self.assertEqual(self.order.payment.amount, Decimal('35000'))

    def test_order_list_and_detail_show_payment_information(self):
        self.order.complete_payment(Payment.Method.CLICK, Decimal('23000'), self.user)

        list_response = self.client.get(reverse('order-list'))
        detail_response = self.client.get(reverse('order-detail', args=(self.order.pk,)))

        self.assertContains(list_response, 'Click: 23000,00 so‘m')
        self.assertContains(detail_response, 'Zakaz cheki')
        self.assertContains(detail_response, '24000,00 so‘m')

    def test_payment_page_creates_and_updates_payment(self):
        payment_url = reverse('order-payment', args=(self.order.pk,))

        create_response = self.client.post(payment_url, {
            'payment_type': Payment.Method.CASH,
            'amount': '22000.00',
        })
        update_response = self.client.post(payment_url, {
            'payment_type': Payment.Method.CLICK,
            'amount': '21000.00',
        })

        self.assertRedirects(create_response, reverse('order-detail', args=(self.order.pk,)))
        self.assertRedirects(update_response, reverse('order-detail', args=(self.order.pk,)))
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 1)
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.method, Payment.Method.CLICK)
        self.assertEqual(payment.amount, Decimal('21000'))

    def test_order_detail_and_update_show_product_image(self):
        self.product.banner_image = 'products/banners/ceo-order-test.jpg'
        self.product.save(update_fields=('banner_image', 'updated_at'))

        detail_response = self.client.get(reverse('order-detail', args=(self.order.pk,)))
        update_response = self.client.get(reverse('order-update', args=(self.order.pk,)))

        image_url = '/media/products/banners/ceo-order-test.jpg'
        self.assertContains(detail_response, image_url)
        self.assertContains(update_response, image_url)
        self.assertContains(update_response, 'product-images')

    def test_cash_report_uses_payment_item_snapshots_and_product_filter(self):
        self.order.complete_payment(Payment.Method.CASH, Decimal('23000'), self.user)

        response = self.client.get(reverse('cash-report'), {
            'period': 'all',
            'product': self.product.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['received_total'], Decimal('23000'))
        self.assertEqual(response.context['item_sales_total'], Decimal('24000'))
        self.assertEqual(response.context['product_rows'][0]['quantity'], 2)
        self.assertEqual(response.context['daily_product_rows'][0]['quantity'], 2)
        self.assertContains(response, 'Kassa Hisobot')
        self.assertContains(response, 'cash-trend-chart')

    def test_product_report_builds_product_category_and_order_breakdowns(self):
        self.order.complete_payment(Payment.Method.CLICK, Decimal('23000'), self.user)

        response = self.client.get(reverse('product-report'), {
            'period': 'all',
            'category': 'Taomlar',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['revenue_total'], Decimal('24000'))
        self.assertEqual(response.context['quantity_total'], 2)
        self.assertEqual(response.context['category_rows'][0]['category_name'], 'Taomlar')
        self.assertEqual(response.context['method_rows'][0]['label'], 'Click')
        self.assertEqual(response.context['order_type_rows'][0]['label'], 'Oshxonani o‘zida')
        self.assertContains(response, 'product-trend-chart')
        self.assertContains(response, 'Mahsulotlar bo‘yicha to‘liq statistika')

    def test_cash_report_combines_operational_filters(self):
        self.order.complete_payment(Payment.Method.CASH, Decimal('23000'), self.user)
        filters = {
            'period': 'all',
            'category': 'Taomlar',
            'product': self.product.pk,
            'method': Payment.Method.CASH,
            'order_type': Order.Type.DINE_IN,
            'received_by': self.user.pk,
        }

        response = self.client.get(reverse('cash-report'), filters)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['received_total'], Decimal('23000'))
        self.assertEqual(response.context['item_sales_total'], Decimal('24000'))
        self.assertEqual(response.context['active_filters_count'], 5)
        self.assertContains(response, 'method=cash')

        filters['method'] = Payment.Method.CARD
        empty_response = self.client.get(reverse('cash-report'), filters)
        self.assertEqual(empty_response.context['received_total'], Decimal('0'))
        self.assertEqual(empty_response.context['payment_count'], 0)
