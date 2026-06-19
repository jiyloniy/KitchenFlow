from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.ceo.decorators import ceo_required
from apps.orders.models import Order
from apps.payments.models import Payment, PaymentItem
from apps.products.models import Category, Product
from apps.users.models import User


def resolve_date_range(request):
    today = timezone.localdate()
    period = request.GET.get('period', '30d')
    date_from = parse_date(request.GET.get('date_from', ''))
    date_to = parse_date(request.GET.get('date_to', ''))

    if date_from or date_to:
        period = 'custom'
        start = date_from
        end = date_to or today
    elif period == 'today':
        start = end = today
    elif period == '7d':
        start, end = today - timedelta(days=6), today
    elif period == 'all':
        start, end = None, today
    else:
        period = '30d'
        start, end = today - timedelta(days=29), today

    if start and start > end:
        start, end = end, start
    return period, start, end


def apply_payment_dates(queryset, start, end):
    if start:
        queryset = queryset.filter(paid_at__date__gte=start)
    if end:
        queryset = queryset.filter(paid_at__date__lte=end)
    return queryset


def apply_item_dates(queryset, start, end):
    if start:
        queryset = queryset.filter(payment__paid_at__date__gte=start)
    if end:
        queryset = queryset.filter(payment__paid_at__date__lte=end)
    return queryset


@ceo_required
def cash_report_view(request):
    period, start, end = resolve_date_range(request)
    product_id = request.GET.get('product', '').strip()
    category_name = request.GET.get('category', '').strip()
    payment_method = request.GET.get('method', '').strip()
    order_type = request.GET.get('order_type', '').strip()
    receiver_id = request.GET.get('received_by', '').strip()

    payments = apply_payment_dates(
        Payment.objects.select_related('order', 'received_by').prefetch_related('items'),
        start,
        end,
    )
    if payment_method in Payment.Method.values:
        payments = payments.filter(method=payment_method)
    else:
        payment_method = ''
    if order_type in Order.Type.values:
        payments = payments.filter(order__order_type=order_type)
    else:
        order_type = ''

    selected_receiver = None
    if receiver_id.isdigit():
        selected_receiver = User.objects.filter(pk=receiver_id).first()
        if selected_receiver:
            payments = payments.filter(received_by=selected_receiver)

    report_items = PaymentItem.objects.select_related('payment').filter(payment__in=payments)
    selected_product = None
    if product_id.isdigit():
        selected_product = Product.objects.filter(pk=product_id).first()
        if selected_product:
            report_items = report_items.filter(product_id=selected_product.pk)

    selected_category = None
    if category_name:
        selected_category = Category.objects.filter(name=category_name).first()
        if selected_category:
            report_items = report_items.filter(category_name=selected_category.name)

    if selected_product or selected_category:
        payments = payments.filter(pk__in=report_items.values('payment_id')).distinct()

    payment_summary = payments.aggregate(total=Sum('amount'), count=Count('id'))
    received_total = payment_summary['total'] or Decimal('0')
    payment_count = payment_summary['count'] or 0
    average_payment = received_total / payment_count if payment_count else Decimal('0')
    item_sales_total = report_items.aggregate(total=Sum('total_price'))['total'] or Decimal('0')

    method_rows = []
    method_aggregates = {
        row['method']: row
        for row in payments.values('method').annotate(total=Sum('amount'), count=Count('id'))
    }
    for method, label in Payment.Method.choices:
        row = method_aggregates.get(method, {})
        amount = row.get('total') or Decimal('0')
        method_rows.append({
            'method': method,
            'label': label,
            'amount': amount,
            'count': row.get('count', 0),
            'share': round((amount / received_total * 100), 1) if received_total else 0,
        })

    product_rows = list(
        report_items.values('product_id', 'product_name')
        .annotate(
            quantity=Sum('quantity'),
            revenue=Sum('total_price'),
            payment_count=Count('payment_id', distinct=True),
        )
        .order_by('-revenue', 'product_name')
    )
    daily_product_rows = list(
        report_items.annotate(day=TruncDate('payment__paid_at'))
        .values('day', 'product_id', 'product_name')
        .annotate(
            quantity=Sum('quantity'),
            revenue=Sum('total_price'),
            payment_count=Count('payment_id', distinct=True),
        )
        .order_by('-day', '-revenue', 'product_name')
    )

    if selected_product or selected_category:
        trend_rows = list(
            report_items.annotate(day=TruncDate('payment__paid_at'))
            .values('day')
            .annotate(total=Sum('total_price'))
            .order_by('day')
        )
        selected_label = selected_product.name if selected_product else selected_category.name
        trend_title = f'{selected_label} sotuv trendi'
    else:
        trend_rows = list(
            payments.annotate(day=TruncDate('paid_at'))
            .values('day')
            .annotate(total=Sum('amount'))
            .order_by('day')
        )
        trend_title = 'Kassa tushumi trendi'
    trend_map = {row['day']: row['total'] for row in trend_rows}
    if start and end and (end - start).days <= 366:
        days = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
    else:
        days = list(trend_map.keys())

    persisted_filters = request.GET.copy()
    for key in ('period', 'date_from', 'date_to'):
        persisted_filters.pop(key, None)

    context = {
        'active_page': 'cash_report',
        'period': period,
        'date_from': start,
        'date_to': end,
        'products': Product.objects.filter(is_active=True).order_by('name'),
        'categories': Category.objects.filter(is_active=True).order_by('name'),
        'receivers': User.objects.filter(received_payments__isnull=False).distinct().order_by('name'),
        'payment_methods': Payment.Method.choices,
        'order_types': Order.Type.choices,
        'selected_product': selected_product,
        'selected_category': selected_category,
        'selected_receiver': selected_receiver,
        'selected_method': payment_method,
        'selected_order_type': order_type,
        'received_total': received_total,
        'item_sales_total': item_sales_total,
        'payment_count': payment_count,
        'average_payment': average_payment,
        'method_rows': method_rows,
        'product_rows': product_rows,
        'daily_product_rows': daily_product_rows,
        'recent_payments': payments.order_by('-paid_at')[:10],
        'trend_labels': [day.strftime('%d.%m') for day in days],
        'trend_values': [float(trend_map.get(day, 0)) for day in days],
        'trend_title': trend_title,
        'active_filters_count': sum(bool(value) for value in (
            selected_product,
            selected_category,
            selected_receiver,
            payment_method,
            order_type,
        )),
        'persisted_filters': persisted_filters.urlencode(),
    }
    return render(request, 'ceo/reports/cash.html', context)


@ceo_required
def product_report_view(request):
    period, start, end = resolve_date_range(request)
    product_id = request.GET.get('product', '').strip()
    category_name = request.GET.get('category', '').strip()

    report_items = apply_item_dates(
        PaymentItem.objects.select_related('payment__order', 'product'),
        start,
        end,
    )
    selected_product = None
    if product_id.isdigit():
        selected_product = Product.objects.filter(pk=product_id).first()
        if selected_product:
            report_items = report_items.filter(product_id=selected_product.pk)

    selected_category = None
    if category_name:
        selected_category = Category.objects.filter(name=category_name).first()
        if selected_category:
            report_items = report_items.filter(category_name=selected_category.name)

    totals = report_items.aggregate(
        revenue=Sum('total_price'),
        quantity=Sum('quantity'),
        payment_count=Count('payment_id', distinct=True),
        product_count=Count('product_name', distinct=True),
    )
    revenue_total = totals['revenue'] or Decimal('0')
    quantity_total = totals['quantity'] or 0
    average_unit_price = revenue_total / quantity_total if quantity_total else Decimal('0')

    product_rows = list(
        report_items.values('product_id', 'product_name', 'category_name')
        .annotate(
            quantity=Sum('quantity'),
            revenue=Sum('total_price'),
            payment_count=Count('payment_id', distinct=True),
        )
        .order_by('-revenue', 'product_name')
    )
    for row in product_rows:
        row['average_price'] = row['revenue'] / row['quantity'] if row['quantity'] else Decimal('0')

    category_rows = list(
        report_items.values('category_name')
        .annotate(
            quantity=Sum('quantity'),
            revenue=Sum('total_price'),
            product_count=Count('product_name', distinct=True),
        )
        .order_by('-revenue', 'category_name')
    )
    for row in category_rows:
        row['share'] = round(row['revenue'] / revenue_total * 100, 1) if revenue_total else 0

    method_labels = dict(Payment.Method.choices)
    method_rows = list(
        report_items.values('payment__method')
        .annotate(quantity=Sum('quantity'), revenue=Sum('total_price'))
        .order_by('-revenue')
    )
    for row in method_rows:
        row['label'] = method_labels.get(row['payment__method'], row['payment__method'])
        row['share'] = round(row['revenue'] / revenue_total * 100, 1) if revenue_total else 0

    order_type_labels = dict(Order.Type.choices)
    order_type_rows = list(
        report_items.values('payment__order__order_type')
        .annotate(quantity=Sum('quantity'), revenue=Sum('total_price'))
        .order_by('-revenue')
    )
    for row in order_type_rows:
        value = row['payment__order__order_type']
        row['label'] = order_type_labels.get(value, value)
        row['share'] = round(row['revenue'] / revenue_total * 100, 1) if revenue_total else 0

    trend_rows = list(
        report_items.annotate(day=TruncDate('payment__paid_at'))
        .values('day')
        .annotate(total=Sum('total_price'), quantity=Sum('quantity'))
        .order_by('day')
    )
    trend_map = {row['day']: row for row in trend_rows}
    if start and end and (end - start).days <= 366:
        days = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
    else:
        days = list(trend_map.keys())

    context = {
        'active_page': 'product_report',
        'period': period,
        'date_from': start,
        'date_to': end,
        'products': Product.objects.filter(is_active=True).order_by('name'),
        'categories': Category.objects.filter(is_active=True).order_by('name'),
        'selected_product': selected_product,
        'selected_category': selected_category,
        'revenue_total': revenue_total,
        'quantity_total': quantity_total,
        'payment_count': totals['payment_count'] or 0,
        'product_count': totals['product_count'] or 0,
        'average_unit_price': average_unit_price,
        'product_rows': product_rows,
        'category_rows': category_rows,
        'method_rows': method_rows,
        'order_type_rows': order_type_rows,
        'top_product': product_rows[0] if product_rows else None,
        'trend_labels': [day.strftime('%d.%m') for day in days],
        'trend_revenue': [float(trend_map.get(day, {}).get('total', 0)) for day in days],
        'trend_quantity': [trend_map.get(day, {}).get('quantity', 0) for day in days],
    }
    return render(request, 'ceo/reports/products.html', context)
