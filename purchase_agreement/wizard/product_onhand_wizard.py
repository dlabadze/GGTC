from odoo import models, fields, api

class ProductOnHandWizard(models.TransientModel):
    _name = 'product.onhand.wizard'
    _description = 'Product On Hand Wizard'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    onhand_lines = fields.One2many('product.onhand.wizard.line', 'wizard_id', string='On Hand Lines')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            line = self.env['inventory.line'].browse(active_id)
            res['product_id'] = line.product_id.id

            stock_quants = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
            ])

            lines_data = []
            for quant in stock_quants:
                lines_data.append((0, 0, {
                    'x_studio_location_id': quant.x_studio_location_id.id or False,
                    'location_id': quant.location_id.id,
                    'x_studio_product_reference': quant.x_studio_product_reference or '',
                    'product_id': line.product_id.id,
                    'inventory_quantity_auto_apply': quant.inventory_quantity_auto_apply or 0.0,
                    'reserved_quantity': quant.reserved_quantity or 0.0,
                    'product_uom_id': quant.product_uom_id.id,
                }))

            res['onhand_lines'] = lines_data

        return res
