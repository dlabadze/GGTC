from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    partner_vat = fields.Char(
        string='Partner VAT',
        related='partner_id.vat',
        readonly=True,
        store=False,
    )

