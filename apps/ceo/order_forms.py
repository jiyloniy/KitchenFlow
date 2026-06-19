from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.products.models import Product


class OrderForm(forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=(('', 'To‘lov turini tanlang'), *Payment.Method.choices),
        required=False,
        label='To‘lov turi',
    )
    payment_amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0.01,
        required=False,
        label='To‘lanadigan summa',
    )

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
        if self.instance.pk and self.instance.is_paid:
            self.fields['payment_method'].initial = self.instance.payment.method
            self.fields['payment_amount'].initial = self.instance.payment.amount

    def clean(self):
        cleaned_data = super().clean()
        order_type = cleaned_data.get('order_type')
        table = cleaned_data.get('table')
        status = cleaned_data.get('status')
        payment_method = cleaned_data.get('payment_method')
        payment_amount = cleaned_data.get('payment_amount')
        has_payment = bool(self.instance.pk and self.instance.is_paid)

        if order_type == Order.Type.DINE_IN and table is None:
            self.add_error('table', 'Oshxonani o‘zida zakaz uchun stol tanlang.')
        if order_type == Order.Type.SABOY and table is not None:
            self.add_error('table', 'Saboy zakaz uchun stol tanlanmaydi.')
        if status == Order.Status.CLOSED and not payment_method and not has_payment:
            self.add_error('payment_method', 'Zakazni yopish uchun to‘lov turini tanlang.')
        if status == Order.Status.CLOSED and payment_amount is None:
            self.add_error('payment_amount', 'To‘lanadigan summani kiriting.')
        if has_payment and status != Order.Status.CLOSED:
            self.add_error('status', 'To‘lov qilingan zakaz yopiq holatda qolishi kerak.')

        return cleaned_data


class PaymentForm(forms.Form):
    payment_type = forms.ChoiceField(
        choices=Payment.Method.choices,
        label='To‘lov turi',
        widget=forms.RadioSelect,
    )
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0.01,
        label='To‘lanadigan summa',
    )

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = order
        if order and order.is_paid:
            self.fields['payment_type'].initial = order.payment.method
            self.fields['amount'].initial = order.payment.amount
        elif order:
            self.fields['amount'].initial = order.total_amount


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
