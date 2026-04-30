from ast import literal_eval

from odoo import models, fields, api

class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    enable_auto_logic = fields.Boolean(default=True)


    @api.onchange('line_ids')
    def _onchange_lines(self):
        warehouse_1 = self.env['stock.location'].search([('location_id.name','=','ცენტრალური საწყობი')], limit=1)
        warehouse_2 = self.env['stock.location'].search([('x_unique_location_id', '=','00003')],limit=1)
        for line in self.line_ids:
            if (line.x_studio_purchase or line.x_studio_boolean_field_2bu_1j82g13ub) and not line.x_studio_warehouse and warehouse_1:
                line.x_studio_warehouse = warehouse_1.id
            elif line.x_studio_boolean_field_3rt_1j82fv6ek and not line.x_studio_warehouse and warehouse_2:
                line.x_studio_warehouse = warehouse_2.id

    def write(self, vals):
        res = super().write(vals)
        self._apply_auto_logic()
        return res

    def _apply_auto_logic(self):
        warehouse_1 = self.env['stock.location'].search([('location_id.name','=','ცენტრალური საწყობი')], limit=1)
        warehouse_2 = self.env['stock.location'].search([('x_unique_location_id', '=','00003')],limit=1)

        for rec in self:
            for line in rec.line_ids:
                if (line.x_studio_purchase or line.x_studio_boolean_field_2bu_1j82g13ub) and not line.x_studio_warehouse and warehouse_1:
                    line.x_studio_warehouse = warehouse_1.id
                elif line.x_studio_boolean_field_3rt_1j82fv6ek and not line.x_studio_warehouse and warehouse_2:
                    line.x_studio_warehouse = warehouse_2.id



