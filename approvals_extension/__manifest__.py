{
    'name': 'Approvals Extension',
    'version': '18.0.1.0.0',
    'depends': [
        'base',
        'approvals',
    ],
    'external_dependencies': {
        'python': ['python-docx', 'Pillow', 'cairosvg'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/approval_reqeust_views.xml',
        'wizard/create_new_request_wizar_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}