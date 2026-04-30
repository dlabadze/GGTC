from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    request_number = fields.Char(
        related='move_id.request_number',
        string='შესყიდვის მოთხოვნის ნომერი',
        readonly=True,
    )
    # x_request_number_manual = fields.Char(
    #     related='picking_id.x_request_number_manual',
    #     string='მოთხოვნის ნომერი (ხელით)',
    #     readonly=True,
    # )
    comment_picking = fields.Text(
        related='picking_id.comment',
        string='საფუძველი',
        readonly=True,
    )
    aqtis_nomeri = fields.Char(
        related='picking_id.x_studio_aqtis_nomeri',
        string='აქტის ნოემრი',
        readonly=True,
    )
    inventory_request_id = fields.Many2one(
        'inventory.request',
        related='picking_id.x_studio_request_ref',
        readonly=True,
    )
    value = fields.Monetary(
        string='Value',
        compute='_compute_value',
        currency_field='currency_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )

    @api.depends(
        'move_id',
        'move_id.stock_valuation_layer_ids',
        'move_id.stock_valuation_layer_ids.value',
        'move_id.stock_valuation_layer_ids.product_id',
        'quantity',
        'product_uom_id',
        'product_id',
        'company_id',
        'date',
    )
    def _compute_value(self):
        for line in self:
            line.value = line._compute_line_value()

    def _compute_line_value(self):
        self.ensure_one()
        # _logger.info(f"|||||||||||||||{self.id}|||||||||||||||||||||||||")
        if not self.product_id or not self.company_id:
            return 0.0

        qty = abs(self._get_qty_in_product_uom())
        if not qty:
            return 0.0

        move = self.move_id
        if move and 'stock_valuation_layer_ids' in move._fields:
            move_layers = move.stock_valuation_layer_ids.filtered(
                lambda layer: layer.product_id.id == self.product_id.id
            )
            move_value = sum(abs(layer.value or 0.0) for layer in move_layers)
            if self.id == 59200:
                _logger.info(f"move layers: {move_layers}")
                _logger.info(f"მოვე move value: {move_value}")
            if move_value:
                return move_value

        unit_cost = self._get_last_non_zero_unit_cost()
        if not unit_cost:
            unit_cost = self.product_id.standard_price or 0.0
        return qty * abs(unit_cost)

    def _get_qty_in_product_uom(self):
        self.ensure_one()
        qty = self.quantity or 0.0
        if not qty:
            return 0.0
        if self.product_uom_id and self.product_id and self.product_id.uom_id:
            return self.product_uom_id._compute_quantity(qty, self.product_id.uom_id)
        return qty

    def _get_last_non_zero_unit_cost(self):
        self.ensure_one()
        try:
            valuation_layer_model = self.env['stock.valuation.layer']
        except KeyError:
            return 0.0

        valuation_domain = [
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', self.company_id.id),
            ('unit_cost', '!=', 0.0),
        ]
        if self.date:
            valuation_domain.append(('create_date', '<=', self.date))

        last_layer = valuation_layer_model.search(
            valuation_domain,
            order='create_date desc, id desc',
            limit=1,
        )
        return last_layer.unit_cost if last_layer else 0.0
