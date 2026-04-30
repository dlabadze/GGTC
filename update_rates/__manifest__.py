{
    'name': 'NBG Currency Rates',
    'version': '1.0',
    'summary': 'Update currency rates from National Bank of Georgia',
    'description': """
        Simple module to update currency rates from the National Bank of Georgia (NBG).
        Features:
        - Update rates for specific date range
        - Automated daily updates
        - Skip weekends when rates aren't published
    """,
    'category': 'Accounting/Accounting',
    'author': 'FMG SOFT',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/update_rate_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}