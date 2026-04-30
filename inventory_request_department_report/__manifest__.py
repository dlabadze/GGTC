{
    'name': 'Inventory Request Department Report',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Report lines for same-department requests by product overlap and date range',
    'depends': ['inventory_request_extension'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_dept_report_views.xml',
        'wizard/department_report_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
