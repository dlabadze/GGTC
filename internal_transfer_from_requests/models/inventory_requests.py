from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class InventoryRequests(models.Model):
    _inherit = 'inventory.request'


    internal_transfer_ids = fields.One2many(
        'stock.picking',
        'x_studio_request_ref',
        string='Internal Transfers'
    )

    internal_transfer_count = fields.Integer(
        string='Transfer Count',
        compute='_compute_internal_transfer_count'
    )

    manufacturing_ids = fields.One2many(
        'mrp.production',
        'inventory_request_id',
        string='Manufacturing Orders'
    )

    manufacturing_count = fields.Integer(
        compute='_compute_manufacturing_count',
        string='Manufacturing Orders'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    is_tag_ids_invisible = fields.Boolean(
        string='Is Tag Ids Invisible',
        default=False
    )
    mrp_production_id = fields.Many2one(
        'mrp.production',
    )
    line_ids = fields.One2many(
        'inventory.line',
        'request_id',
        default=lambda self: self._default_line_ids()
    )

    @api.model
    def _default_line_ids(self):
        line_vals = []
        
        # Get mrp_production_id from context
        mrp_production_id = self.env.context.get('default_mrp_production_id')
        
        if mrp_production_id:
            mrp_production = self.env['mrp.production'].browse(mrp_production_id)
            
            if mrp_production.exists():
                _logger.info(f"Creating lines from MRP Production: {mrp_production.name}")
                if mrp_production.move_raw_ids:
                    for move in mrp_production.move_raw_ids:
                        line_vals.append((0, 0, {
                            'product_id': move.product_id.id,
                            'uom_id': move.product_uom.id,
                            'quantity': move.product_uom_qty,
                        }))        
        return line_vals


    @api.depends('manufacturing_ids')
    def _compute_manufacturing_count(self):
        for rec in self:
            rec.manufacturing_count = len(rec.manufacturing_ids)

    @api.depends('internal_transfer_ids')
    def _compute_internal_transfer_count(self):
        for record in self:
            record.internal_transfer_count = len(record.internal_transfer_ids)

    # MAIN ACTION

    def action_generate_internal_transfers(self):
        for record in self:
            record._generate_internal_transfers()
            record._generate_manufacturing_orders()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Internal transfers and manufacturing orders generated successfully'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_delete_internal_transfers(self):
        for record in self:
            transfers = record.internal_transfer_ids
            if not transfers:
                continue
            to_delete = transfers.filtered(lambda p: p.state in ['draft', 'cancel','waiting','confirmed','assigned'])
            forbidden = transfers.filtered(lambda p: p.state not in ['draft', 'cancel','waiting','confirmed','assigned'])

            if forbidden:
                _logger.warning(
                    f"Some transfers for {record.name} were not deleted because they are already processed.")

            if to_delete:
                to_delete.unlink()
                _logger.info(f"Deleted {len(to_delete)} transfers for request {record.name}")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Eligible internal transfers have been deleted.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _generate_internal_transfers(self):
        self.ensure_one()

        if not self.line_ids:
            raise UserError(_('No request lines found to process'))

        user_location = self.x_studio_many2one_field_49t_1j431uvkl
        if not user_location:
            raise UserError(_('User location not configured'))

        # 1. Get the Specific Mechanical Workshop Location
        mech_workshop = self.env['stock.location'].search([
            ('name', '=', 'გ. ბიწაძე (მექანიკური საამქრო)')
        ], limit=1)
        if not mech_workshop:
            raise UserError(_('Mechanical Workshop location not found!'))

        parent_location = user_location.location_id
        scrap_location = self.env['stock.location'].search([
            ('scrap_location', '=', True),
            ('company_id', 'in', [False, self.env.company.id])
        ], limit=1)

        picking_type = self._get_internal_picking_type()
        transfer_map = defaultdict(list)

        for line in self.line_ids:
            warehouse_loc = line.x_studio_warehouse
            
            # --- LEG 1: Mech Workshop to line.x_studio_warehouse ---
            if line.x_studio_boolean_field_3rt_1j82fv6ek:
                if mech_workshop.id != warehouse_loc.id:
                    transfer_map[(mech_workshop.id, warehouse_loc.id)].append(line)

            # --- LEG 2: Warehouse to Parent Location ---
            if warehouse_loc.id != parent_location.id:
                transfer_map[(warehouse_loc.id, parent_location.id)].append(line)
            
            # --- LEG 3: Parent Location to User Location ---
            if parent_location.id != user_location.id:
                transfer_map[(parent_location.id, user_location.id)].append(line)
            
            # --- LEG 4: User Location to Scrap ---
            if not self.mrp_production_id.id and user_location.id != scrap_location.id:
                transfer_map[(user_location.id, scrap_location.id)].append(line)

        created_transfer_records = []

        for (source_id, dest_id), lines in transfer_map.items():
            move_lines = self._prepare_move_lines(
                lines,
                self.env['stock.location'].browse(source_id),
                self.env['stock.location'].browse(dest_id)
            )

            existing_transfer = self.env['stock.picking'].search([
                ('x_studio_request_ref', '=', self.id),
                ('location_id', '=', source_id),
                ('location_dest_id', '=', dest_id),
                ('state', 'not in', ['done', 'cancel']),
            ], limit=1)

            if existing_transfer:
                if not existing_transfer.move_ids:
                    for move_line_cmd in move_lines:
                        move_line_cmd[2]['picking_id'] = existing_transfer.id
                        self.env['stock.move'].create(move_line_cmd[2])

                    existing_transfer.write({
                        'scheduled_date': fields.Datetime.to_datetime(self.request_date),
                        'origin': self.name,
                        'comment': self.description,
                    })
                    existing_transfer.action_confirm()

                transfer = existing_transfer
                _logger.info(f"Reusing existing transfer {transfer.name} for {source_id} -> {dest_id}")

            else:
                transfer = self.env['stock.picking'].create({
                    'company_id': self.env.company.id,
                    'picking_type_id': picking_type.id,
                    'scheduled_date': fields.Datetime.to_datetime(self.request_date),
                    'move_type': 'one',
                    'location_id': source_id,
                    'location_dest_id': dest_id,
                    'move_ids': move_lines,
                    'x_studio_request_ref': self.id,
                    'origin': self.name,
                    'comment': self.description,
                })
                transfer.action_confirm()

            prod_data = defaultdict(lambda: {'total_qty': 0.0, 'deduct_qty': 0.0})
            for line in lines:
                prod_id = line.product_id.id
                prod_data[prod_id]['total_qty'] += line.quantity

                is_purchase_mrp = line.x_studio_purchase or line.x_studio_boolean_field_3rt_1j82fv6ek or line.x_studio_boolean_field_2bu_1j82g13ub
                is_transit_leg = source_id != line.x_studio_warehouse.id

                if is_purchase_mrp or is_transit_leg:
                    prod_data[prod_id]['deduct_qty'] += line.quantity

            for move in transfer.move_ids:
                data = prod_data.get(move.product_id.id)
                if not data:
                    continue

                current_move_qty = move.product_uom_qty
                reduction_amount = data['deduct_qty']
                new_target_qty = max(0.0, current_move_qty - reduction_amount)
                move._do_unreserve()
                _logger.info(f"Setting {move.product_id.name}: {current_move_qty} -> {new_target_qty}")
                move.write({'quantity': new_target_qty})

            for line in lines:
                line.transfer_ids = [(4, transfer.id)]
            created_transfer_records.append(transfer)

        return [t.id for t in created_transfer_records]

    # MOVE LINES
    def _prepare_move_lines(self, lines, source_location, dest_location):
        move_lines = []

        for line in lines:
            qty = line.quantity
            if line.x_studio_purchase or line.x_studio_boolean_field_3rt_1j82fv6ek or line.x_studio_boolean_field_2bu_1j82g13ub:
                qty = 0.0

            if line.quantity <= 0:
                continue


            move_line_data = {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'company_id': self.env.company.id,
                'state': 'draft',
                'origin': self.name,
                'x_studio_': self.x_studio_request_number,
            }

            move_lines.append((0, 0, move_line_data))

        return move_lines

    def _get_internal_picking_type(self):
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not picking_type:
            raise UserError(_('Internal picking type not found'))

        return picking_type

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def action_show_internal_transfers(self):
        self.ensure_one()
        return {
            'name': 'Internal Transfers',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.internal_transfer_ids.ids)],
            'target': 'current',
        }

    def action_view_internal_transfers(self):
        self.ensure_one()

        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        if len(self.internal_transfer_ids) > 1:
            action['domain'] = [('id', 'in', self.internal_transfer_ids.ids)]
        elif self.internal_transfer_ids:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = self.internal_transfer_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        action['context'] = dict(self._context, default_origin=self.name)
        return action

    # MANUFACTURED ONLY
    def _generate_manufacturing_orders(self):
        MrpProduction = self.env['mrp.production']
        location = self.env['stock.location'].search([('name','=','გ. ბიწაძე (მექანიკური საამქრო)')], limit=1)

        for request in self:
            manufacturing_lines = request.line_ids.filtered(
                lambda l: l.x_studio_boolean_field_3rt_1j82fv6ek
            )

            for line in manufacturing_lines:
                exists = MrpProduction.search_count([
                    ('inventory_request_id', '=', request.id),
                    ('product_id', '=', line.product_id.id),
                ])

                if exists:
                    continue

                MrpProduction.create({
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'product_uom_id': line.uom_id.id,
                    'origin': request.name,
                    'inventory_request_id': request.id,
                    'company_id': request.company_id.id,
                    'location_src_id': location.id if location else False,
                    'location_dest_id': location.id if location else False,
                })

