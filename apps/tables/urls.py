from rest_framework.routers import DefaultRouter

from apps.tables.views import TableCategoryViewSet, TableViewSet

router = DefaultRouter()
router.register('categories', TableCategoryViewSet, basename='api-table-category')
router.register('tables', TableViewSet, basename='api-table')

urlpatterns = router.urls
