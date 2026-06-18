from django.db.models import Count
from rest_framework.viewsets import ModelViewSet

from apps.tables.models import Table, TableCategory
from apps.tables.permissions import IsCeoOrReadOnly
from apps.tables.serializers import TableCategorySerializer, TableSerializer


class TableCategoryViewSet(ModelViewSet):
    """
    Stol kategoriyalari CRUD API.
    GET hamma uchun ochiq, yozish faqat CEO uchun.
    """
    queryset = TableCategory.objects.annotate(tables_count=Count('tables')).order_by('name')
    serializer_class = TableCategorySerializer
    permission_classes = (IsCeoOrReadOnly,)


class TableViewSet(ModelViewSet):
    """
    Stollar CRUD API.
    GET hamma uchun ochiq, yozish faqat CEO uchun.
    """
    queryset = Table.objects.select_related('category').order_by('number')
    serializer_class = TableSerializer
    permission_classes = (IsCeoOrReadOnly,)

# Create your views here.
