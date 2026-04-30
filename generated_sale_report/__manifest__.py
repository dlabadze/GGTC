{
    'name': 'Sale Report1',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Sale Report',
    'depends': ['sale', 'stock', 'mrp', 'product_extend', 'point_of_sale'],
    'data': [
        'security/generated_sale_report_security.xml',
        'security/ir.model.access.csv',
        'wizard/generate_sale_report_wizard_views.xml',
        'views/generated_sale_report_views.xml',
        'views/product_supplier_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}