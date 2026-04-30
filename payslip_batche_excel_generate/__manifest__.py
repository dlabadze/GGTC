# -*- coding: utf-8 -*-
{
    'name': 'Payslip Batch Excel Generate',
    'version': '18.0.1.0.0',
    'depends': ['hr_payroll'],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'data': [
        'views/hr_payslip_run_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

