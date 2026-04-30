{
    'name': 'Charicxvebi Excel',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Generate Excel from Accounting',
    'description': """
        This module generates Excel reports from accounting data.
    """,
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/charicxvebi_excel_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
