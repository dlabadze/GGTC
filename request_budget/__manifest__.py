{
    'name': 'Requests Budgeting',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Manage inventory requests with lines',
    'description': """
        This module provides:
        - Inventory Requests management
        - Inventory Lines tracking
        - Kanban and List views
        - Integrated form views
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'stock',
        'web_studio',
        'account',
        'analytic',
        'account_budget',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/inventory_request_views.xml',
        'views/inventory_line_views.xml',
        'views/confix.xml',
        'views/wizard.xml',
        'views/budget_excel_import_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}