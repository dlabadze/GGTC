{
    'name': 'Purchase Plan Preliminary',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'depends': [
        'base',
        'stock',
        'purchase_stock',
        'purchase',
        'budget',
    ],
    'data': [
        'views/purchase_plan_preliminary.xml',
        'security/ir.model.access.csv',
        'reports/report_template.xml',
        'reports/action_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',

}