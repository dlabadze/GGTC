{
    'name': 'Inventory Request - Horizontal Scroll Buttons',
    'version': '18.0.1.0.0',
    'summary': 'Adds floating left/right scroll buttons over the one2many lines in inventory.request form view',
    'author': 'Custom',
    'category': 'Inventory',
    'depends': ['base', 'web'],
    'assets': {
        'web.assets_backend': [
            'inventory_request_scroll/static/src/css/scroll_buttons.css',
            'inventory_request_scroll/static/src/js/scroll_buttons.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
