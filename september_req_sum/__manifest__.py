{
    'name': 'September Line Quantity Sum',
    'version': '1.0',
    'summary': 'Adds a button to sum quantities by Code and Budget Name Main in September Line model',
    'description': """
        This module adds a button on the September Line form view.
        When clicked, it groups lines by Code and Budget Name Main, sums the quantities, and displays the result.
    """,
    'depends': [
        'base',
        'web_studio',
        'request_budget',
        'september_requests',
        'stock',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/server_action_view.xml',
        'views/button_in_form.xml',
    ],

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
