{
    'name': 'Stock Valuation Import Wizard',
    'version': '18.0.1.0.0',
    'summary': 'Import product costs from Excel and backfill Jan 1st valuation layers',
    'author': 'GGTC',
    'category': 'Inventory/Valuation',
    'depends': [
        'stock_account',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_valuation_import_wizard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
