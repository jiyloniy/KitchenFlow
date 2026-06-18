from rest_framework.viewsets import ModelViewSet

from apps.orders.models import Order
from apps.orders.permissions import IsCeoOrReadOnly
from apps.orders.serializers import OrderSerializer


class OrderViewSet(ModelViewSet):
    """
    Zakaz CRUD API.
    GET hamma uchun ochiq, yozish faqat CEO uchun.
    """
    queryset = Order.objects.select_related('table').prefetch_related('items__product').order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = (IsCeoOrReadOnly,)

# Create your views here.
