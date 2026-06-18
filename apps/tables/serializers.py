from rest_framework import serializers

from apps.tables.models import Table, TableCategory


class TableCategorySerializer(serializers.ModelSerializer):
    tables_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TableCategory
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'is_active',
            'tables_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('slug', 'created_at', 'updated_at')


class TableSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Table
        fields = (
            'id',
            'category',
            'category_name',
            'name',
            'number',
            'capacity',
            'status',
            'status_display',
            'is_active',
            'note',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')
