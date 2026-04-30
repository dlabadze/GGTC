{
    'name': 'vacancy hr',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Add vacancy count field to job positions',
    'description': """
        This module adds a vacancy count field to job positions that shows
        the difference between recruitment quota and current employee count.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['hr'],
    'data': [
        'views/hr_job_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
