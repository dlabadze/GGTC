{
    'name': 'HR Employee Components Mod',
    'version': '1.0',
    'summary': 'Add search components to Studio model x_hr_employee_line_6b83f',
    'description': """
        This module adds a search view to the Studio model x_hr_employee_line_6b83f.
    """,
    'author': 'Antigravity',
    'depends': ['base', 'hr', 'hr_payroll'],
    'data': [
        'views/hr_employee_line_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
