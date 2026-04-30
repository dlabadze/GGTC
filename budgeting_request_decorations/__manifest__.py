{
    'name': 'Budgeting Request Decorations',
    'version': '1.0',
    'category': 'Customizations',
    'summary': 'Adds decorative styling to budgeting request views',
    'description': """
        This module adds decorative styling to budgeting request views,
        highlighting price fields based on stage conditions.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'web', 'web_studio'],
    'data': [
        'views/budgeting_request_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
