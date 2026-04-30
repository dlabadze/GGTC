{
    'name': 'Bank Actions',
    "version": "18.0.1.0.0",
    'depends': ['account'],
    'data': [
        'views/post_action_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bank_actions/static/src/js/bank_rec_widget_extension.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
    'auto_install': False,
}