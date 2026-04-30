{
    'name': 'Salary Management',
    'version': '1.0',
    'summary': 'Import salaries and generate journal entries',
    'description': """
        This module allows you to:
        - Import salary data from Excel files
        - Generate journal entries based on imported salary data
    """,
    'category': 'Human Resources/Payroll',
    'author': 'My Company',
    'website': 'https://www.mycompany.com',
    'depends': ['base', 'account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/salary_import_views.xml',
        'views/account_move_views.xml',
        'views/salary_batch_import_views.xml',
        'views/insurance_import_views.xml',
        'views/salary_payment_import_views.xml',
        'views/employee_report_views.xml',
        'views/menu_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}