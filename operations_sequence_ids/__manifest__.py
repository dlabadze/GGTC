{
    'name': 'Operations Sequence IDs',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Adds global and per-operation-type sequence fields to x_operations',
    'description': 'Adds command_seq and operation_type_seq fields with automatic numbering.',
    'author': 'Giorgi',
    'depends': ['base', 'web_studio', 'studio_customization'],
    'data': [
        'views/operations_views.xml',
    ],
    'installable': True,
    'application': False,
}
