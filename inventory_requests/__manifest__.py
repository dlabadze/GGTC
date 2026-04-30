{
    'name': 'Inventory Requests',
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
        'product',
        'purchase',
        'hr',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/server_actions.xml',
        # 'views/inventory_request_views.xml',
        # 'views/inventory_line_views.xml',
        'views/menu_views.xml',
        'views/confix.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}