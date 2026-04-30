{
    'name': 'Batch Payslip Department Selection',
    'version': '1.0.0',
    'summary': 'Select specific child departments in payslip generation wizard',
    'category': 'Human Resources/Payroll',
    'author': 'Your Company',
    'license': 'LGPL-3',

    'depends': [
        'hr',
        'hr_payroll',   # ENTERPRISE payroll (required)
    ],

    'data': [
        'views/batch_payslip_modification_view.xml',
    ],

    'installable': True,
    'application': False,
}