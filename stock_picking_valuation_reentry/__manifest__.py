{
    'name': 'Stock Picking Valuation Re-entry',
    'version': '1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Re-process or manually create accounting entries for stock pickings.',
    'description': """
        This module adds a button to stock pickings to re-process valuation entries.
        It deletes existing valuation layers and account moves linked to the picking
        and re-generates them using the picking date.
    """,
    'author': 'Antigravity',
    'depends': ['stock_account', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
