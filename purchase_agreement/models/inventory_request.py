from odoo import models, fields, api

class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    preiskuranti_id = fields.Integer(string="preiskuranti")