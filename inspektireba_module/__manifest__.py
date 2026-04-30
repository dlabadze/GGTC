{
    'name': 'Inspektireba',
    'version': '1.0',
    'summary': 'Inspektireba workflow',
    'category': 'Custom',
    'depends': [
        'base',
        'mail',
        'purchase_requisition',
        'fleet',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/inspektireba_sequences.xml',
        'reports/inspektireba_reports.xml',
        'views/inspektireba_view.xml',
    ],
    'installable': True,
    'application': True,
}
