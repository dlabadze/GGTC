{
    'name': 'საწვავის ნაშთები',
    'version': '1.0',
    'category': 'Fleet',
    'summary': 'Simple module for fleet fuel remains',
    'description': """
        This module adds a simple model to track fuel remains for fleet.
        Fields:
        - Date
        - Reservoir Name
        - Initial Remain
        - Final Remain
    """,
    'author': 'Antigravity',
    'depends': ['base', 'fleet'],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_fuel_remain_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
