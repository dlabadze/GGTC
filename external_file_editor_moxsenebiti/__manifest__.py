{
    'name': 'External File Editor - Moxsenebiti',
    'version': '18.0.1.0.0',
    'depends': ['base', 'external_file_editor'],
    'data': [
        'security/ir.model.access.csv',
        'views/moxsenebiti_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'external_file_editor_moxsenebiti/static/src/js/file_editor.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
