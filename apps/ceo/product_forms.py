from django import forms

from apps.products.models import Category, Product


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [super(MultipleImageField, self).clean(item, initial) for item in data]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'is_active')
        labels = {
            'name': 'Kategoriya nomi',
            'is_active': 'Faol',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['is_active'].widget.attrs['class'] = 'checkbox-input'


class ProductForm(forms.ModelForm):
    gallery_images = MultipleImageField(
        label='Qo‘shimcha rasmlar',
        required=False,
        help_text='Bir nechta rasm tanlash mumkin.',
    )

    class Meta:
        model = Product
        fields = ('category', 'name', 'description', 'price', 'banner_image', 'is_active')
        labels = {
            'category': 'Kategoriya',
            'name': 'Mahsulot nomi',
            'description': 'Izoh',
            'price': 'Narx',
            'banner_image': 'Asosiy banner rasm',
            'is_active': 'Sotuvda bor',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['is_active'].widget.attrs['class'] = 'checkbox-input'
        self.fields['gallery_images'].widget.attrs['multiple'] = True
