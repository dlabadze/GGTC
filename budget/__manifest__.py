{
    'name': 'Accounting Procurement Planning',
    'version': '18.0.1.0.2',
    'category': 'Accounting/Accounting',
    'summary': 'Procurement Planning for Accounting',
    'description': """
Accounting Procurement Planning
=============================
This module provides procurement planning capabilities integrated with accounting:
- Budget tracking
- CPV code management
- Procurement planning
- Integration with journal entries
- Analytic accounting support
""",
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'analytic',
        'account_budget',
        'base',
        'website',
        'purchase_requisition',
        'web_studio',
        'stock',
        'purchase_stock'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/budget_views.xml',
        'views/account_analytic_views.xml',
        'views/purchase_plans.xml',
        'views/visual_report_template.xml',
        'views/purchase_plan_lines_report_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/budget/static/src/js/main.js',
        ],
    },
    'post_init_hook': 'create_missing_budget_line_changes',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',

}