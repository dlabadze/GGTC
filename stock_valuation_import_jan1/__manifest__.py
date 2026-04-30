{
    'name': 'Stock Valuation Import & Fix (Jan 1st)',
    'version': '1.1',
    'category': 'Inventory/Inventory',
    'summary': 'Import product costs from Excel and fix/backdate valuation layers and journal entries to Jan 1st.',
    'description': """
This module allows importing product costs from an Excel file and:
1. Updating standard_price on products.
2. Updating existing stock valuation layers (SVLs) for a specific date (e.g., Jan 1st).
3. Backdating linked journal entries (account.move) to the target date.
4. Correcting account assignments on journal items based on product category settings.
5. Deleting accidental revaluation moves created today.
6. Regenerating accounting entries for Jan 1st layers.
    """,
    'author': 'Antigravity',
    'depends': ['stock_account', 'account'],
    'external_dependencies': {
        'python': ['pandas', 'openpyxl'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_valuation_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
