{
    'name': 'Invoice SOAP Integration',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Module for handling SOAP requests and fetching invoices',
    'description': """
        This module integrates with the SOAP service to fetch invoices from the Revenue Service of Georgia 
        and store them in the Invoice model. It provides a wizard for user input and handles SOAP requests 
        to retrieve invoice data.
    """,
    'author': 'Your Name',
    'website': 'https://yourwebsite.com',
    'depends': ['base', 'account'],  # Add other dependencies as needed
    'data': [
        'views/faqtura_views.xml',  # Wizard view
        'security/ir.model.access.csv',
        'views/faqtura_wizard.xml',
        'views/faqtura_buyer.xml',
        # Add any other views, security files, or data files if needed
    ],
    'demo': [
        # 'data/demo_data.xml',  # Uncomment and add demo data if applicable
    ],
    'assets': {
        'web.assets_backend': [
            'factura_download_module/static/src/js/button.js',
            'factura_download_module/static/src/xml/button.xml',
            'factura_download_module/static/src/xml/button1.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
