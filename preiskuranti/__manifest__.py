{
    'name': 'Preiskuranti',
    'version': '1.0',
    'summary': 'ტრანსპორტის პრეისკურანტი',
    'category': 'Fleet',
    'depends': ['base', 'fleet', 'stock','inventory_requests'],
    'data': [
        'security/ir.model.access.csv',
        'views/preiskuranti_view.xml',
        'views/inventory_request_view_temo.xml',
    ],
    'sequence': 200,
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'preiskuranti/static/src/css/style.css',
        ],
    },
}