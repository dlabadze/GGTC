{
    "name": "Update Inventory Line Prices",
    "version": "18.0.1.0.0",
    "category": "Inventory",
    "summary": "Upload Excel and update inventory line prices",
    "depends": [
        "inventory_request_extension",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/inventory_line_price_upload_wizard_views.xml",
        "views/inventory_request_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
