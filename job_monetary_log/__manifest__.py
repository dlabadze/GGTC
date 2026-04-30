{
    'name': 'Job Position Salary Logger',
    'version': '1.0',
    'summary': 'Logs salary and date changes in Job Positions',
    'description': """
        This module logs the Studio salary field and contract date field
        whenever a Job Position (hr.job) is created or updated.
    """,
    'category': 'Human Resources',
    'depends': ['hr', 'mail'],
    'data': [
        'views/hr_job_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
