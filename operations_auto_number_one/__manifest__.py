{
    'name': 'X Operations Extension',
    'version': '18.0.1.0',
    'depends': ['base'],
    'author': 'Fmg Soft',
    'category': 'Extra Tools',
    'summary': 'Extension for X Operations Model with Auto Numbering',
    'description': ('Adds sequence functionality to x_operations model '
                    'with yearly reset'),
    'data': [
        'views/operations_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}