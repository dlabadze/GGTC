# -*- coding: utf-8 -*-

from odoo import fields, models


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    dv_fix_valuation_to_standard_price = fields.Boolean(
        string="Fix valuation to Standard Price",
        help="When enabled, this scrap's stock valuation and accounting entries will be adjusted "
        "so that valuation equals product Standard Price × quantity.",
        copy=False,
    )

    def action_dv_apply_standard_price_valuation_fix(self):
        for scrap in self:
            scrap.dv_fix_valuation_to_standard_price = True
            if scrap.state == "done":
                scrap.move_ids._dv_fix_valuation_to_standard_price()
        return True

