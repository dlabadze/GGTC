# -*- coding: utf-8 -*-

from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    move_account_ang = fields.Many2one(
        'account.account',
        string='Reconciliation Account',
        domain="[('deprecated', '=', False)]",
        help='Account to use for reconciliation of this move\'s accounting entries. '
             'If not set, the Stock Account from picking will be used.',
        check_company=True,
    )


