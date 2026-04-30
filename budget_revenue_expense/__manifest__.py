{
    'name': 'Budget Revenue & Expense Fields',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add conditional fields for budget lines based on budget type',
    'description': """
Budget Revenue & Expense Fields
================================
This module extends budget.line with conditional fields:
- Revenue-specific fields (shown when budget_type = 'revenue')
- Expense-specific fields (shown when budget_type = 'expense')
- Automatic calculations for differences
- Revenue Code field in account.move and account.payment
""",
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'account_budget',
        'budget',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/budget_line_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/cash_flow_import_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
