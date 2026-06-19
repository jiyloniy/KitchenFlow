from django.contrib import admin

from apps.payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'method', 'amount', 'received_by', 'paid_at')
    list_filter = ('method', 'paid_at')
    search_fields = ('order__code', 'order__customer_name')
    readonly_fields = ('paid_at', 'updated_at')
