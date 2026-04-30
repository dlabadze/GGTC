from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    valuations_ids = fields.Many2many(
        'stock.valuation.layer',
        string='Valuations',
        compute='_compute_valuations_data',
        readonly=True,
    )
    valuation_count = fields.Integer(
        string='Valuation Count',
        compute='_compute_valuations_data',
        store=True,
    )

    @api.depends('move_ids.stock_valuation_layer_ids')
    def _compute_valuations_data(self):
        for picking in self:
            valuations = picking.move_ids.stock_valuation_layer_ids
            picking.valuations_ids = valuations
            picking.valuation_count = len(valuations)