# # -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GenerateSaleReportWizard(models.TransientModel):
    _name = 'generate.sale.report.wizard'
    _description = 'Generate Sale Report Wizard'

    date_start = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today,
    )

    def _build_picking_invoice_maps(self, order_return_moves, order_out_moves, order_invoice_lines):
        """Build returned_qty, delivery_amount, returned_invoice_amount, cost maps keyed by (order_id, product_tmpl_id)."""
        returned_qty_map = {}
        delivery_amount_map = {}
        returned_invoice_amount_map = {}
        for order_id, return_moves in order_return_moves.items():
            for move in return_moves:
                if not move.product_id:
                    continue
                pt_id = move.product_id.product_tmpl_id.id
                key = (order_id, pt_id)
                returned_qty_map[key] = returned_qty_map.get(key, 0.0) + move.quantity
        for order_id, inv_lines in order_invoice_lines.items():
            for line in inv_lines:
                if not line.product_id:
                    continue
                pt_id = line.product_id.product_tmpl_id.id
                key = (order_id, pt_id)
                if line.move_id.move_type == 'out_invoice':
                    delivery_amount_map[key] = delivery_amount_map.get(key, 0.0) + (line.price_total or 0.0)
                elif line.move_id.move_type == 'out_refund':
                    refund = line.price_total or 0.0
                    returned_invoice_amount_map[key] = returned_invoice_amount_map.get(key, 0.0) + refund

        all_out_move_ids = []
        move_to_order_pt = {}
        for order_id, out_moves in order_out_moves.items():
            for move in out_moves:
                if move.product_id:
                    all_out_move_ids.append(move.id)
                    move_to_order_pt[move.id] = (order_id, move.product_id.product_tmpl_id.id)
        cost_map = {}
        cost_qty_map = {}
        if all_out_move_ids:
            valuations = self.env['stock.valuation.layer'].search([
                ('stock_move_id', 'in', all_out_move_ids),
            ])
            for val in valuations:
                key = move_to_order_pt.get(val.stock_move_id.id)
                if key and val.product_id and val.product_id.product_tmpl_id.id == key[1]:
                    cost_map[key] = cost_map.get(key, 0.0) + (val.value or 0.0)
                    cost_qty_map[key] = cost_qty_map.get(key, 0.0) + (val.quantity or 0.0)
            for k in cost_map:
                cost_map[k] = abs(cost_map[k])
        erteuli_cost_map = {}
        for k in cost_map:
            qty = cost_qty_map.get(k, 0.0)
            erteuli_cost_map[k] = abs(cost_map[k] / qty) if qty else 0.0
        return returned_qty_map, delivery_amount_map, returned_invoice_amount_map, cost_map, erteuli_cost_map

    def _build_picking_invoice_maps_by_sale_line(self, order_return_moves, order_out_moves, order_invoice_lines):
        """Build maps keyed by sale.order.line id (sale_line_id) for SO: account.move.line by sale_line_ids, stock.move by sale_line_id."""
        returned_qty_map = {}
        delivery_amount_map = {}
        returned_invoice_amount_map = {}
        for order_id, return_moves in order_return_moves.items():
            for move in return_moves:
                sol = getattr(move, 'sale_line_id', False)
                if not sol:
                    continue
                returned_qty_map[sol.id] = returned_qty_map.get(sol.id, 0.0) + move.quantity
        for order_id, inv_lines in order_invoice_lines.items():
            for line in inv_lines:
                for sol in (line.sale_line_ids or self.env['sale.order.line']):
                    if line.move_id.move_type == 'out_invoice':
                        delivery_amount_map[sol.id] = delivery_amount_map.get(sol.id, 0.0) + (line.price_total or 0.0)
                    elif line.move_id.move_type == 'out_refund':
                        refund = line.price_total or 0.0
                        returned_invoice_amount_map[sol.id] = returned_invoice_amount_map.get(sol.id, 0.0) + refund
        all_out_move_ids = []
        move_to_sol = {}
        for order_id, out_moves in order_out_moves.items():
            for move in out_moves:
                sol = getattr(move, 'sale_line_id', False)
                if sol:
                    all_out_move_ids.append(move.id)
                    move_to_sol[move.id] = sol.id
        cost_map = {}
        cost_qty_map = {}
        if all_out_move_ids:
            valuations = self.env['stock.valuation.layer'].search([
                ('stock_move_id', 'in', all_out_move_ids),
            ])
            for val in valuations:
                sol_id = move_to_sol.get(val.stock_move_id.id)
                if sol_id and val.product_id and val.stock_move_id.product_id.product_tmpl_id.id == val.product_id.product_tmpl_id.id:
                    cost_map[sol_id] = cost_map.get(sol_id, 0.0) + (val.value or 0.0)
                    cost_qty_map[sol_id] = cost_qty_map.get(sol_id, 0.0) + (val.quantity or 0.0)
            for k in cost_map:
                cost_map[k] = abs(cost_map[k])
        erteuli_cost_map = {}
        for k in cost_map:
            qty = cost_qty_map.get(k, 0.0)
            erteuli_cost_map[k] = abs(cost_map[k] / qty) if qty else 0.0
        return returned_qty_map, delivery_amount_map, returned_invoice_amount_map, cost_map, erteuli_cost_map

    def _fill_picking_and_invoice_fields(self, reports):
        """Fill returned_qty, delivery_amount, delivery_untaxed_amount, returned_invoice_amount, cost from sale order or POS order pickings and invoices."""
        if not reports:
            return
        report_table = reports._table

        # --- Sale order branch: same logic as before, keyed by sale_order_id ---
        reports_so = reports.filtered('sale_order_id')
        order_date_order = {}
        order_delivery_date = {}
        so_returned_qty_map = {}
        so_delivery_amount_map = {}
        so_returned_invoice_amount_map = {}
        so_cost_map = {}
        if reports_so:
            order_ids = list(set(reports_so.mapped('sale_order_id').ids))
            orders = self.env['sale.order'].browse(order_ids)
            order_date_order = {o.id: o.date_order for o in orders}
            order_delivery_date = {
                o.id: getattr(o, 'delivery_date', False)
                for o in orders
            }
            order_return_moves = {}
            order_out_moves = {}
            order_invoice_lines = {}
            for order in orders:
                return_pickings = order.picking_ids.filtered(lambda p: p.return_id)
                out_pickings = order.picking_ids.filtered(lambda p: not p.return_id)
                order_return_moves[order.id] = return_pickings.mapped('move_ids_without_package')
                order_out_moves[order.id] = out_pickings.mapped('move_ids_without_package')
                order_invoice_lines[order.id] = order.invoice_ids.mapped('invoice_line_ids')
            so_returned_qty_map, so_delivery_amount_map, so_returned_invoice_amount_map, so_cost_map, so_erteuli_cost_map = self._build_picking_invoice_maps_by_sale_line(
                order_return_moves, order_out_moves, order_invoice_lines
            )

        # --- POS order branch: same logic, pickings from pos_order_id (stock.picking linked via pos_order_id) ---
        reports_pos = reports.filtered('pos_order_id')
        pos_order_date_order = {}
        pos_order_delivery_date = {}
        pos_returned_qty_map = {}
        pos_delivery_amount_map = {}
        pos_returned_invoice_amount_map = {}
        pos_cost_map = {}
        if reports_pos:
            pos_order_ids = list(set(reports_pos.mapped('pos_order_id').ids))
            pos_orders = self.env['pos.order'].browse(pos_order_ids)
            pos_order_date_order = {o.id: o.date_order for o in pos_orders}
            # delivery_date: use first done picking's date_done or order date
            for o in pos_orders:
                done_pickings = o.picking_ids.filtered(lambda p: p.state == 'done')
                pos_order_delivery_date[o.id] = done_pickings[0].date_done if done_pickings else o.date_order
            order_return_moves = {}
            order_out_moves = {}
            order_invoice_lines = {}
            for order in pos_orders:
                return_pickings = order.picking_ids.filtered(lambda p: p.return_id)
                out_pickings = order.picking_ids.filtered(lambda p: not p.return_id)
                order_return_moves[order.id] = return_pickings.mapped('move_ids_without_package')
                order_out_moves[order.id] = out_pickings.mapped('move_ids_without_package')
                inv_lines = order.account_move.invoice_line_ids if order.account_move else self.env['account.move.line']
                order_invoice_lines[order.id] = inv_lines
            pos_returned_qty_map, pos_delivery_amount_map, pos_returned_invoice_amount_map, pos_cost_map, pos_erteuli_cost_map = self._build_picking_invoice_maps(
                order_return_moves, order_out_moves, order_invoice_lines
            )
            # Delivery quantity for POS: sum stock.move.quantity grouped by stock.move.pos_order_line_id
            pos_delivery_qty_by_line = {}
            for _order_id, out_moves in order_out_moves.items():
                for move in out_moves:
                    pol = getattr(move, 'pos_order_line_id', False)
                    if not pol:
                        continue
                    pos_delivery_qty_by_line[pol.id] = pos_delivery_qty_by_line.get(pol.id, 0.0) + move.quantity
            # Refunded quantity for POS: from pos.order.line.refunded_qty (computed: -sum(refund_orderline_ids.qty))
            pos_refunded_qty_by_line = {}
            pos_line_ids = list(set(reports_pos.mapped('pos_order_line_id').ids))
            if pos_line_ids:
                for line in self.env['pos.order.line'].browse(pos_line_ids):
                    pos_refunded_qty_by_line[line.id] = line.refunded_qty
        else:
            pos_delivery_qty_by_line = {}
            pos_refunded_qty_by_line = {}
            pos_erteuli_cost_map = {}

        # Build list of (report_id, vals) using SO or POS maps per record
        vals_list = []
        for rec in reports:
            if rec.sale_order_id:
                order_id = rec.sale_order_id.id
                date_order = order_date_order.get(order_id)
                delivery_date = order_delivery_date.get(order_id)
                returned_qty_map = so_returned_qty_map
                delivery_amount_map = so_delivery_amount_map
                returned_invoice_amount_map = so_returned_invoice_amount_map
                cost_map = so_cost_map
                erteuli_cost_map = so_erteuli_cost_map
            elif rec.pos_order_id:
                order_id = rec.pos_order_id.id
                date_order = pos_order_date_order.get(order_id)
                delivery_date = pos_order_delivery_date.get(order_id)
                returned_qty_map = pos_returned_qty_map
                delivery_amount_map = pos_delivery_amount_map
                returned_invoice_amount_map = pos_returned_invoice_amount_map
                cost_map = pos_cost_map
                erteuli_cost_map = pos_erteuli_cost_map
            else:
                vals_list.append((
                    rec.id, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                    False, False,
                    0.0, 0.0, 0.0,
                ))
                continue

            product_tmpl = rec.product_id
            if not product_tmpl:
                sale_delivery_qty = rec.sale_delivery_quantity if rec.sale_order_id else 0.0
                refunded_qty_val = 0.0
                vals_list.append((
                    rec.id, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                    date_order, delivery_date,
                    sale_delivery_qty, refunded_qty_val, 0.0,
                ))
                continue
            pt_id = product_tmpl.id
            # Sale orders: key by sale_order_line_id (account.move.line matched by sale_line_ids, stock.move by sale_line_id)
            # POS: key by (order_id, product_tmpl_id)
            if rec.sale_order_id and rec.sale_order_line_id:
                key = rec.sale_order_line_id.id
            else:
                key = (order_id, pt_id)
            returned_qty = returned_qty_map.get(key, 0.0)
            delivery_amount = delivery_amount_map.get(key, 0.0)
            delivery_untaxed_amount = delivery_amount / 1.18 if delivery_amount else 0.0
            refund_total = returned_invoice_amount_map.get(key, 0.0)
            returned_invoice_amount = -abs(refund_total) if refund_total else 0.0
            cost = cost_map.get(key, 0.0)
            erteuli_cost = erteuli_cost_map.get(key, 0.0)
            # BOM cost rollup only for POS (key is (order_id, pt_id)); SO uses sale_line_id key
            bom_ids = getattr(product_tmpl, 'bom_ids', None)
            bom = None
            if bom_ids and not rec.sale_order_id:
                bom = next(
                    (b for b in bom_ids if getattr(b, 'active', True) and b.bom_line_ids),
                    None,
                )
                if bom:
                    for bom_line in bom.bom_line_ids:
                        if bom_line.product_id:
                            comp_pt_id = bom_line.product_id.product_tmpl_id.id
                            cost += cost_map.get((order_id, comp_pt_id), 0.0)
            # sale_delivery_quantity: for SO keep value from INSERT (sol.qty_delivered); for POS = sum of move.quantity for stock.moves with same pos_order_line_id
            if rec.sale_order_id:
                sale_delivery_qty = rec.sale_delivery_quantity
                refunded_qty_val = 0.0
            else:
                pol_id = rec.pos_order_line_id.id if rec.pos_order_line_id else False
                sale_delivery_qty = pos_delivery_qty_by_line.get(pol_id, 0.0) if pol_id else 0.0
                refunded_qty_val = pos_refunded_qty_by_line.get(pol_id, 0.0) if pol_id else 0.0
                # For POS rows, returned_qty must be same as refunded_qty.
                returned_qty = refunded_qty_val
            # POS: when partner_id is false, delivery_amount = sale_price_total; returned_invoice_amount from pos.order.line refunded_qty
            if rec.pos_order_id:
                if not rec.partner_id:
                    delivery_amount = rec.sale_price_total
                    delivery_untaxed_amount = delivery_amount / 1.18 if delivery_amount else 0.0
                if rec.sale_quantity:
                    returned_invoice_amount = -(rec.sale_price_total * refunded_qty_val / rec.sale_quantity)
                else:
                    returned_invoice_amount = 0.0
            real_invoice_amount = delivery_amount + returned_invoice_amount
            real_invoice_untaxed_amount = real_invoice_amount / 1.18 if real_invoice_amount > 0 else 0.0
            earned_amount = real_invoice_untaxed_amount - ((sale_delivery_qty - returned_qty) * erteuli_cost)
            margin = (earned_amount / real_invoice_untaxed_amount) if (earned_amount > 0 and real_invoice_untaxed_amount) else 0.0
            vals_list.append((
                rec.id, returned_qty, delivery_amount, delivery_untaxed_amount, returned_invoice_amount, cost,
                real_invoice_amount, real_invoice_untaxed_amount, earned_amount, margin,
                date_order, delivery_date,
                sale_delivery_qty, refunded_qty_val, erteuli_cost,
            ))

        if not vals_list:
            return
        ids = [v[0] for v in vals_list]
        rqs = [v[1] for v in vals_list]
        das = [v[2] for v in vals_list]
        duas = [v[3] for v in vals_list]
        rias = [v[4] for v in vals_list]
        costs = [v[5] for v in vals_list]
        ria_real = [v[6] for v in vals_list]
        ria_untaxed = [v[7] for v in vals_list]
        earned = [v[8] for v in vals_list]
        margins = [v[9] for v in vals_list]
        date_orders = [v[10] for v in vals_list]
        delivery_dates = [v[11] for v in vals_list]
        sale_delivery_qtys = [v[12] for v in vals_list]
        refunded_qtys = [v[13] for v in vals_list]
        erteuli_costs = [v[14] for v in vals_list]
        self.env.cr.execute(
            f"""
            UPDATE {report_table} AS r SET
                returned_qty = sub.returned_qty,
                delivery_amount = sub.delivery_amount,
                delivery_untaxed_amount = sub.delivery_untaxed_amount,
                returned_invoice_amount = sub.returned_invoice_amount,
                cost = sub.cost,
                erteuli_cost = sub.erteuli_cost,
                real_invoice_amount = sub.real_invoice_amount,
                real_invoice_untaxed_amount = sub.real_invoice_untaxed_amount,
                earned_amount = sub.earned_amount,
                margin = sub.margin,
                date_order = sub.date_order,
                delivery_date = sub.delivery_date,
                sale_delivery_quantity = sub.sale_delivery_quantity,
                refunded_qty = sub.refunded_qty,
                write_uid = %s,
                write_date = NOW() AT TIME ZONE 'UTC'
            FROM (
                SELECT * FROM unnest(
                    %s::integer[],
                    %s::double precision[],
                    %s::double precision[],
                    %s::double precision[],
                    %s::double precision[],
                    %s::double precision[],
                    %s::double precision[],
                    %s::double precision[],
                    %s::double precision[],
                    %s::double precision[],
                    %s::timestamp[],
                    %s::timestamp[],
                    %s::double precision[],
                    %s::double precision[],
                    %s::double precision[]
                ) AS t(id, returned_qty, delivery_amount, delivery_untaxed_amount, returned_invoice_amount, cost, real_invoice_amount, real_invoice_untaxed_amount, earned_amount, margin, date_order, delivery_date, sale_delivery_quantity, refunded_qty, erteuli_cost)
            ) sub
            WHERE r.id = sub.id
            """,
            [self.env.uid, ids, rqs, das, duas, rias, costs, ria_real, ria_untaxed, earned, margins, date_orders, delivery_dates, sale_delivery_qtys, refunded_qtys, erteuli_costs],
        )
        reports.invalidate_recordset([
            'returned_qty', 'delivery_amount', 'delivery_untaxed_amount',
            'returned_invoice_amount', 'cost', 'erteuli_cost',
            'real_invoice_amount', 'real_invoice_untaxed_amount', 'earned_amount', 'margin',
            'date_order', 'delivery_date', 'sale_delivery_quantity', 'refunded_qty',
        ])

    def action_generate(self):
        self.ensure_one()
        if self.date_start > self.date_end:
            raise UserError(_('Start Date must be before End Date.'))

        Report = self.env['generated.sale.report']
        so_table = self.env['sale.order']._table
        sol_table = self.env['sale.order.line']._table
        po_table = self.env['pos.order']._table
        pol_table = self.env['pos.order.line']._table
        report_table = Report._table
        pt_table = self.env['product.template']._table
        partner_table = self.env['res.partner']._table

        # 1) Insert from sale_order_line joined to sale_order
        # Filter: date_order between start and end, only product lines (no section/note)
        # amount_until_discount: use price_unit * product_uom_qty (same as order line logic)
        # article_id, category_id, momwodebeli, volume from product; buyer_group, city_region from partner
        # sale_product_group_id from product.product (pp.product_group_id)
        # discount_percent, loyalty_program_id from line; discount_difference = amount_until_discount - price_total
        query = f"""
            INSERT INTO {report_table} (
                sale_order_id,
                sale_order_line_id,
                sale_status,
                partner_id,
                salesperson_id,
                product_id,
                sale_quantity,
                sale_delivery_quantity,
                sale_invoice_quantity,
                sale_packaging_quantity,
                sale_packaging_id,
                unit_price,
                sale_amount_until_discount,
                sale_price_total,
                sale_product_group_id,
                article_id,
                category_id,
                momwodebeli,
                volume,
                buyer_group,
                city_region,
                discount_percent,
                loyalty_program_id,
                discount_difference,
                create_uid,
                create_date,
                write_uid,
                write_date
            )
            SELECT
                sol.order_id,
                sol.id,
                so.state,
                so.partner_id,
                so.user_id,
                pp.product_tmpl_id,
                sol.product_uom_qty,
                sol.qty_delivered,
                sol.qty_invoiced,
                COALESCE(sol.product_packaging_qty, 0),
                sol.product_packaging_id,
                sol.price_unit,
                (sol.price_unit * sol.product_uom_qty),
                sol.price_total,
                pp.product_group_id,
                pp.article_id,
                pt.categ_id,
                pp.x_studio_char_field_6s1_1jd28btq1,
                pp.volume,
                rp.x_studio_selection_field_7uv_1iv0qtpkb,
                rp.x_studio_selection_field_2fn_1iv0pcsi9,
                sol.discount,
                sol.loyalty_program_id,
                (sol.price_unit * sol.product_uom_qty) - sol.price_total,
                %s,
                NOW() AT TIME ZONE 'UTC',
                %s,
                NOW() AT TIME ZONE 'UTC'
            FROM {sol_table} sol
            JOIN {so_table} so ON so.id = sol.order_id
            LEFT JOIN product_product pp ON pp.id = sol.product_id
            LEFT JOIN {pt_table} pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN {partner_table} rp ON rp.id = so.partner_id
            WHERE so.date_order::date >= %s
              AND so.date_order::date <= %s
              AND (sol.display_type IS NULL OR sol.display_type = '')
              AND sol.product_id IS NOT NULL
            RETURNING id
        """
        self.env.cr.execute(query, (
            self.env.uid,
            self.env.uid,
            self.date_start,
            self.date_end,
        ))
        report_ids = [r[0] for r in self.env.cr.fetchall()]

        # 2) Insert from pos_order_line joined to pos_order (date filter: pos.order.date_order)
        query_pos = f"""
            INSERT INTO {report_table} (
                pos_order_id,
                pos_order_line_id,
                pos_status,
                partner_id,
                salesperson_id,
                product_id,
                sale_quantity,
                sale_delivery_quantity,
                sale_invoice_quantity,
                sale_packaging_quantity,
                sale_packaging_id,
                unit_price,
                sale_amount_until_discount,
                sale_price_total,
                sale_product_group_id,
                article_id,
                category_id,
                momwodebeli,
                volume,
                buyer_group,
                city_region,
                discount_percent,
                loyalty_program_id,
                discount_difference,
                create_uid,
                create_date,
                write_uid,
                write_date
            )
            SELECT
                po.id,
                pol.id,
                po.state,
                po.partner_id,
                po.user_id,
                pp.product_tmpl_id,
                pol.qty,
                0,
                0,
                0,
                NULL,
                pol.price_unit,
                (pol.price_unit * pol.qty),
                pol.price_subtotal_incl,
                pp.product_group_id,
                pp.article_id,
                pt.categ_id,
                pp.x_studio_char_field_6s1_1jd28btq1,
                pp.volume,
                rp.x_studio_selection_field_7uv_1iv0qtpkb,
                rp.x_studio_selection_field_2fn_1iv0pcsi9,
                pol.discount,
                NULL,
                (pol.price_unit * pol.qty) - pol.price_subtotal_incl,
                %s,
                NOW() AT TIME ZONE 'UTC',
                %s,
                NOW() AT TIME ZONE 'UTC'
            FROM {pol_table} pol
            JOIN {po_table} po ON po.id = pol.order_id
            LEFT JOIN product_product pp ON pp.id = pol.product_id
            LEFT JOIN {pt_table} pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN {partner_table} rp ON rp.id = po.partner_id
            WHERE po.date_order::date >= %s
              AND po.date_order::date <= %s
              AND pol.product_id IS NOT NULL
              AND (po.name IS NULL OR po.name NOT LIKE %s)
            RETURNING id
        """
        self.env.cr.execute(query_pos, (
            self.env.uid,
            self.env.uid,
            self.date_start,
            self.date_end,
            '%REFUND%',
        ))
        report_ids.extend([r[0] for r in self.env.cr.fetchall()])

        Report.invalidate_model([
            'sale_order_id', 'sale_order_line_id', 'pos_order_id', 'pos_order_line_id', 'sale_status', 'pos_status', 'partner_id', 'salesperson_id', 'product_id', 'sale_delivery_quantity',
            'sale_invoice_quantity', 'sale_packaging_quantity',
            'sale_packaging_id', 'unit_price', 'sale_amount_until_discount',
            'sale_price_total', 'sale_product_group_id',
            'article_id', 'category_id', 'momwodebeli', 'volume',
            'buyer_group', 'city_region', 'discount_percent', 'loyalty_program_id',
            'discount_difference',
        ])

        if report_ids:
            self._fill_picking_and_invoice_fields(Report.browse(report_ids))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Report'),
            'res_model': 'generated.sale.report',
            'view_mode': 'list,pivot',
            'domain': [('id', 'in', report_ids)] if report_ids else [],
        }