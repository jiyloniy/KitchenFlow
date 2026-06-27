from apps.orders.models import Order
from apps.tables.models import Table


def refresh_table_status(table_id):
    if not table_id:
        return

    try:
        table = Table.objects.get(pk=table_id)
    except Table.DoesNotExist:
        return

    has_open_order = Order.objects.filter(
        table_id=table_id,
        order_type=Order.Type.DINE_IN,
        status=Order.Status.OPEN,
    ).exists()

    if has_open_order:
        if table.status != Table.Status.DISABLED and table.status != Table.Status.BUSY:
            table.status = Table.Status.BUSY
            table.save(update_fields=('status', 'updated_at'))
        return

    if table.status == Table.Status.BUSY:
        table.status = Table.Status.AVAILABLE
        table.save(update_fields=('status', 'updated_at'))


def sync_order_table_status(order, previous_table_id=None):
    table_ids = {order.table_id, previous_table_id}
    for table_id in table_ids:
        refresh_table_status(table_id)
