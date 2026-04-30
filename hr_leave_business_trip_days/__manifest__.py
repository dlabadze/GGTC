{
    'name': 'HR Leave Include Weekends for Business Trips',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Includes weekends in leave calculation when Time Off Type is "მივლინება".',
    'author': 'Your Company',
    'depends': ['hr_holidays'],
    'data': [
        'views/hr_leave_views.xml',
    ],
    'installable': True,
    'application': False,
}
