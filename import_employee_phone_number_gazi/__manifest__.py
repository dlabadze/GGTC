# -*- coding: utf-8 -*-
{
    'name': 'Import Employee Phone Number Gazi',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Import employee phone numbers from Excel file (Gazi format)',
    'depends': [
        'base',
        'hr',
        'salary_components_import_excel',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/employee_phone_import_wizard_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

