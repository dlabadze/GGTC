# -*- coding: utf-8 -*-

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    dv_fix_valuation_to_standard_price = fields.Boolean(
        string="Fix valuation to Standard Price",
        help="When enabled, this picking's stock valuation and accounting entries will be adjusted "
        "so that valuation equals product Standard Price × quantity for each outgoing move.",
        copy=False,
    )

    def action_dv_apply_standard_price_valuation_fix(self):
        for picking in self:
            picking.dv_fix_valuation_to_standard_price = True
            if picking.state == "done":
                picking.move_ids._dv_fix_valuation_to_standard_price()
        return True

