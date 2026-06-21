from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentPart
from apps.products.models import Product


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('order_type', 'status', 'table', 'customer_name', 'note')
        labels = {
            'order_type': 'Zakaz turi',
            'status': 'Holat',
            'table': 'Stol',
            'customer_name': 'Mijoz ismi',
            'note': 'Izoh',
        }
        widgets = {
            'note': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['table'].required = False

    def clean(self):
        cleaned_data = super().clean()
        order_type = cleaned_data.get('order_type')
        table = cleaned_data.get('table')
        status = cleaned_data.get('status')
        has_payment = bool(self.instance.pk and self.instance.is_paid)

        if order_type == Order.Type.DINE_IN and table is None:
            self.add_error('table', 'Oshxonani o‘zida zakaz uchun stol tanlang.')
        if order_type == Order.Type.SABOY and table is not None:
            self.add_error('table', 'Saboy zakaz uchun stol tanlanmaydi.')
        if status == Order.Status.CLOSED and not has_payment:
            self.add_error('status', 'Zakazni To‘lov qilish sahifasi orqali yoping.')
        if has_payment and status != Order.Status.CLOSED:
            self.add_error('status', 'To‘lov qilingan zakaz yopiq holatda qolishi kerak.')

        return cleaned_data


class PaymentForm(forms.Form):
    cash_amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01, required=False, label='Naqd')
    click_amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01, required=False, label='Click')
    terminal_amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01, required=False, label='Terminal')

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = order
        if order and order.is_paid:
            for part in order.payment.parts.all():
                self.fields[f'{part.method}_amount'].initial = part.amount
        elif order:
            self.fields['cash_amount'].initial = order.total_amount

    def clean(self):
        cleaned = super().clean()
        self.parts = [
            {'method': method, 'amount': cleaned.get(f'{method}_amount')}
            for method in PaymentPart.Method.values
            if cleaned.get(f'{method}_amount') is not None
        ]
        if not self.parts:
            raise forms.ValidationError('Kamida bitta to‘lov summasini kiriting.')
        return cleaned


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ('product', 'quantity')
        labels = {
            'product': 'Mahsulot',
            'quantity': 'Miqdor',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True).order_by('name')
        self.fields['product'].required = False
        self.fields['quantity'].required = False
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')

        if product and not quantity:
            self.add_error('quantity', 'Miqdor kiriting.')
        if quantity and not product:
            self.add_error('product', 'Mahsulot tanlang.')

        return cleaned_data

    def save(self, commit=True):
        item = super().save(commit=False)
        if item.product_id:
            item.unit_price = item.product.price
        if commit:
            item.save()
        return item


class BaseOrderItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        has_item = any(
            form.cleaned_data.get('product') and not form.cleaned_data.get('DELETE')
            for form in self.forms
        )
        if not has_item:
            raise forms.ValidationError('Zakazga kamida bitta mahsulot qo‘shing.')


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    formset=BaseOrderItemFormSet,
    extra=1,
    can_delete=True,
)
