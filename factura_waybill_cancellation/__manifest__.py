{
    'name': 'Factura and Waybill Cancellation',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Cancel/Delete factura and waybill from RS.GE and combined invoice model',
    'license': 'LGPL-3',
    'author': 'Your Name',
    'website': 'http://www.yourwebsite.com',
    'depends': ['extension_views', 'sale', 'account', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'views/stock_picking_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
