from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.ceo.decorators import ceo_required
from apps.ceo.order_forms import OrderForm, OrderItemFormSet, PaymentForm
from apps.orders.models import Order, OrderItem
from apps.products.models import Product


def get_product_prices():
    return {
        str(product_id): str(price)
        for product_id, price in Product.objects.filter(is_active=True).values_list('id', 'price')
    }


def get_product_images():
    products = Product.objects.filter(is_active=True).prefetch_related('images')
    return {
        str(product.pk): product.display_image.url if product.display_image else ''
        for product in products
    }


def save_order_items(order, formset, replace=False):
    if replace:
        order.items.all().delete()

    for item_form in formset:
        cleaned_data = getattr(item_form, 'cleaned_data', {})
        if not cleaned_data or cleaned_data.get('DELETE'):
            continue

        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        if not product or not quantity:
            continue

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=product.price,
        )


@ceo_required
def order_list_view(request):
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'all')
    order_type = request.GET.get('type', 'all')
    orders = Order.objects.select_related('table', 'payment').prefetch_related(
        'items__product__images', 'payment__parts'
    ).order_by('-created_at')

    if query:
        orders = orders.filter(customer_name__icontains=query)
    if status != 'all':
        orders = orders.filter(status=status)
    if order_type != 'all':
        orders = orders.filter(order_type=order_type)

    return render(request, 'ceo/orders/list.html', {
        'active_page': 'orders',
        'orders': orders,
        'query': query,
        'status': status,
        'order_type': order_type,
        'total_count': Order.objects.count(),
        'open_count': Order.objects.filter(status=Order.Status.OPEN).count(),
        'closed_count': Order.objects.filter(status=Order.Status.CLOSED).count(),
        'cancelled_count': Order.objects.filter(status=Order.Status.CANCELLED).count(),
        'paid_total': Order.objects.filter(payment__isnull=False).aggregate(
            total=Sum('payment__amount')
        )['total'] or 0,
    })


@ceo_required
def order_detail_view(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('table', 'payment__received_by').prefetch_related(
            'items__product__images', 'payment__parts'
        ),
        pk=pk,
    )
    return render(request, 'ceo/orders/detail.html', {
        'active_page': 'orders',
        'order': order,
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def order_payment_view(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('table', 'payment__received_by').prefetch_related(
            'items__product__images', 'payment__parts'
        ),
        pk=pk,
    )
    form = PaymentForm(request.POST or None, order=order)

    if request.method == 'POST' and form.is_valid():
        was_paid = order.is_paid
        with transaction.atomic():
            order.complete_payment(
                form.parts, request.user,
            )
        messages.success(
            request,
            'To‘lov yangilandi.' if was_paid else 'To‘lov qabul qilindi.',
        )
        return redirect('order-detail', pk=order.pk)

    return render(request, 'ceo/orders/payment.html', {
        'active_page': 'orders',
        'order': order,
        'form': form,
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def order_create_view(request):
    form = OrderForm(request.POST or None)
    formset = OrderItemFormSet(request.POST or None)

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            order = form.save()
            formset.instance = order
            save_order_items(order, formset)
            order.recalculate_total()
        messages.success(request, 'Zakaz yaratildi.')
        return redirect('order-list')

    return render(request, 'ceo/orders/form.html', {
        'active_page': 'orders',
        'form': form,
        'formset': formset,
        'title': 'Yangi zakaz',
        'button_text': 'Saqlash',
        'product_prices': get_product_prices(),
        'product_images': get_product_images(),
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def order_update_view(request, pk):
    order = get_object_or_404(Order, pk=pk)
    form = OrderForm(request.POST or None, instance=order)
    formset = OrderItemFormSet(request.POST or None, instance=order)

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            order = form.save()
            save_order_items(order, formset, replace=True)
            order.recalculate_total()
        messages.success(request, 'Zakaz yangilandi.')
        return redirect('order-list')

    return render(request, 'ceo/orders/form.html', {
        'active_page': 'orders',
        'form': form,
        'formset': formset,
        'order': order,
        'title': 'Zakazni tahrirlash',
        'button_text': 'Yangilash',
        'product_prices': get_product_prices(),
        'product_images': get_product_images(),
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def order_delete_view(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        order.delete()
        messages.success(request, 'Zakaz o‘chirildi.')
        return redirect('order-list')

    return render(request, 'ceo/orders/delete.html', {
        'active_page': 'orders',
        'order': order,
    })
