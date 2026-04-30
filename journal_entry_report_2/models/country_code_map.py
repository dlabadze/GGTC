from odoo import models, fields, api


class CountryCodeMap(models.Model):
    _name = 'res.country.code.map.2'
    _description = 'Country Code Mapping'

    country_name = fields.Char(string='Country Name', required=True)
    country_code = fields.Char(string='Country Code', required=True)

    _sql_constraints = [
        ('country_unique', 'unique(country_name)', 'Country name must be unique!')
    ]

    @api.model
    def update_or_create_country_code(self, name, code):
        existing = self.search([('country_name', '=', name)], limit=1)
        if existing:
            existing.write({'country_code': code})
        else:
            self.create({'country_name': name, 'country_code': code})

