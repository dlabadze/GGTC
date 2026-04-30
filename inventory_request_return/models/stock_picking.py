from odoo import models, api

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def action_create_returns(self):
        res = super().action_create_returns()
        if res and isinstance(res, dict):
            new_picking_id = res.get('res_id')
            if new_picking_id:
                new_picking = self.browse(new_picking_id)
                new_picking.user_id = self.env.user.id
        return res

    @api.model
    def action_create_returns_all(self):
        res = super().action_create_returns_all()
        if res and isinstance(res, dict):
            new_picking_id = res.get('res_id')
            if new_picking_id:
                new_picking = self.browse(new_picking_id)
                new_picking.user_id = self.env.user.id
        return res
