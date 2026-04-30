{
    'name': 'Waybill Product Matching Custom',
    'version': '1.0',
    'summary': 'Custom overrides for waybill product matching and fetching logic',
    'description': 'This module extends waybill_management_custom to adjust product matching during waybill downloads and document creation.',
    'category': 'Inventory/Waybill',
    'depends': ['waybill_management_custom', 'product', 'stock', 'account', 'purchase', 'sale'],
    'data': ['views/account_move_line_view.xml', 'views/purchase_order_line.xml',],
    'installable': True,
    'application': False,
    'auto_install': False,
}
