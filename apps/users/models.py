from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        WAITER = 'waiter', 'Ofitsiant'
        CASHIER = 'cashier', 'Kassir'
        CEO = 'ceo', 'CEO'

    name = models.CharField(max_length=120)
    role = models.CharField(max_length=20, choices=Role.choices)

    def __str__(self):
        return f'{self.name} ({self.get_role_display()})'
