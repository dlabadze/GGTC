# -*- coding: utf-8 -*-
{
    'name': 'Income Benefit Import',
    'version': '18.0.1.0.0',
    'depends': [
        'base',
        'hr',
        'salary_components_import_excel',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/income_benefit_import_wizard_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

