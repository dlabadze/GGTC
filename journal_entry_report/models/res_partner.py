from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_studio_checkbox = fields.Boolean(string="Checkbox")
    x_studio_start_date_1 = fields.Date(string="Start Date")
    x_studio_shegavati = fields.Float(string="Shegavati")