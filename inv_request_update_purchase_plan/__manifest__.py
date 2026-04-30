{
    'name': 'Inventory Request Update Purchase Plan',
    'version': '18.0.1.0.0',
    'depends': ['stock', 'inventory_requests', 'budget'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard_update_purchase_plan_views.xml',
        'data/inventory_line_server_actions.xml',
        'views/inventory_line_views.xml',
    ],
}