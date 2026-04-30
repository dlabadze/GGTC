{
    'name': 'Gadziritadeba',
    'version': '1.0',
    'summary': 'Track internal scrap transfers with auto-loaded product lines',
    'category': 'Inventory',
    'depends': ['stock',
    'account',
    'account_asset'],
    'data': [
        'security/ir.model.access.csv',
        'views/gadziritadeba_view.xml',
       # 'x_asset_movement_log',
    ],
    'sequence': 999,
    'installable': True,
    'application': True,
}
