{
    'name': 'External File Editor',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Edit files with external editor integration',
    'description': """
        External File Editor Integration
        =================================
        This module allows editing files using an external editor service.
        - Sends file to external editor at http://localhost:4706/wordedit
        - Receives callback with edited file
        - Updates the file in approval request
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'approvals', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/approval_request_views.xml',
        'views/external_file_editor_db.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'external_file_editor/static/src/js/file_editor.js',
            'external_file_editor/static/src/xml/file_editor.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
