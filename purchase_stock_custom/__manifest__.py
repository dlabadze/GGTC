{
    'name': 'Purchase to Stock Custom Sync',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Sync custom field from Purchase Order to Stock Picking',
    'description': """
        This module adds a custom field to Purchase Order and synchronization it to the Stock Picking.
    """,
    'author': 'Antigravity',
    'depends': ['purchase', 'stock', 'purchase_stock'],
    'data': [
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
