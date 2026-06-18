from django.db.models import Count
from rest_framework.viewsets import ModelViewSet

from apps.products.models import Category, Product
from apps.products.permissions import IsCeoOrReadOnly
from apps.products.serializers import CategorySerializer, ProductSerializer


class CategoryViewSet(ModelViewSet):
    """
    Product category CRUD.
    """
    queryset = Category.objects.annotate(products_count=Count('products')).order_by('name')
    serializer_class = CategorySerializer
    permission_classes = (IsCeoOrReadOnly,)


class ProductViewSet(ModelViewSet):
    """
    Sellable product CRUD.
    """
    queryset = Product.objects.select_related('category').all().order_by('category__name', 'name')
    serializer_class = ProductSerializer
    permission_classes = (IsCeoOrReadOnly,)
