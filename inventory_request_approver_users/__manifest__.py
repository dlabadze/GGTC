{
    'name': 'Inventory Request Approver Users',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'depends': [
        'inventory_requests', 
        'hr',
        'inventory_request_extension', 
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_request_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}