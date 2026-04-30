{
    'name': 'Fuel Trip Management',
    'version': '18.0.1.0.0',
    'category': 'Fleet',
    'summary': 'Manage fuel expenses for trips',
    'description': """
        Odoo 18 module to record fuel expenses incurred during trips.
        Features:
        - Link to Approval Requests
        - Link to Fleet Vehicles
        - Record Fuel Amount
    """,
    'author': 'Antigravity',
    'depends': ['fleet', 'approvals', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/fuel_trip_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
