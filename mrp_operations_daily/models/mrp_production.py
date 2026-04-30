from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    product_code = fields.Char(string='Product Code', index=True)

