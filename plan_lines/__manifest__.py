{
    'name': 'Purchase Plan Reports',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Purchase Plan and Purchase Plan Changes Reports',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'purchase',
        'budget',
    ],
    'data': [
        'report/report_template.xml',
        'report/action_view.xml',
        'views/changes_lines.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}