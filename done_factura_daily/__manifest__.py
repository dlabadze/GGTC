{
    'name': 'Done Factura Daily Cron',
    'version': '1.0.0',
    'category': 'Accounting',
    'summary': 'Daily cron: auto-create done.factura from avansi for active contracts',
    'depends': ['done_factura_download_module', 'purchase_requisition', 'account'],
    'data': [
        'data/cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
