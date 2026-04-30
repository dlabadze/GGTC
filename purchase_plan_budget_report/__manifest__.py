{
    'name': 'Purchase Plan Budget Report',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Visual report showing purchase plan lines with negative budget CPV amounts',
    'depends': ['budget', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_plan_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
