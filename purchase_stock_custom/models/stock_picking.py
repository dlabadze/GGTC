from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_transfer_info = fields.Char(string='ხელშეკრულების ნომერი')
