from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.ceo.decorators import ceo_required
from apps.ceo.product_forms import CategoryForm, ProductForm
from apps.products.models import Category, Product, ProductImage


@ceo_required
def category_list_view(request):
    categories = Category.objects.annotate(products_count=Count('products')).order_by('name')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'all')

    if query:
        categories = categories.filter(name__icontains=query)
    if status == 'active':
        categories = categories.filter(is_active=True)
    elif status == 'inactive':
        categories = categories.filter(is_active=False)

    return render(request, 'ceo/categories/list.html', {
        'active_page': 'categories',
        'categories': categories,
        'query': query,
        'status': status,
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def category_create_view(request):
    form = CategoryForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Kategoriya yaratildi.')
        return redirect('category-list')

    return render(request, 'ceo/categories/form.html', {
        'active_page': 'categories',
        'form': form,
        'title': 'Yangi kategoriya',
        'button_text': 'Saqlash',
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def category_update_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Kategoriya yangilandi.')
        return redirect('category-list')

    return render(request, 'ceo/categories/form.html', {
        'active_page': 'categories',
        'form': form,
        'category': category,
        'title': 'Kategoriyani tahrirlash',
        'button_text': 'Yangilash',
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def category_delete_view(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        if category.products.exists():
            messages.error(request, 'Bu kategoriya ichida mahsulot bor, avval mahsulotlarni boshqa kategoriyaga o‘tkazing.')
            return redirect('category-list')

        category.delete()
        messages.success(request, 'Kategoriya o‘chirildi.')
        return redirect('category-list')

    return render(request, 'ceo/categories/delete.html', {
        'active_page': 'categories',
        'category': category,
    })


@ceo_required
def product_list_view(request):
    status = request.GET.get('status', 'all')
    category_id = request.GET.get('category', 'all')
    query = request.GET.get('q', '').strip()
    products = Product.objects.select_related('category').order_by('category__name', 'name')

    if query:
        products = products.filter(name__icontains=query)
    if category_id != 'all':
        products = products.filter(category_id=category_id)
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)

    return render(request, 'ceo/products/list.html', {
        'active_page': 'products',
        'products': products,
        'categories': Category.objects.filter(is_active=True).order_by('name'),
        'category_id': category_id,
        'query': query,
        'status': status,
        'total_count': Product.objects.count(),
        'active_count': Product.objects.filter(is_active=True).count(),
        'inactive_count': Product.objects.filter(is_active=False).count(),
        'categories_count': Category.objects.count(),
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def product_create_view(request):
    form = ProductForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        product = form.save()
        for index, image in enumerate(request.FILES.getlist('gallery_images')):
            ProductImage.objects.create(product=product, image=image, sort_order=index)
        messages.success(request, 'Mahsulot yaratildi.')
        return redirect('product-list')

    return render(request, 'ceo/products/form.html', {
        'active_page': 'products',
        'form': form,
        'title': 'Yangi mahsulot',
        'button_text': 'Saqlash',
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def product_update_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)

    if request.method == 'POST' and form.is_valid():
        product = form.save()
        start_order = product.images.count()
        for index, image in enumerate(request.FILES.getlist('gallery_images'), start=start_order):
            ProductImage.objects.create(product=product, image=image, sort_order=index)
        messages.success(request, 'Mahsulot yangilandi.')
        return redirect('product-list')

    return render(request, 'ceo/products/form.html', {
        'active_page': 'products',
        'form': form,
        'product': product,
        'title': 'Mahsulotni tahrirlash',
        'button_text': 'Yangilash',
    })


@ceo_required
@require_POST
def product_toggle_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save(update_fields=['is_active', 'updated_at'])

    if product.is_active:
        messages.success(request, f'{product.name} sotuvga chiqarildi.')
    else:
        messages.success(request, f'{product.name} sotuvdan olindi.')

    next_url = request.POST.get('next') or 'product-list'
    return redirect(next_url)


@ceo_required
@require_http_methods(['POST'])
def product_image_delete_view(request, pk):
    image = get_object_or_404(ProductImage, pk=pk)
    product_pk = image.product_id
    image.delete()
    messages.success(request, 'Mahsulot rasmi o‘chirildi.')
    return redirect('product-update', pk=product_pk)


@ceo_required
@require_http_methods(['GET', 'POST'])
def product_delete_view(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Mahsulot o‘chirildi.')
        return redirect('product-list')

    return render(request, 'ceo/products/delete.html', {
        'active_page': 'products',
        'product': product,
    })
