{
    'name': 'Extend Views',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'This module extends the views of the Sale Order',
    'license': 'LGPL-3',
    'author': 'Your Name',
    'website': 'http://www.yourwebsite.com',
    'depends': ['sale','base', 'stock','product','web','purchase','hr','stock_landed_costs','web_studio','purchase_stock'],
    'data': [
        'views/sale_order_view.xml',
        'views/product_template_view.xml',
        'views/users_rs_ge.xml',
        'views/res_partner_view.xml',
        'views/stock.location.xml',
        'views/product_inventory.xml',
        'security/ir.model.access.csv',
        'views/stockpickinginherit.xml',
        'security/security.xml',
        'views/account_move.xml',
        'views/purchase_order.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,

}