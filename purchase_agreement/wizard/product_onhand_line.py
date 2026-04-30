from odoo import models, fields, api

class ProductOnhandLine(models.TransientModel):
    _name = 'product.onhand.line'
    _description = 'On Hand Stock Line'

    wizard_id = fields.Many2one('product.onhand.wizard')
    x_studio_location_id = fields.Char( string='Studio Location ID')
    location_id = fields.Many2one('stock.location', string='Location')
    x_studio_product_reference = fields.Char(string='Product Reference')
    product_id = fields.Many2one('product.product', string='Product')
    inventory_quantity_auto_apply = fields.Float(string='Inventory Quantity')
    reserved_quantity = fields.Float(string='Reserved Quantity')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')