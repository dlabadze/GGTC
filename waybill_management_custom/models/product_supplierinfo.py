from odoo import models, fields

class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    koef = fields.Float(string='Coefficient', default=1.0, help="Coefficient for unit conversion")
