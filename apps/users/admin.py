from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('KitchenFlow', {'fields': ('name', 'role')}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ('KitchenFlow', {'fields': ('name', 'role')}),
    )
    list_display = ('username', 'name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'name')
