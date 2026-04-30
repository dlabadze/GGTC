from odoo import models, fields, api
from odoo.exceptions import UserError

class InventoryLine(models.Model):
    _inherit = 'inventory.line'


    # readonly_warehouse = fields.Boolean(string="Readonly Warehouse")
    #
    # @api.onchange('x_studio_purchase')
    # def _compute_readonly_warehouse(self):
    #     for line in self:
    #         if line.request_id.enable_auto_logic:
    #             line.readonly_warehouse = (
    #                 line.request_id.enable_auto_logic and line.x_studio_purchase
    #             )

    # @api.onchange('x_studio_purchase')
    # def _onchange_lines(self):
    #     warehouse = self.env['stock.location'].search([('location_id.name','=','ცენტრალური საწყობი')], limit=1)
    #     for line in self:
    #         if line.x_studio_purchase and not line.x_studio_warehouse:
    #             line.x_studio_warehouse = warehouse.id



