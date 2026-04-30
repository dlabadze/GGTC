{
    'name': 'Time Off Auto Number',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Add automatic sequential number to Time Off requests',
    'description': '''
Add automatic ნომერი (Number) field to Time Off requests.
Generates unique 5-digit numbers: 00001, 00002, 00003, etc.
    ''',
    'author': 'Your Company',
    'depends': [
        'hr_holidays',
    ],
    'data': [
        'views/hr_leave_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}