from io import BytesIO
from urllib.parse import urlencode

from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
import qrcode

from apps.ceo.decorators import ceo_required
from apps.ceo.table_forms import TableCategoryForm, TableForm
from apps.orders.models import Order
from apps.tables.models import Table, TableCategory


def get_table_qr_url(request, table):
    public_path = f"{reverse('public-table-qr')}?{urlencode({'table': table.pk})}"
    return request.build_absolute_uri(public_path)


def with_table_qr_data(request, table):
    table.qr_url = get_table_qr_url(request, table)
    table.qr_image_url = reverse('table-qr-image', kwargs={'pk': table.pk})
    return table


def render_qr_png(value):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=14,
        border=3,
    )
    qr.add_data(value)
    qr.make(fit=True)
    image = qr.make_image(fill_color='#132523', back_color='white').convert('RGB')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


@ceo_required
def table_category_list_view(request):
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'all')
    categories = TableCategory.objects.annotate(tables_count=Count('tables')).order_by('name')

    if query:
        categories = categories.filter(name__icontains=query)
    if status == 'active':
        categories = categories.filter(is_active=True)
    elif status == 'inactive':
        categories = categories.filter(is_active=False)

    return render(request, 'ceo/table_categories/list.html', {
        'active_page': 'table_categories',
        'categories': categories,
        'query': query,
        'status': status,
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def table_category_create_view(request):
    form = TableCategoryForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Stol kategoriyasi yaratildi.')
        return redirect('table-category-list')

    return render(request, 'ceo/table_categories/form.html', {
        'active_page': 'table_categories',
        'form': form,
        'title': 'Yangi stol kategoriyasi',
        'button_text': 'Saqlash',
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def table_category_update_view(request, pk):
    category = get_object_or_404(TableCategory, pk=pk)
    form = TableCategoryForm(request.POST or None, instance=category)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Stol kategoriyasi yangilandi.')
        return redirect('table-category-list')

    return render(request, 'ceo/table_categories/form.html', {
        'active_page': 'table_categories',
        'form': form,
        'category': category,
        'title': 'Stol kategoriyasini tahrirlash',
        'button_text': 'Yangilash',
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def table_category_delete_view(request, pk):
    category = get_object_or_404(TableCategory, pk=pk)

    if request.method == 'POST':
        if category.tables.exists():
            messages.error(request, 'Bu kategoriya ichida stol bor, avval stollarni boshqa kategoriyaga o‘tkazing.')
            return redirect('table-category-list')

        category.delete()
        messages.success(request, 'Stol kategoriyasi o‘chirildi.')
        return redirect('table-category-list')

    return render(request, 'ceo/table_categories/delete.html', {
        'active_page': 'table_categories',
        'category': category,
    })


@ceo_required
def table_list_view(request):
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'all')
    category_id = request.GET.get('category', 'all')
    tables = Table.objects.select_related('category').order_by('number')

    if query:
        tables = tables.filter(name__icontains=query)
    if category_id != 'all':
        tables = tables.filter(category_id=category_id)
    if status != 'all':
        tables = tables.filter(status=status)

    tables = [with_table_qr_data(request, table) for table in tables]

    return render(request, 'ceo/tables/list.html', {
        'active_page': 'tables',
        'tables': tables,
        'categories': TableCategory.objects.filter(is_active=True).order_by('name'),
        'query': query,
        'status': status,
        'category_id': category_id,
        'total_count': Table.objects.count(),
        'available_count': Table.objects.filter(status=Table.Status.AVAILABLE).count(),
        'busy_count': Table.objects.filter(status=Table.Status.BUSY).count(),
        'reserved_count': Table.objects.filter(status=Table.Status.RESERVED).count(),
    })


@ceo_required
def table_detail_view(request, pk):
    table = get_object_or_404(Table.objects.select_related('category'), pk=pk)
    with_table_qr_data(request, table)
    open_order = Order.objects.filter(
        table=table,
        order_type=Order.Type.DINE_IN,
        status=Order.Status.OPEN,
    ).order_by('-created_at').first()

    return render(request, 'ceo/tables/detail.html', {
        'active_page': 'tables',
        'table': table,
        'qr_url': table.qr_url,
        'open_order': open_order,
    })


@ceo_required
def table_qr_image_view(request, pk):
    table = get_object_or_404(Table, pk=pk)
    image = render_qr_png(get_table_qr_url(request, table))
    response = HttpResponse(image, content_type='image/png')
    if request.GET.get('download'):
        response['Content-Disposition'] = f'attachment; filename="table-{table.pk}-qr.png"'
    return response


def public_table_qr_view(request):
    table_id = request.GET.get('table', '').strip()
    table = None
    order = None

    if table_id.isdigit():
        table = Table.objects.filter(pk=int(table_id), is_active=True).first()

    if table:
        order = Order.objects.select_related('table').prefetch_related(
            'items__product__images'
        ).filter(
            table=table,
            order_type=Order.Type.DINE_IN,
            status=Order.Status.OPEN,
        ).order_by('-created_at').first()

    return render(request, 'ceo/qr/table_order.html', {
        'table_id': table_id,
        'table': table,
        'order': order,
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def table_create_view(request):
    form = TableForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Stol yaratildi.')
        return redirect('table-list')

    return render(request, 'ceo/tables/form.html', {
        'active_page': 'tables',
        'form': form,
        'title': 'Yangi stol',
        'button_text': 'Saqlash',
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def table_update_view(request, pk):
    table = get_object_or_404(Table, pk=pk)
    with_table_qr_data(request, table)
    form = TableForm(request.POST or None, instance=table)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Stol yangilandi.')
        return redirect('table-list')

    return render(request, 'ceo/tables/form.html', {
        'active_page': 'tables',
        'form': form,
        'table': table,
        'qr_url': table.qr_url,
        'title': 'Stolni tahrirlash',
        'button_text': 'Yangilash',
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def table_delete_view(request, pk):
    table = get_object_or_404(Table, pk=pk)

    if request.method == 'POST':
        table.delete()
        messages.success(request, 'Stol o‘chirildi.')
        return redirect('table-list')

    return render(request, 'ceo/tables/delete.html', {
        'active_page': 'tables',
        'table': table,
    })
