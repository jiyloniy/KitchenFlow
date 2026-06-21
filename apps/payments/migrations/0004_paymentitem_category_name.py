from django.db import migrations, models


def backfill_category_names(apps, schema_editor):
    PaymentItem = apps.get_model('payments', 'PaymentItem')
    for item in PaymentItem.objects.select_related('product__category').iterator():
        if item.product_id and item.product.category_id:
            item.category_name = item.product.category.name
            item.save(update_fields=('category_name',))


class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0003_paymentitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentitem',
            name='category_name',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.RunPython(backfill_category_names, migrations.RunPython.noop),
    ]
