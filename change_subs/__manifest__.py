{
    'name': 'Change Subs',
    'version': '18.0',
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
    'depends': ['sale_subscription','base','account',],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_views.xml',
        'views/subscription_views.xml',
        'views/purchase_plan_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}