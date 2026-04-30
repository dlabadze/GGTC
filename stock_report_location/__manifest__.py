{
    "name": "Stock Report by Location",
    "version": "1.0",
    "category": "Inventory",
    "depends": ["stock", 'web_studio', 'extension_views'],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_report_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

