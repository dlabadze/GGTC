from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    brdzaneba = fields.Many2one('approval.request', related='move_id.x_studio_brdzaneba')