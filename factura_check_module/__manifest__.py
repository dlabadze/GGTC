{
    'name': 'Factura Check Module',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Check and update factura invoice numbers from faqtura system',
    'description': """
        This module provides functionality to check selected accounting invoices
        against the faqtura system and update f_series and f_number fields if they differ.
    """,
    'author': 'Your Company',
    'depends': ['account', 'extension_views'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

