from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.ceo.decorators import ceo_required
from apps.ceo.forms import CeoLoginForm, EmployeeForm
from apps.products.models import Category, Product
from apps.tables.models import Table, TableCategory
from apps.orders.models import Order
from apps.users.models import User


@require_http_methods(['GET', 'POST'])
def panel_login_view(request):
    if request.user.is_authenticated and request.user.role == User.Role.CEO:
        return redirect('ceo-dashboard')

    form = CeoLoginForm(request=request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('ceo-dashboard')

    return render(request, 'ceo/auth/login.html', {'form': form})


@require_POST
def panel_logout_view(request):
    logout(request)
    return redirect('panel-login')


@ceo_required
def dashboard_view(request):
    context = {
        'active_page': 'dashboard',
        'total_employees': User.objects.count(),
        'waiters_count': User.objects.filter(role=User.Role.WAITER).count(),
        'cashiers_count': User.objects.filter(role=User.Role.CASHIER).count(),
        'ceos_count': User.objects.filter(role=User.Role.CEO).count(),
        'categories_count': Category.objects.count(),
        'products_count': Product.objects.count(),
        'tables_count': Table.objects.count(),
        'table_categories_count': TableCategory.objects.count(),
        'orders_count': Order.objects.count(),
        'recent_employees': User.objects.order_by('-date_joined')[:5],
    }
    return render(request, 'ceo/dashboard/index.html', context)


@ceo_required
def employee_list_view(request):
    employees = User.objects.order_by('role', 'name')
    return render(request, 'ceo/employees/list.html', {
        'active_page': 'employees',
        'employees': employees,
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def employee_create_view(request):
    form = EmployeeForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Hodim yaratildi.')
        return redirect('employee-list')

    return render(request, 'ceo/employees/form.html', {
        'form': form,
        'active_page': 'employees',
        'title': 'Yangi hodim',
        'button_text': 'Saqlash',
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def employee_update_view(request, pk):
    employee = get_object_or_404(User, pk=pk)
    form = EmployeeForm(request.POST or None, instance=employee)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Hodim yangilandi.')
        return redirect('employee-list')

    return render(request, 'ceo/employees/form.html', {
        'form': form,
        'active_page': 'employees',
        'employee': employee,
        'title': 'Hodimni tahrirlash',
        'button_text': 'Yangilash',
    })


@ceo_required
@require_http_methods(['GET', 'POST'])
def employee_delete_view(request, pk):
    employee = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        if employee == request.user:
            messages.error(request, 'O‘zingizni o‘chira olmaysiz.')
            return redirect('employee-list')

        employee.delete()
        messages.success(request, 'Hodim o‘chirildi.')
        return redirect('employee-list')

    return render(request, 'ceo/employees/delete.html', {
        'active_page': 'employees',
        'employee': employee,
    })
