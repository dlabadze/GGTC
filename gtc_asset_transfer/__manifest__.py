{
    'name': 'GTC Asset Transfer Report',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Reporting',
    'summary': 'Georgian Asset Transfer Report for GTC',
    'description': """
        GTC Asset Transfer Report
        =========================
        
        Georgian format asset transfer report for GTC company.
        Adds print button to journal entries with complete Georgian text.
    """,
    'author': 'GTC',
    'website': 'https://ggtc.ge',
    'depends': [
        'base',
        'web_studio',
        'account',
        
    ],
    'data': [
        'views/account_move_views.xml',
        'views/account_move_views_two.xml',
    ],
    'images': [
        'static/src/img/ggtc-logo.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}