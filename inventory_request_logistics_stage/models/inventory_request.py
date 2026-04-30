from odoo import models, _
from odoo.exceptions import UserError


class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    def write(self, vals):
        # Remember which records are in old stage before write (super changes stage_id)
        records_to_check = self.env['inventory.request']
        if 'stage_id' in vals:
            new_stage = self.env['inventory.request.stage'].browse(vals['stage_id'])
            old_stage_name = 'სასაწყობე მეურ. სამმ.'
            new_stage_name = 'ლოგისტიკის დეპარტამენტი'
            if new_stage.name == new_stage_name:
                records_to_check = self.filtered(
                    lambda r: r.stage_id and r.stage_id.name == old_stage_name
                )

        result = super(InventoryRequest, self).write(vals)

        for record in records_to_check:
            purchase_lines = record.line_ids.filtered(
                lambda l: getattr(l, 'x_studio_purchase', False)
            )
            # purchase_lines.amount = 1
            purchase_lines.amount = 0.0
            purchase_lines.unit_price = 0.0
            # raise UserError(purchase_lines.mapped('amount'))

        return result
