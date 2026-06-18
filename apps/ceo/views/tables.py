from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.ceo.decorators import ceo_required
from apps.ceo.table_forms import TableCategoryForm, TableForm
from apps.tables.models import Table, TableCategory


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
    form = TableForm(request.POST or None, instance=table)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Stol yangilandi.')
        return redirect('table-list')

    return render(request, 'ceo/tables/form.html', {
        'active_page': 'tables',
        'form': form,
        'table': table,
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
