{
    'name': 'Inventory Request Fields Invisible',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'depends': [
        'inventory_requests',
        'inventory_request_extension',
        'preiskuranti',
        'inventory_request_gatvaliswinebuli',
    ],
    'data': [
        'views/inventory_request_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}