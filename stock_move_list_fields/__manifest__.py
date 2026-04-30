{
    'name': 'Stock Move Line List Fields',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'depends': [
        'stock',
        'stock_report_location'
    ],
    'data': [
        'views/stock_move_line_list.xml',
        'views/gza_stock_location_report_view.xml',
        'views/stock_move_history_list_view.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}