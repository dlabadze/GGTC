# -*- coding: utf-8 -*-
{
    'name': 'Salary Attachment Import',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Import Salary Attachments from Excel using Employee Identification ID',
    'depends': ['hr_payroll', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/salary_attachment_import_wizard_views.xml',
        'wizard/salary_attachment_import_phone_views.xml',
        'views/salary_attachment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

