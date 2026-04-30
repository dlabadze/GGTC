from odoo import models, fields, api, _


class InventoryLine(models.Model):
    _inherit = 'inventory.line'

    shenishvna_for_print = fields.Char(string='სენიშვნა მიმდინარე საწყობისთვის', compute='_compute_shenishvna_for_print')

    def _compute_shenishvna_for_print(self):
        for rec in self:
            shenishvna = ""
            if rec.x_studio_warehouse:
                shenishvna += rec.x_studio_warehouse.display_name
            
            # if rec.x_studio_purchase and shenishvna != "":
            #     shenishvna += "|| შესასყიდი"
            # elif rec.x_studio_purchase and shenishvna == "":
            #     shenishvna += "შესასყიდი"
            if rec.x_studio_purchase:
                shenishvna = "შესასყიდი"
            # if rec.x_studio_boolean_field_3rt_1j82fv6ek and shenishvna != "":
            #     shenishvna += " || დასამზადებელი"
            # elif rec.x_studio_boolean_field_3rt_1j82fv6ek and shenishvna == "":
            #     shenishvna += "დასამზადებელი"
            if rec.x_studio_boolean_field_2bu_1j82g13ub:
                shenishvna = "გათვალისწინებული"

            if rec.x_studio_boolean_field_3rt_1j82fv6ek:
                shenishvna = "დასამზადებელი"


            rec.shenishvna_for_print = shenishvna