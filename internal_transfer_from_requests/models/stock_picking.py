from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_studio_request_ref = fields.Many2one(
        'inventory.request',
        string='Request Reference'
    )

    x_request_line_id = fields.Many2many(
        'inventory.line',
        string="Request Lines",
        relation='stock_picking_request_line_rel',
        column1='picking_id',
        column2='request_line_id',
        readonly=True,
        copy=False,
    )

    @api.onchange('location_id')
    def _onchange_update_move_location_id(self):
        if self.location_id:
            for move in self.move_ids:
                move.location_id = self.location_id
