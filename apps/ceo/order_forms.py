from django import forms
from django.forms import inlineformset_factory

from apps.orders.models import Order, OrderItem
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

        if order_type == Order.Type.DINE_IN and table is None:
            self.add_error('table', 'Oshxonani o‘zida zakaz uchun stol tanlang.')
        if order_type == Order.Type.SABOY and table is not None:
            self.add_error('table', 'Saboy zakaz uchun stol tanlanmaydi.')

        return cleaned_data


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


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True,
)
