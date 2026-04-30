{
    'name': 'Work Trip',
    'version': '1.0',
    'summary': 'Import Work Trip',
    'category': 'Human Resources/Payroll',
    'depends': ['base', 'account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/work_trip_import_views.xml',
        'views/menu_views.xml',
        'views/acc_move_line_view.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}