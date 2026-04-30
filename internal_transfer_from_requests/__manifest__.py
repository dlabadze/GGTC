{
    'name': 'Inventory Requests Internal Transfers',
    'version': '1.0',
    'summary': 'Automatically create internal transfers for inventory requests',
    'description': """
                        This module extends inventory.
                        requests to generate internal stock transfers.
                    """,
    'depends': [
        'stock',
        'mrp',
        'inventory_requests',
    ],
    'data': [
        'views/server_action_view.xml',
        'views/button_view.xml',
        'views/inventroy_line_form.xml',
        'views/invontory_req_view.xml',
        'views/mrp_production_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
