{
    'name': 'Accounting Library',
    'version': '1.0',
    'summary': 'Registry of documents for accountants',
    'category': 'Accounting',
    'depends': [
        'base',
        'mail',
        'account',
        'approvals',
        'inspektireba_module',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/accounting_library_views.xml',
        'views/accounting_library_menus.xml',
    ],
    'installable': True,
    'application': True,
}
