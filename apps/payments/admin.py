from django.contrib import admin

from apps.payments.models import Payment, PaymentItem, PaymentPart


class PaymentPartInline(admin.TabularInline):
    model = PaymentPart
    extra = 0


class PaymentItemInline(admin.TabularInline):
    model = PaymentItem
    extra = 0
    can_delete = False
    readonly_fields = (
        'product',
        'product_name',
        'category_name',
        'quantity',
        'unit_price',
        'total_price',
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'received_by', 'paid_at')
    list_filter = ('parts__method', 'paid_at')
    search_fields = ('order__code', 'order__customer_name')
    readonly_fields = ('paid_at', 'updated_at')
    inlines = (PaymentPartInline, PaymentItemInline)
