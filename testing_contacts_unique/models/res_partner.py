from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vat = fields.Char(string='Tax ID', required=True)

    _sql_constraints = [
        ('unique_vat', 'UNIQUE(vat)', 'The Tax ID must be unique.'),
    ]

    @api.constrains('vat')
    def _check_unique_vat(self):
        for partner in self:
            if partner.vat:
                existing = self.search([
                    ('vat', '=', partner.vat),
                    ('id', '!=', partner.id)
                ], limit=1)
                if existing:
                    raise ValidationError("The Tax ID must be unique.")