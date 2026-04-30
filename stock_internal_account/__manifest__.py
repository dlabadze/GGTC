# -*- coding: utf-8 -*-
{
    'name': 'Stock Internal Transfer Account Reconciliation',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Add account fields for internal transfers and reconciliation',
    'description': """
Stock Internal Transfer Account Reconciliation
==============================================
This module adds account fields for internal transfers and provides
reconciliation functionality.

Features:
---------
* Add stock_account_ang field on stock.picking for internal transfers
* Add move_account_ang field on stock.move for internal transfers
* Action to reconcile account move lines based on configured accounts
    """,
    'depends': ['stock_account', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/stock_move_views.xml',
        'views/account_journal_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

