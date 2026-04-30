{
    'name': 'Fuel Filling Log Excel Import',
    'version': '18.0.1.0.0',
    'category': 'Fleet',
    'summary': 'Safe Excel import for fuel filling logs',
    'depends': ['fleet', 'base'],
    'external_dependencies': {
        'python': ['pandas', 'openpyxl'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/fuel_import_wizard_view.xml',
        'views/fleet_branch_views.xml',
        'views/fleet_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}