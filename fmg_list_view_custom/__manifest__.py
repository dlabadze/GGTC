{
    'name': 'Global List View Customizations',
    'version': '1.0',
    'category': 'Hidden/Tools',
    'summary': 'Makes list view headers sticky',
    'description': """
This module globally tweaks Odoo list (tree) views:
- Keeps the table column headers sticky at the top when scrolling through many lines.
    """,
    'author': 'FMG',
    'website': '',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'fmg_list_view_custom/static/src/scss/list_view_custom.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
