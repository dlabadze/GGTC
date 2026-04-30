# -*- coding: utf-8 -*-
{
    'name': 'Inventory Line Scroll Arrows',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Add horizontal scroll arrows with smooth animation for inventory lines table',
    'description': """
        Add left/right navigation arrows to inventory lines table
        - Smooth horizontal scrolling
        - Arrows appear on hover
        - Modern carousel-like navigation
    """,
    'author': 'Your Company',
    'depends': ['inventory_requests'],
    'data': [
        # 'views/inventory_line_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inventory_line_scroll_arrows/static/src/css/inventory_line_scroll.css',
            'inventory_line_scroll_arrows/static/src/js/inventory_line_scroll.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
