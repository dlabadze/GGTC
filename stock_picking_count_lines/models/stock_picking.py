from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    line_count = fields.Integer(string='Line Count', compute='_compute_line_count', store=True)

    @api.depends('move_ids')
    def _compute_line_count(self):
        for picking in self:
            picking.line_count = len(picking.move_ids)