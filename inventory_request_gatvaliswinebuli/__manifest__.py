{
    'name': 'Inventory Request Gatvaliswinebuli',
    'version': '18.0.1.0.0',
    'depends': ['base', 'inventory_requests', 'inventory_request_extension'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/gatvaliwinebuli_wizard_views.xml',
        'views/request_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inventory_request_gatvaliswinebuli/static/src/purchase_check_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}