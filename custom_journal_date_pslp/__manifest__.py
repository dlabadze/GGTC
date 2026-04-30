{
    'name': 'Payroll Batch Accounting Date',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'depends': [
        'hr_payroll',
        'hr_payroll_account',
        'account'
    ],
    'data': [
        'views/payslip_run_form_date.xml',
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}