{
    'name': 'Inventory Date To Quants',
    'version': '1.0',
    'category': 'Inventory/Inventory',
    'depends': ['stock', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/fix_date_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}