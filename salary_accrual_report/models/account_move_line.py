from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    partner_vat = fields.Char(related='partner_id.vat')