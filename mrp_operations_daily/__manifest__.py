{
    'name': 'MRP Operations Daily',
    'version': '18.0.1.0.0',
    'depends': ['mrp'],
    'data': [
        'data/ir_cron_data.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

