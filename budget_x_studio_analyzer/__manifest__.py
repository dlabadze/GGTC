{
    'name': 'Budget X Studio Analyzer',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Analyze and verify budget.line x_studio_ field values',
    'depends': ['budget', 'account', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/analyzer_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
