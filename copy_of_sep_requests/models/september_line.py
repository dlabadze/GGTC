from odoo import models, fields, api


class SeptemberRequest(models.Model):
    _inherit = "september.line"

    x_studio_related_field_1pq_1j2ffqufh = fields.Char(
        string="Internal Reference",
        related="product_id.default_code",
        store=True,
        readonly=True,
    )