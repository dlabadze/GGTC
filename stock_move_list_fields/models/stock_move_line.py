from odoo import models, fields, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    x_studio_request_number = fields.Char(
        string="Request Number",
        compute="_compute_inventory_request_data",
        store=True
    )

    request_date = fields.Date(
        string="Request Date",
        compute="_compute_inventory_request_data",
        store=True
    )
    request_manual_num = fields.Char(
        string="Picking Manual Number",
        compute="_compute_inventory_manual_num",
        store=True,
    )

    @api.depends('inventory_request_id.x_studio_request_number',
                 'inventory_request_id.request_date')
    def _compute_inventory_request_data(self):
        for line in self:
            request = line.inventory_request_id
            if request:
                line.x_studio_request_number = request.x_studio_request_number
                line.request_date = request.request_date
            else:
                line.x_studio_request_number = False
                line.request_date = False

    @api.depends('picking_id.x_request_number_manual')
    def _compute_inventory_manual_num(self):
        for line in self:
            picking = line.picking_id
            if picking:
                line.request_manual_num = picking.x_request_number_manual
            else:
                line.request_manual_num = False
