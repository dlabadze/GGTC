# -*- coding: utf-8 -*-
{
    'name': 'Payroll Import with Phone',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Import payroll data from Excel using mobile phone numbers',
    'depends': ['hr_payroll', 'hr', 'hr_work_entry_contract_enterprise'],
    'data': [
        'security/ir.model.access.csv',
        'views/mobile_debt_views.xml',
        'wizard/mobile_debt_import_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

