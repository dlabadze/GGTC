{
    'name': 'HR Payroll Contract-End Fix',
    'version': '1.0',
    'summary': 'Fixes incorrect counting of public holidays after contract end in payslips',
    'description': """
        This module prevents Odoo from counting public holidays
        as worked days when an employee’s contract ends before
        the payslip period finishes.
    """,
    'author': 'Temo',
    'license': 'LGPL-3',
    'depends': ['hr_payroll'],
    'data': [],
    'installable': True,
    'application': False,
}