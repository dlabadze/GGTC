{
    'name': "Inventory Excel Import (Backdated)",
    'summary': "Upload starting inventory via Excel and force a specific backdate (e.g., Jan 1st).",
    'description': """
        This module provides a wizard in the Inventory app to upload an exported Odoo product Excel file 
        (containing XML IDs for products and locations) and create an inventory adjustment. 
        It forces the date of the resulting stock moves to a user-selected date to keep historical reports mathematically accurate.
    """,
    'author': "Custom",
    'category': 'Inventory',
    'version': '18.0.1.0.0',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_inventory_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
