from odoo import models, fields, api

class Partner(models.Model):
    _inherit = "res.partner"

    shegavati_1 = fields.Float(string="შეღავათი")

