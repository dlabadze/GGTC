{
    'name': 'Inventory Line Color',
    'version': '18.0.1.0.0',
    'summary': 'Add a checkbox and color actions to inventory lines',
    'description': """
Adds a boolean field to inventory.line and two server actions:
- Mark selected lines green (and check the box)
- Clear color and uncheck the box
""",
    'category': 'Inventory',
    'depends': ['inventory_requests'],
    'data': [
        'views/inventory_line_views.xml',
        'data/server_actions.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
