{
    'name': 'Inventory Request Return Button',
    'version': '18.0.1.0.0',
    'depends': ['inventory_requests'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/return_button_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}