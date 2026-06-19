from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.ceo.decorators import ceo_required
from apps.payments.models import Payment, PaymentItem
from apps.products.models import Product


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

    payments = apply_payment_dates(
        Payment.objects.select_related('order', 'received_by').prefetch_related('items'),
        start,
        end,
    )
    report_items = apply_item_dates(PaymentItem.objects.select_related('payment'), start, end)
    selected_product = None
    if product_id.isdigit():
        selected_product = Product.objects.filter(pk=product_id).first()
        if selected_product:
            report_items = report_items.filter(product_id=selected_product.pk)

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

    if selected_product:
        trend_rows = list(
            report_items.annotate(day=TruncDate('payment__paid_at'))
            .values('day')
            .annotate(total=Sum('total_price'))
            .order_by('day')
        )
        trend_title = f'{selected_product.name} sotuv trendi'
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

    context = {
        'active_page': 'cash_report',
        'period': period,
        'date_from': start,
        'date_to': end,
        'products': Product.objects.filter(is_active=True).order_by('name'),
        'selected_product': selected_product,
        'received_total': received_total,
        'item_sales_total': item_sales_total,
        'payment_count': payment_count,
        'average_payment': average_payment,
        'method_rows': method_rows,
        'product_rows': product_rows,
        'recent_payments': payments.order_by('-paid_at')[:10],
        'trend_labels': [day.strftime('%d.%m') for day in days],
        'trend_values': [float(trend_map.get(day, 0)) for day in days],
        'trend_title': trend_title,
    }
    return render(request, 'ceo/reports/cash.html', context)
