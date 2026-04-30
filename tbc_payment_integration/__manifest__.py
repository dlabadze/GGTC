# -*- coding: utf-8 -*-
{
    'name': "TBC Payment Integration",

    'summary': "TBC Bank Integration with Odoo Standard Reconciliation",

    'description': """
TBC Bank Payment Integration - Reworked for Odoo Standard Flow
=================================================================
This module integrates TBC Bank transactions with Odoo's standard bank reconciliation system.

Key Features:
* Import TBC bank transactions from BOG API
* Automatic creation of bank statement lines
* Custom reconciliation models using TBC code mappings
* Automatic partner detection from tax codes (INN)
* Product group-based account mapping
* Full integration with Odoo's reconciliation widget

Version 2.0 - Completely reworked to use Odoo's standard accounting lifecycle:
- Transactions → Bank Statement Lines → Reconciliation → Posted Entries

Legacy compatibility maintained for existing data.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Accounting/Accounting',
    'version': '2.0.0',

    # Module dependencies - now requires account_accountant for reconciliation widget
    'depends': ['base', 'account', 'web', 'account_accountant', 'purchase_requisition', 'budget'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/Tbc_view.xml',
        'views/views.xml',
        'views/reconcile_model_views.xml',
        'views/purchase_requisition_payment_wizard_view.xml',
        'views/budget_payment_wizard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tbc_payment_integration/static/src/js/button.js',
            'tbc_payment_integration/static/src/js/purchase_requisition_button.js',
            'tbc_payment_integration/static/src/xml/button.xml',
            'tbc_payment_integration/static/src/xml/button_payment_integration.xml',
            'tbc_payment_integration/static/src/xml/bank_rec_widget_inherit.xml',
            'tbc_payment_integration/static/src/xml/purchase_requisition_button.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
