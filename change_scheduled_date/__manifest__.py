{
    'name': 'Change Scheduled Date',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'depends': ['stock','mrp'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/change_scheduled_date_wizard_views.xml',
        'wizard/change_production_date_wizard_view.xml',
        'data/server_action.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
