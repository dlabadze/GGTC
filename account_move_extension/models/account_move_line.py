from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    get_invoice_id = fields.Char(related='move_id.get_invoice_id', string='Invoice ID', readonly=True)
    move_id_comment = fields.Text(related='move_id.comment', string='კომენტარი', readonly=True)
    location_desk_id = fields.Many2one(related='move_id.location_desk_id')
