{
    'name': 'Payroll Journal Entry Partner Fix',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'depends': [
        'base',
        'hr',
        'account',
        'hr_payroll',
        'hr_payroll_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/payslip_account_filter_form_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}