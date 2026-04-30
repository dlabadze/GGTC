from odoo import fields,models

class InventoryLine(models.Model):
    _inherit = "inventory.line"

    transfer_ids = fields.Many2many(
        'stock.picking',
        'stock_picking_request_line_rel',
        'request_line_id',
        'picking_id',
        string="Transfers",
        readonly=True,
    )