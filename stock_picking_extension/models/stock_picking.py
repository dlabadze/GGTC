from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    location_desk_id = fields.Many2one('stock.location', string='Location Desk')

    @api.model_create_multi
    def create(self, vals_list):
        """Override create method"""
        res = super(StockPicking, self).create(vals_list)
        for picking in res:
            if picking.x_studio_related_field_2sg_1j7espk8g and picking.x_studio_related_field_2sg_1j7espk8g not in picking.name:
                picking.name += f" | {picking.x_studio_related_field_2sg_1j7espk8g}"
        return res

    def write(self, vals):
        """Override write method"""
        res = super(StockPicking, self).write(vals)
        for picking in self:
            if picking.x_studio_related_field_2sg_1j7espk8g:
                if picking.x_studio_related_field_2sg_1j7espk8g not in picking.name:
                    if " | " in picking.name:
                        base_name = picking.name.split(" | ")[0]
                        picking.name = f"{base_name} | {picking.x_studio_related_field_2sg_1j7espk8g}"
                    else:
                        picking.name += f" | {picking.x_studio_related_field_2sg_1j7espk8g}"
            else:
                if " | " in picking.name:
                    picking.name = picking.name.split(" | ")[0]
        return res

    def action_confirm(self):
        """Override action_confirm to prevent merging moves for specific picking types"""
        self._check_company()
        self.mapped('package_level_ids').filtered(lambda pl: pl.state == 'draft' and not pl.move_ids)._generate_moves()

        for picking in self:
            if picking.picking_type_id and picking.picking_type_id.name in ["ოდორანტის ჩამოწერა", "მეორადი საბურავის მიღება", "იმპორტის ოპერაცია"]:
                picking.move_ids.filtered(lambda move: move.state == 'draft')._action_confirm(merge=False)
            else:
                picking.move_ids.filtered(lambda move: move.state == 'draft')._action_confirm()

        self.move_ids.filtered(lambda move: move.state not in ('draft', 'cancel', 'done'))._trigger_scheduler()
        return True
