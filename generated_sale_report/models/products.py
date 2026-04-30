from odoo import models, fields, api, _


class Products(models.Model):
    _inherit = 'product.product'

    litri = fields.Float(
        string='ლიტრი',
        related='product_tmpl_id.litri',
        readonly=False,
        store=True,
    )
    supplier_id = fields.Many2one(
        'suppliers',
        string='მომწოდებელი',
        related='product_tmpl_id.supplier_id',
        readonly=False,
        store=True,
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    litri = fields.Float(string='ლიტრი')
    supplier_id = fields.Many2one(
        'suppliers',
        string='მომწოდებელი',
    )
