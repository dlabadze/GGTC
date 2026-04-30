{
    'name': 'Copy September To Inventory',
    'version': '1.0.0',
    'summary': 'Copies september request to inventory request',
    'depends': [
        'base',
        'inventory_requests',
        'web_studio',
        'request_budget',
        'september_requests',
        'stock',
        'contacts',
        'hr',
    ],
    'data': [
        'views/server_action.xml',
        'views/button_view.xml',
        'views/inventroy_request_view.xml',
    ],
    'installable': True,
    'application': False,
}
