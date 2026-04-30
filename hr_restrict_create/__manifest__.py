# -*- coding: utf-8 -*-
{
    'name': 'HR Restrict Department/Job Create',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Restrict Create and Create-and-Edit options on department fields for non-admin users',
    'description': """
        This module restricts the quick-create ("Create …" and "Create and Edit…")
        dropdown options on the following many2one fields for regular (non-administrator) users:

        - Parent Department (parent_id) on the Department form
        - Department (department_id) on the Job Position form

        Administrator users retain full create access.
    """,
    'license': 'LGPL-3',
    'author': 'Abano',
    'depends': ['hr', 'hr_recruitment', 'hr_payroll'],
    'data': [
        'views/hr_department_restrict_view.xml',
        'views/hr_job_restrict_view.xml',
        'views/hr_payslip_employees_restrict_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
