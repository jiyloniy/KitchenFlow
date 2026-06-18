from django.contrib import admin

from apps.tables.models import Table, TableCategory


@admin.register(TableCategory)
class TableCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('name', 'number', 'category', 'capacity', 'status', 'is_active')
    list_filter = ('category', 'status', 'is_active')
    search_fields = ('name', 'number')

# Register your models here.
