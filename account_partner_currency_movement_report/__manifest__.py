{
    'name': 'Account Partner Currency Movement Report',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Generate partner currency movement reports showing movements by client/vendor/employee, currency and account',
    'description': """
Account Partner Currency Movement Report
========================================

This module provides a comprehensive partner-focused currency movement report that shows:

* Partner movements (Clients/Vendors/Employees) by currency and account
* Opening balances by partner, currency and account
* Closing balances by partner, currency and account  
* Total debit and credit movements during the period
* Net movement calculations
* Multi-currency support with partner focus
* Filtering by date range, partners, accounts, and currencies
* Hierarchical view: Partner → Currency → Account
* Multiple view modes (list, pivot, graph)
* PDF export functionality
* Excel export capability

The report groups data by partners first, then currencies, then accounts, providing detailed insights into partner-specific financial movements across different currencies.

Key Features:
- Partner-centric reporting (clients, vendors, employees)
- Period-based reporting with customizable date ranges
- Multi-company support
- Advanced filtering options
- Interactive pivot tables and charts
- Drill-down functionality to journal entries
- Professional PDF reports
- Data export capabilities

Use Cases:
- Client/vendor balance analysis by currency
- Partner-specific foreign exchange tracking
- Employee expense analysis by currency
- Partner reconciliation reporting
- Regulatory compliance reporting
- Partner financial analysis
    """,
    'author': 'Custom Development',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/partner_currency_movement_report_wizard_view.xml',
        'views/partner_currency_movement_report_view.xml',
        'report/partner_currency_movement_report_template.xml',
        'views/partner_currency_movement_report_menu.xml',
    ],
    'demo': [],
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 101,
} 