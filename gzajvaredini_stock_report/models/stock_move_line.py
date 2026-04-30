from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    value = fields.Monetary(
        string='Value',
        compute='_compute_value',
        currency_field='currency_id',
        store=False,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )

    @api.depends(
        'stock_valuation_layer_ids.value',
        'quantity',
        'product_uom',
        'product_id',
        'company_id',
        'date',
    )
    def _compute_value(self):
        for move in self:
            move.value = move._compute_move_value()

    def _compute_move_value(self):
        self.ensure_one()
        if not self.product_id or not self.company_id:
            return 0.0

        move_value = sum(abs(layer.value or 0.0) for layer in self.stock_valuation_layer_ids)
        if move_value:
            return move_value

        qty = abs(self._get_qty_in_product_uom())
        if not qty:
            return 0.0

        unit_cost = self._get_last_non_zero_unit_cost()
        if not unit_cost:
            unit_cost = self.product_id.standard_price or 0.0
        return qty * abs(unit_cost)

    def _get_qty_in_product_uom(self):
        self.ensure_one()
        qty = self.quantity or 0.0
        if not qty:
            return 0.0
        if self.product_uom and self.product_id and self.product_id.uom_id:
            return self.product_uom._compute_quantity(qty, self.product_id.uom_id)
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