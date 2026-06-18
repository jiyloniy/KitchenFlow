from django import forms

from apps.tables.models import Table, TableCategory


class TableCategoryForm(forms.ModelForm):
    class Meta:
        model = TableCategory
        fields = ('name', 'description', 'is_active')
        labels = {
            'name': 'Kategoriya nomi',
            'description': 'Izoh',
            'is_active': 'Faol',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['is_active'].widget.attrs['class'] = 'checkbox-input'


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ('category', 'name', 'number', 'capacity', 'status', 'is_active', 'note')
        labels = {
            'category': 'Kategoriya',
            'name': 'Stol nomi',
            'number': 'Stol raqami',
            'capacity': 'Sig‘im',
            'status': 'Holat',
            'is_active': 'Faol',
            'note': 'Izoh',
        }
        widgets = {
            'note': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['is_active'].widget.attrs['class'] = 'checkbox-input'
