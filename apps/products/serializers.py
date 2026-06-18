from rest_framework import serializers

from apps.products.models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = (
            'id',
            'name',
            'slug',
            'is_active',
            'products_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('slug', 'created_at', 'updated_at')


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'image_url', 'alt_text', 'sort_order')

    def get_image_url(self, obj):
        request = self.context.get('request')
        if not obj.image:
            return ''
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    banner_image_url = serializers.SerializerMethodField()
    gallery_images = ProductImageSerializer(source='images', many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            'id',
            'category',
            'category_name',
            'name',
            'slug',
            'description',
            'price',
            'banner_image',
            'banner_image_url',
            'gallery_images',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('slug', 'created_at', 'updated_at')

    def get_banner_image_url(self, obj):
        request = self.context.get('request')
        if not obj.banner_image:
            return ''
        if request:
            return request.build_absolute_uri(obj.banner_image.url)
        return obj.banner_image.url
