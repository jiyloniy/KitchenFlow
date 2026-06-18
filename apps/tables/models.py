from django.db import models
from django.utils.text import slugify


class TableCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        verbose_name = 'Stol kategoriyasi'
        verbose_name_plural = 'Stol kategoriyalari'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Table(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Bo‘sh'
        BUSY = 'busy', 'Band'
        RESERVED = 'reserved', 'Bron'
        DISABLED = 'disabled', 'O‘chiq'

    category = models.ForeignKey(TableCategory, on_delete=models.PROTECT, related_name='tables')
    name = models.CharField(max_length=80)
    number = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveSmallIntegerField(default=4)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    is_active = models.BooleanField(default=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('number',)
        verbose_name = 'Stol'
        verbose_name_plural = 'Stollar'

    def __str__(self):
        return f'{self.name} ({self.number})'

# Create your models here.
