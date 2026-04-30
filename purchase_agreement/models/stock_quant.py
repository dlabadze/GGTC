from odoo import models, fields, api, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    free_quantity = fields.Float(
        string='Free Quantity',
        compute='_compute_free_quantity',
        store=True,
    )

    @api.depends('quantity', 'reserved_quantity')
    def _compute_free_quantity(self):
        for quant in self:
            quant.free_quantity = (quant.quantity or 0.0) - (quant.reserved_quantity or 0.0)

    @api.model
    def cron_update_free_quantity(self):
        records = self.search([])
        for record in records:
            inventory_quantity_auto_apply = record.inventory_quantity_auto_apply or 0.0
            reserved_quantity = record.reserved_quantity or 0.0
            record.free_quantity = inventory_quantity_auto_apply - reserved_quantity


