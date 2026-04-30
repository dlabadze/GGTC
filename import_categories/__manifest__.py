{
    'name': 'Import Categories',
    'version': '18.0.1.0.0',
    'depends': [
        'base',
        'product',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_categories_wizard_views.xml',
        'wizard/update_products_wizard_views.xml',
        'views/product_category_views.xml',
        'views/product_product_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
