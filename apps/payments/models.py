from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction


class Payment(models.Model):
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='payment',
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=(MinValueValidator(Decimal('0.01')),),
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

    @property
    def method_summary(self):
        return ', '.join(
            f'{part.get_method_display()}: {part.amount}' for part in self.parts.all()
        )

    @transaction.atomic
    def replace_parts(self, parts):
        self.parts.all().delete()
        PaymentPart.objects.bulk_create([
            PaymentPart(payment=self, method=part['method'], amount=part['amount'])
            for part in parts
        ])
        self.amount = sum((part['amount'] for part in parts), 0)
        self.save(update_fields=('amount', 'updated_at'))

    @transaction.atomic
    def adjust_total(self, new_total):
        difference = new_total - self.amount
        parts = list(self.parts.order_by('id'))
        if not parts or difference == 0:
            return
        if difference > 0:
            parts[-1].amount += difference
            parts[-1].save(update_fields=('amount',))
        else:
            reduction = -difference
            for part in reversed(parts):
                if reduction <= 0:
                    break
                if part.amount <= reduction:
                    reduction -= part.amount
                    part.delete()
                else:
                    part.amount -= reduction
                    part.save(update_fields=('amount',))
                    reduction = 0
        self.amount = new_total
        self.save(update_fields=('amount', 'updated_at'))

    @transaction.atomic
    def sync_items_from_order(self):
        self.items.all().delete()
        PaymentItem.objects.bulk_create([
            PaymentItem(
                payment=self,
                product=item.product,
                product_name=item.product.name,
                category_name=item.product.category.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
            )
            for item in self.order.items.select_related('product__category')
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
    category_name = models.CharField(max_length=120, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ('id',)
        verbose_name = 'To‘lov mahsuloti'
        verbose_name_plural = 'To‘lov mahsulotlari'

    def __str__(self):
        return f'{self.product_name} x {self.quantity}'


class PaymentPart(models.Model):
    class Method(models.TextChoices):
        CASH = 'cash', 'Naqd'
        CLICK = 'click', 'Click'
        TERMINAL = 'terminal', 'Terminal'

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='parts')
    method = models.CharField(max_length=12, choices=Method.choices)
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=(MinValueValidator(Decimal('0.01')),),
    )

    class Meta:
        ordering = ('id',)
        constraints = (
            models.UniqueConstraint(fields=('payment', 'method'), name='unique_payment_method'),
        )

    def __str__(self):
        return f'{self.get_method_display()}: {self.amount} so‘m'
