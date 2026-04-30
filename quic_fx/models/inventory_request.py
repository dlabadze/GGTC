from odoo import models, fields, api

class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    enable_auto_logic = fields.Boolean(default=True)
    files = fields.Binary(string='files')