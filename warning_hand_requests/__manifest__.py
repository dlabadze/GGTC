{
    'name': 'Inventory Request Line Warning Logic',
    'version': '1.0',
    'category': 'Inventory',
    'depends': [
        'inventory_requests',
        'inventory_request_extension',
    ],
    'data': [
        'views/line_warnig.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}