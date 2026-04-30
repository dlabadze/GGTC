{
    'name': 'Create Purchase Agreement',
    'version': '1.0.0',
    'depends': [
        'base',
        'inventory_requests',
        'web_studio',
        'request_budget',
        'purchase',
        'stock'
        # 'operations',
    ],
    'data': [
        'data/ir_cron.xml',
        'views/action_view.xml',
        # 'views/inherit_studio.xml',
        'views/invontory_req_line.xml',
        'views/inventory_request_form_view.xml',
        'views/stock_quant_view.xml',
    ],
    'installable': True,
    'application': False,
}
