{
    'name': 'Inventory Request Print',
    'version': '1.0',
    'category': 'Inventory',
    'depends': [
        'inventory_requests',
        'inventory_request_approver_users',
    ],
    'data': [
        'views/transport_template_view.xml',
        'views/action_view.xml',
        'views/report_template_view.xml',
        'views/sep_insp_req_templ.xml',
        'views/sep_insp_gr_req_templ.xml',
    ],
}
