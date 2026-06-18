from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

from apps.users.models import User


class CeoLoginForm(forms.Form):
    username = forms.CharField(label='Foydalanuvchi nomi', max_length=150)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if not username or not password:
            return cleaned_data

        self.user = authenticate(
            self.request,
            username=username,
            password=password,
        )

        if self.user is None:
            raise ValidationError('Foydalanuvchi nomi yoki password xato.')

        if not self.user.is_active:
            raise ValidationError('Bu foydalanuvchi faol emas.')

        if self.user.role != User.Role.CEO:
            raise ValidationError('Bu panelga faqat CEO kira oladi.')

        return cleaned_data

    def get_user(self):
        return self.user


class EmployeeForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        required=False,
        widget=forms.PasswordInput,
        help_text='Yangi hodim uchun majburiy. Tahrirlashda bo‘sh qoldirilsa o‘zgarmaydi.',
    )

    class Meta:
        model = User
        fields = ('name', 'username', 'role', 'is_active', 'password')
        labels = {
            'name': 'Ism',
            'username': 'Foydalanuvchi nomi',
            'role': 'Lavozim',
            'is_active': 'Faol',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['is_active'].widget.attrs['class'] = 'checkbox-input'

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if self.instance.pk is None and not password:
            raise ValidationError('Yangi hodim uchun password kiriting.')
        return password

    def save(self, commit=True):
        password = self.cleaned_data.pop('password', None)
        user = super().save(commit=False)

        if password:
            user.set_password(password)

        if commit:
            user.save()

        return user
