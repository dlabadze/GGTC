{
    'name': 'ზედნადებების ჩამოტვირთვა',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Manage and fetch waybills',
    'description': """
        This module allows you to manage waybills and fetch them from an external service.
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['base', 'account','web'],
    'data': [
        'security/ir.model.access.csv',
        'views/waybill_views.xml',
        'views/waybill_views_1.xml',
        'views/waybill_views_3.xml',
        'views/waybill_views_4.xml',
        'views/waybill_views_5.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'waybill_management_custom/static/src/css/custom_background.css',
            'waybill_management_custom/static/src/js/button.js',
            'waybill_management_custom/static/src/xml/button_1.xml',
            'waybill_management_custom/static/src/xml/button_2.xml',
            'waybill_management_custom/static/src/xml/button_3.xml',
            'waybill_management_custom/static/src/xml/button_4.xml',
            'waybill_management_custom/static/src/xml/button_5.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
