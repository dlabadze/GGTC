{
    'name': 'Inventory Request Extension',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Extensions for Inventory Requests',
    'description': """
        This module extends inventory_requests with:
        - Budget limit checking for inventory lines
        - Visual indicators for lines exceeding budget limits
    """,
    'depends': [
        'inventory_requests',
        'request_budget',  # For budgeting.line model
        'copy_of_sep_requests',  # For september.request, september.line
        'hr',  # For hr.department model
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/ganawileba_wizard_views.xml',
        'wizard/ganfaseba_wizard_views.xml',
        'views/inventory_request_views.xml',
        'views/inventory_line_views.xml',
        'views/request_report_wizard_views.xml',
        'views/request_report_line_views.xml',
        'views/budget_items_comparison_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

