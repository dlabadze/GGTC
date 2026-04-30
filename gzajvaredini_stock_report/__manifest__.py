# -*- coding: utf-8 -*-
{
    'name': 'Gza Stock Report',
    'version': '1.1.0',
    'category': 'Inventory',
    'summary': 'Enhanced stock reporting with actual transaction prices',
    'description': """
        Stock Report with Enhanced Amount Calculations
        ================================================
        
        Features:
        ---------
        * Uses actual purchase prices from purchase orders
        * Tracks transaction-level costs accurately
        * Date range filtering
        * Warehouse and category filtering
        * Detailed movement history
        * Export to Excel/PDF
        
        Version 1.1 Changes:
        --------------------
        * Enhanced amount calculations using actual transaction prices
        * Better handling of multi-price purchases
        * Improved JSONB standard_price handling
        * Comprehensive documentation added
    """,
    'author': 'Gza (თბილისერვისი)',
    'website': '',
    'depends': ["stock", 'web_studio', 'extension_views'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}