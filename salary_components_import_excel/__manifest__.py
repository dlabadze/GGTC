# -*- coding: utf-8 -*-
{
    'name': 'Salary Components Import Excel',
    'version': '18.0.1.0.0',
    'depends': [
        'base',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/salary_components_import_wizard_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

