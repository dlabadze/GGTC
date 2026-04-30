from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment')