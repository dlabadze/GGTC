{
    "name": "Invoice Import from Excel",
    "version": "18.0.1.0.0",
    "depends": [
                "account",
                "extension_views",
                ],
    "category": "Accounting",
    "summary": "Upload Excel and create invoices automatically",
    "data": [
        "security/ir.model.access.csv",
        "views/invoice_import_wizard_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
