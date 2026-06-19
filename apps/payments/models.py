from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


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
