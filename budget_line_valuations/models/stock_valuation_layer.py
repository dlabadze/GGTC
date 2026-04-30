from odoo import fields, models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    picking_id = fields.Many2one(
        'stock.picking',
        related='stock_move_id.picking_id',
        string='Picking',
        store=False,
        readonly=True,
    )
