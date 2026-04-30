{
    'name': 'FMG Accounting Date Fix',
    'version': '18.0.1.0.0',
    'summary': 'Fixes the issue where accounting date is not changed in fmg_effective_date_change',
    'description': 'This module provides a more robust way to update the accounting date (account.move.date) associated with a stock picking.',
    'author': 'Antigravity',
    'category': 'Inventory/Accounting',
    'depends': ['stock', 'account', 'fmg_effective_date_change'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/fix_accounting_date_wizard_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
