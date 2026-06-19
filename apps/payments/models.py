from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = 'cash', 'Naqd'
        CARD = 'card', 'Karta'
        CLICK = 'click', 'Click'

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='payment',
    )
    method = models.CharField(max_length=12, choices=Method.choices)
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=(MinValueValidator(0.01),),
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='received_payments',
        null=True,
        blank=True,
    )
    paid_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-paid_at',)
        verbose_name = 'To‘lov'
        verbose_name_plural = 'To‘lovlar'

    def __str__(self):
        return f'{self.order.display_code} - {self.amount} so‘m'

    @property
    def difference_amount(self):
        return self.amount - self.order.total_amount

    @transaction.atomic
    def sync_items_from_order(self):
        self.items.all().delete()
        PaymentItem.objects.bulk_create([
            PaymentItem(
                payment=self,
                product=item.product,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
            )
            for item in self.order.items.select_related('product')
        ])


class PaymentItem(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        related_name='payment_items',
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=140)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ('id',)
        verbose_name = 'To‘lov mahsuloti'
        verbose_name_plural = 'To‘lov mahsulotlari'

    def __str__(self):
        return f'{self.product_name} x {self.quantity}'
