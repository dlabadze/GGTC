{
    "name": "Approval Request Table Lines",
    "version": "1.0",
    "summary": "Adds table lines to approval request",
    "depends": [
        "approvals",
        "fleet",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/approval_req_table.xml",
        'views/ext_view.xml',
    ],
    "application": False,
    "installable": True,
}
