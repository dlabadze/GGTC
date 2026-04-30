{
    'name': 'Inventory Request Purchase/Warehouse Logic',
    'depends': [
        'stock',
        'product',
        'inventory_requests',
        # 'inventory_request_fields_invisible',
    ],
    'data': [
        # 'views/warehouse_read_only.xml',
        # 'views/inventory_line_form.xml',
        # 'views/request_form_attachment.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
