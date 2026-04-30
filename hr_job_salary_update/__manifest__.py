{
    'name': 'HR Job Expected Salary Bulk Update',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_job_views.xml',
        'views/job_salary_update_wizard_view.xml',
    ],
    'installable': True,
}
