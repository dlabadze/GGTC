{
    'name': 'Done Invoice SOAP Integration',
    'version': '1.1.0',
    'category': 'Accounting',
    'summary': 'Fetch invoices by agree_date (RS get_user_invoices) with 30-day interval',
    'description': """
        This module integrates with the RS SOAP service to fetch invoices using get_user_invoices,
        which returns agree_date. Date range is limited to 30-day intervals. Records are created
        with agree_date from the Revenue Service of Georgia.
    """,
    'author': 'Your Name',
    'website': 'https://yourwebsite.com',
    'depends': ['base', 'account', 'product', 'purchase', 'purchase_requisition', 'extension_views'],
    'data': [
        'security/ir.model.access.csv',
        'views/done_faqtura_wizard.xml',
        'views/done_faqtura_views.xml',
        'views/done_factura_server_actions.xml',
        'views/purchase_requisition_avansi_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
