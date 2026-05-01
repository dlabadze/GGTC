{
    'name': 'საბეჭდი ფორმები - Sabechdi Formebi',
    'version': '18.0.1.0.0',
    'category': 'Documents',
    'summary': 'Georgian Request Forms - მოთხოვნის ფორმები',
    'license': 'LGPL-3',
    
    'depends': [
        'base',
        'stock',
        'web',
        'inventory_requests',
    ],
    
    'data': [
        'views/stock_picking_view.xml',
        'views/reset_reports.xml',
        'views/nimushis_forma_ori.xml',
        'views/nimushis_forma_ori_plus.xml',
        'views/nimushis_forma_ori_plus_declaration.xml',
        'views/nimushis_forma_sami.xml',
        'views/nimushis_forma_sami_xelit.xml',
        'views/nimushis_forma_samia.xml',
        'views/nimushis_forma_samib.xml',
        'views/nimushis_forma_otxi.xml',
        'views/nimushis_forma_otxi_xelit.xml',
        'views/nimushis_forma_otxia.xml',
        'views/nimushis_forma_otxia_xelit.xml',
        'views/nimushis_forma_otxib.xml',
        'views/nimushis_forma_otxib_xelit.xml',
        'views/nimushis_forma_xuti.xml',
        'views/nimushis_forma_xuti_plus.xml',
        'views/nimushis_forma_xuti_odorant.xml',
    ],
    
    
    'installable': True,
    'application': True,
    'auto_install': False,
    
    'external_dependencies': {
        'python': [],
    },
}