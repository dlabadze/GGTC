{
    'name': 'Canban Restrict',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Canban Restrict',
    'description': """
        Canban Restrict.
    """,
    'depends': [
        'base',
    ],
    'assets': {
        'web.assets_backend': [
            '/canban_restrict/static/src/js/main.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}