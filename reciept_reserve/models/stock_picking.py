from collections import defaultdict
from operator import truediv

from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    reserve_clicked = fields.Boolean(string='Reserve Clicked', default=False, copy=False)

    def action_receipt_reserve(self):

        if self.state != 'done':
            return True

        if self.picking_type_code != 'incoming':
            return True

        # Receipt destination location must match the internal transfer's source location (location_id).
        location_dest_id = self.location_dest_id
        if not self.move_ids:
            raise UserError(_("No moves found for this picking."))

        moves_to_reserve = self.move_ids.filtered('for_reserve')
        if not moves_to_reserve:
            raise UserError(
                _('Mark at least one line with "რეზერვისთვის" to run reserve.')
            )

        for move in moves_to_reserve:
            request = move.request_number
            quantity = move.quantity
            request = self.env['inventory.request'].search([
                ('x_studio_request_number', '=', request)
            ], limit=1)
            if not request:
                continue

            picking = self.env['stock.picking'].search([
                ('x_studio_request_ref', '=', request.id),
                ('location_id', '=', location_dest_id.id),
                ('picking_type_code', '=', 'internal'),
                ('state', '!=', 'done'),
            ], limit=1)

            if not picking:
                continue

            target_move = picking.move_ids.filtered(lambda m: m.product_id == move.product_id)[:1]
            if not target_move:
                continue

            new_quantity = target_move.quantity + quantity
            target_move.quantity = min(new_quantity, target_move.product_uom_qty)

        self.reserve_clicked = True
        return True