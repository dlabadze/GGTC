from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    location_desk_id = fields.Many2one('stock.location', string='საწყისი ლოკაცია')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    brdzaneba = fields.Char()
