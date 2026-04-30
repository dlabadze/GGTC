{
    'name': 'User Location By Requested',
    'version': '1.0',
    'depends': [
        'base',
        'web_studio',
        'stock',
        'september_requests',
        'inventory_requests',
    ],
    'data': [
        'views/server_action_view.xml',
        'views/button_in_form.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
