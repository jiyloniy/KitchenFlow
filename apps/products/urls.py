from rest_framework.routers import DefaultRouter

from apps.products.views import CategoryViewSet, ProductViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='api-product-category')
router.register('products', ProductViewSet, basename='api-product')

urlpatterns = router.urls
