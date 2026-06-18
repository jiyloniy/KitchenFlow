from django.contrib import admin

from apps.orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('code', 'order_type', 'status', 'table', 'total_amount', 'created_at')
    list_filter = ('order_type', 'status', 'created_at')
    search_fields = ('code', 'id', 'customer_name', 'table__name')
    inlines = (OrderItemInline,)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price')
    list_filter = ('product__category',)
    search_fields = ('product__name',)

# Register your models here.
