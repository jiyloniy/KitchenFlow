from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class Order(models.Model):
    class Type(models.TextChoices):
        SABOY = 'saboy', 'Saboy'
        DINE_IN = 'dine_in', 'Oshxonani o‘zida'

    class Status(models.TextChoices):
        OPEN = 'open', 'Ochiq'
        CLOSED = 'closed', 'Yopiq'
        CANCELLED = 'cancelled', 'Bekor qilindi'

    order_type = models.CharField(max_length=20, choices=Type.choices, default=Type.DINE_IN)
    code = models.CharField(max_length=16, unique=True, null=True, blank=True, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    table = models.ForeignKey('tables.Table', on_delete=models.PROTECT, related_name='orders', null=True, blank=True)
    customer_name = models.CharField(max_length=120, blank=True)
    note = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Zakaz'
        verbose_name_plural = 'Zakazlar'

    def clean(self):
        if self.order_type == self.Type.DINE_IN and self.table is None:
            raise ValidationError({'table': 'Oshxonani o‘zida zakaz uchun stol tanlash majburiy.'})
        if self.order_type == self.Type.SABOY and self.table is not None:
            raise ValidationError({'table': 'Saboy zakaz uchun stol tanlanmaydi.'})

    def recalculate_total(self):
        previous_total = self.total_amount
        try:
            payment = self.payment
        except self._meta.apps.get_model('payments', 'Payment').DoesNotExist:
            payment = None

        total = self.items.aggregate(total=models.Sum(models.F('quantity') * models.F('unit_price')))['total']
        self.total_amount = total or Decimal('0')
        self.save(update_fields=['total_amount', 'updated_at'])

        if payment and payment.amount == previous_total and payment.amount != self.total_amount:
            payment.amount = self.total_amount
            payment.save(update_fields=['amount', 'updated_at'])
        if payment:
            payment.sync_items_from_order()

    def complete_payment(self, method, amount, received_by=None):
        if not self.items.exists():
            raise ValidationError('Mahsulotsiz zakazni yopib bo‘lmaydi.')

        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValidationError('To‘lov summasi 0 dan katta bo‘lishi kerak.')

        self.recalculate_total()
        Payment = self._meta.apps.get_model('payments', 'Payment')
        payment, _ = Payment.objects.update_or_create(
            order=self,
            defaults={
                'method': method,
                'amount': amount,
                'received_by': received_by,
            },
        )
        self.payment = payment
        payment.sync_items_from_order()
        if self.status != self.Status.CLOSED:
            self.status = self.Status.CLOSED
            self.save(update_fields=['status', 'updated_at'])
        return payment

    @property
    def is_paid(self):
        return hasattr(self, 'payment')

    @property
    def code_prefix(self):
        return 'S' if self.order_type == self.Type.SABOY else 'O'

    @property
    def display_code(self):
        return self.code or f'{self.code_prefix}-{self.pk or 0:05d}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code and self.pk:
            self.code = f'{self.code_prefix}-{self.pk:05d}'
            super().save(update_fields=['code'])

    def __str__(self):
        return f'Zakaz {self.display_code} - {self.get_status_display()}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Zakaz mahsuloti'
        verbose_name_plural = 'Zakaz mahsulotlari'

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

# Create your models here.
