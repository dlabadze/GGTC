{
    'name': 'Gas Invoice API',
    'version': '18.0.1.0.0',
    'summary': 'REST API for creating gas transportation invoices',
    'description': """
        This module provides a REST API endpoint to create customer invoices
        for gas transportation services from external systems via HTTP POST requests.

        Features:
        - Customer management by Tax ID
        - Automatic invoice creation with Georgian service name
        - Simple JSON API without authentication
        - Handles quantity in m3, pricing, and amounts
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Accounting/Invoicing',
    'depends': ['base', 'account'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}