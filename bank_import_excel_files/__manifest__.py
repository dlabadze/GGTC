{
    "name": "Bank Import from Excel",
    "version": "18.0.1.0.0",
    "depends": ["account",
                'account_accountant',
                ],
    "category": "Accounting",
    "data": [
        "security/ir.model.access.csv",
        "views/statement_lines_list_view.xml",
        "views/bank_import_wizard_view.xml",
        "views/dashboard_import_button.xml",
        "views/bank_kanban_view.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
