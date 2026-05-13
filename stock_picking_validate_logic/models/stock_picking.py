import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    def button_validate(self):
        draft_pickings = self.filtered(lambda p: p.state == 'draft')
        if draft_pickings:
            draft_pickings.action_confirm()
            for picking in draft_pickings:
                if picking.x_studio_request_ref:

                    picking.move_ids.picked = True

        all_products = self.move_ids.mapped('product_id')
        all_locations = self.move_ids.mapped('location_id')
        current_refs = self.mapped('x_studio_request_ref').filtered(lambda r: r)
        
        if current_refs:
            ref_ids = current_refs.ids if hasattr(current_refs, 'ids') else [r.id if hasattr(r, 'id') else r for r in current_refs]
            
            other_pickings = self.env['stock.picking'].search([
                ('state', 'in', ('confirmed', 'assigned')),
                ('id', 'not in', self.ids),
                '|', ('x_studio_request_ref', 'not in', ref_ids),
                     ('x_studio_request_ref', '=', False)
            ])

            for other_p in other_pickings:
                moves_to_free = other_p.move_ids.filtered(
                    lambda m: m.product_id in all_products and m.location_id in all_locations and m.state in ('confirmed', 'assigned')
                )
                if moves_to_free:
                    _logger.info("Unreserving stock from unrelated picking %s for request weights %s", other_p.name, ref_ids)
                    moves_to_free._do_unreserve()

        is_nashti_control = self.env['ir.config_parameter'].sudo().get_param('stock_picking_validate_logic.nashti_control') == 'True'

        for picking in self:
            if picking.state in ('done', 'cancel'):
                continue

            if is_nashti_control:
                requirements = {}
                for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                    key = (move.product_id, move.location_id)
                    if key not in requirements:
                        requirements[key] = 0.0
                    requirements[key] += move.quantity
                for (product, location), required_qty in requirements.items():
                    if required_qty <= 0:
                        continue
    
                    if location.usage != 'internal':
                        continue
    
                    quants = self.env['stock.quant'].search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', location.id), 
                    ])
                    free_qty = sum(quants.mapped('inventory_quantity_auto_apply'))
    
                    if required_qty > free_qty:
                        raise UserError(_(
                            "Insufficient stock for product '%s' in location '%s'.\n"
                            "Free quantity in stock: %s\n"
                            "Trying to take: %s"
                        ) % (product.display_name, location.display_name, free_qty, required_qty))

        res = super(StockPicking, self).button_validate()

        validated_pickings = self.filtered(lambda p: p.state == 'done')

        for picking in validated_pickings:
            request_ref = picking.x_studio_request_ref
            if not request_ref:
                continue

            ref_value = request_ref.id if hasattr(request_ref, 'id') else request_ref

            related_pickings = self.env['stock.picking'].search([
                ('x_studio_request_ref', '=', ref_value),
                ('location_id', '=', picking.location_dest_id.id),
                ('state', 'not in', ('done', 'cancel')),
                ('id', '!=', picking.id),
                ('backorder_id', '=', False),
            ])

            if not related_pickings:
                continue

            for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
                qty_to_propagate = move.quantity
                if qty_to_propagate <= 0:
                    continue

                related_moves = related_pickings.move_ids.filtered(
                    lambda m: m.product_id == move.product_id and m.state not in ('done', 'cancel')
                )

                for rel_move in related_moves:
                    if qty_to_propagate <= 0:
                        break

                    can_add = rel_move.product_uom_qty - rel_move.quantity
                    if can_add > 0:
                        added = min(qty_to_propagate, can_add)
                        rel_move.quantity += added
                        rel_move.picked = True
                        qty_to_propagate -= added

        return res

    def action_confirm(self):
        res = super(StockPicking, self).action_confirm()
        for picking in self:
            if picking.x_studio_request_ref:
                picking.move_ids.write({'quantity': 0, 'picked': False})
                picking.move_line_ids.write({'quantity': 0, 'picked': False})
        return res

    def _create_backorder(self):
        backorders = super()._create_backorder()

        for backorder in backorders:
            if not backorder.x_studio_request_ref:
                continue

            backorder.move_ids.write({'quantity': 0, 'picked': False})
            backorder.move_line_ids.write({'quantity': 0, 'picked': False})

        return backorders