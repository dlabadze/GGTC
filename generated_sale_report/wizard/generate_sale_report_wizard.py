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

    def _fill_picking_and_invoice_fields(self, reports):
        """Fill all financial/delivery fields via bulk SQL — no Python loops over records."""
        if not reports:
            return

        report_table = reports._table
        uid = self.env.uid
        report_ids = reports.ids

        # ============================================================
        # SALE ORDER UPDATE  (keyed by sale_order_line_id)
        # ============================================================
        self.env.cr.execute(f"""
            UPDATE {report_table} r
            SET
                date_order                  = so.date_order,
                delivery_date               = first_pick.date_done,
                returned_qty                = COALESCE(ret.qty,       0.0),
                refunded_qty                = 0.0,
                sale_delivery_quantity      = COALESCE(dqty.qty,      r.sale_delivery_quantity),
                cost                        = COALESCE(ABS(svl.total_cost), 0.0),
                erteuli_cost                = CASE
                                                WHEN COALESCE(svl.total_qty, 0) > 0
                                                THEN ABS(svl.total_cost) / svl.total_qty
                                                ELSE 0.0
                                              END,
                delivery_amount             = COALESCE(inv.delivered, 0.0),
                delivery_untaxed_amount     = COALESCE(inv.delivered, 0.0) / 1.18,
                returned_invoice_amount     = -ABS(COALESCE(inv.refunded, 0.0)),
                real_invoice_amount         = COALESCE(inv.delivered, 0.0)
                                              - ABS(COALESCE(inv.refunded, 0.0)),
                real_invoice_untaxed_amount = CASE
                                                WHEN COALESCE(inv.delivered, 0.0) - ABS(COALESCE(inv.refunded, 0.0)) > 0
                                                THEN (COALESCE(inv.delivered, 0.0) - ABS(COALESCE(inv.refunded, 0.0))) / 1.18
                                                ELSE 0.0
                                              END,
                write_uid                   = {uid},
                write_date                  = NOW() AT TIME ZONE 'UTC'
            FROM {report_table} rr
            JOIN sale_order so           ON so.id  = rr.sale_order_id
            JOIN sale_order_line sol     ON sol.id = rr.sale_order_line_id

            -- first outgoing delivery date
            LEFT JOIN LATERAL (
                SELECT MIN(sp.date_done) AS date_done
                FROM   stock_picking sp
                JOIN   stock_picking_type spt ON spt.id = sp.picking_type_id
                WHERE  sp.sale_id             = so.id
                  AND  sp.state               = 'done'
                  AND  spt.code               = 'outgoing'
                  AND  sp.return_id           IS NULL
                  AND  sp.date_done           IS NOT NULL
            ) first_pick ON TRUE

            -- returned qty (return pickings, same sale line)
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(sm.quantity), 0.0) AS qty
                FROM   stock_move    sm
                JOIN   stock_picking sp ON sp.id = sm.picking_id
                WHERE  sp.sale_id       = so.id
                  AND  sp.return_id     IS NOT NULL
                  AND  sm.sale_line_id  = sol.id
            ) ret ON TRUE

            -- delivered qty override for BOM lines (sum component moves)
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(sm.quantity), 0.0) AS qty
                FROM   stock_move    sm
                JOIN   stock_picking sp ON sp.id = sm.picking_id
                -- only pick up when a BoM exists; otherwise keep sol.qty_delivered
                WHERE  sp.sale_id      = so.id
                  AND  sp.return_id    IS NULL
                  AND  sm.sale_line_id = sol.id
                  AND  EXISTS (
                      SELECT 1 FROM mrp_bom mb
                      JOIN   product_template pt ON pt.id = mb.product_tmpl_id
                      JOIN   product_product  pp ON pp.product_tmpl_id = pt.id
                      WHERE  pp.id = sol.product_id
                        AND  mb.active = TRUE
                  )
            ) dqty ON TRUE

            -- stock valuation cost (out moves, same sale line)
            LEFT JOIN LATERAL (
                SELECT
                    ABS(SUM(svl.value))    AS total_cost,
                    ABS(SUM(svl.quantity)) AS total_qty
                FROM   stock_valuation_layer svl
                JOIN   stock_move    sm ON sm.id = svl.stock_move_id
                JOIN   stock_picking sp ON sp.id = sm.picking_id
                WHERE  sp.sale_id      = so.id
                  AND  sp.return_id    IS NULL
                  AND  sm.sale_line_id = sol.id
            ) svl ON TRUE

            -- invoiced / refunded totals (linked via sale_order_line_invoice_rel)
            LEFT JOIN LATERAL (
                SELECT
                    SUM(CASE WHEN am.move_type = 'out_invoice' THEN aml.price_total ELSE 0 END) AS delivered,
                    SUM(CASE WHEN am.move_type = 'out_refund'  THEN aml.price_total ELSE 0 END) AS refunded
                FROM   account_move_line          aml
                JOIN   account_move               am  ON am.id  = aml.move_id
                JOIN   sale_order_line_invoice_rel rel ON rel.invoice_line_id = aml.id
                WHERE  rel.order_line_id = sol.id
                  AND  am.move_type IN ('out_invoice', 'out_refund')
            ) inv ON TRUE

            WHERE rr.sale_order_id IS NOT NULL
              AND rr.id = ANY(%s)
              AND r.id  = rr.id
        """, (report_ids,))

        # ============================================================
        # POS ORDER UPDATE  (keyed by pos_order_line_id)
        # ============================================================
        self.env.cr.execute(f"""
            UPDATE {report_table} r
            SET
                date_order                  = po.date_order,
                delivery_date               = first_pick.date_done,
                returned_qty                = COALESCE(ABS(pol_refund.qty), 0.0),
                refunded_qty                = COALESCE(ABS(pol_refund.qty), 0.0),
                sale_delivery_quantity      = COALESCE(dqty.qty, 0.0),
                cost                        = COALESCE(ABS(svl.total_cost), 0.0),
                erteuli_cost                = CASE
                                                WHEN COALESCE(svl.total_qty, 0) > 0
                                                THEN ABS(svl.total_cost) / svl.total_qty
                                                ELSE 0.0
                                              END,
                delivery_amount             = CASE
                                                WHEN po.partner_id IS NULL THEN rr.sale_price_total
                                                ELSE COALESCE(inv.delivered, 0.0)
                                              END,
                delivery_untaxed_amount     = CASE
                                                WHEN po.partner_id IS NULL
                                                THEN rr.sale_price_total / 1.18
                                                ELSE COALESCE(inv.delivered, 0.0) / 1.18
                                              END,
                returned_invoice_amount     = CASE
                                                WHEN COALESCE(rr.sale_quantity, 0) > 0
                                                THEN -(rr.sale_price_total
                                                       * ABS(COALESCE(pol_refund.qty, 0.0))
                                                       / rr.sale_quantity)
                                                ELSE 0.0
                                              END,
                write_uid                   = {uid},
                write_date                  = NOW() AT TIME ZONE 'UTC'
            FROM {report_table} rr
            JOIN pos_order      po  ON po.id  = rr.pos_order_id
            JOIN pos_order_line pol ON pol.id = rr.pos_order_line_id

            -- refunded_qty is computed on pos.order.line; mirror _compute_refund_qty in SQL
            LEFT JOIN LATERAL (
                SELECT COALESCE(-SUM(ref_pol.qty), 0.0) AS qty
                FROM   pos_order_line ref_pol
                JOIN   pos_order po_ref ON po_ref.id = ref_pol.order_id
                WHERE  ref_pol.refunded_orderline_id = pol.id
                  AND  po_ref.state <> 'cancel'
            ) pol_refund ON TRUE

            -- first outgoing delivery date
            LEFT JOIN LATERAL (
                SELECT MIN(sp.date_done) AS date_done
                FROM   stock_picking sp
                JOIN   stock_picking_type spt ON spt.id = sp.picking_type_id
                WHERE  sp.pos_order_id        = po.id
                  AND  sp.state               = 'done'
                  AND  spt.code               = 'outgoing'
                  AND  sp.return_id           IS NULL
                  AND  sp.date_done           IS NOT NULL
            ) first_pick ON TRUE

            -- delivered qty from stock moves (linked by pos_order_line_id)
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(sm.quantity), 0.0) AS qty
                FROM   stock_move    sm
                JOIN   stock_picking sp ON sp.id = sm.picking_id
                WHERE  sp.pos_order_id       = po.id
                  AND  sp.return_id          IS NULL
                  AND  sm.pos_order_line_id  = pol.id
            ) dqty ON TRUE

            -- stock valuation cost
            -- For BOM products, include all component variants of the same POS order
            LEFT JOIN LATERAL (
                SELECT
                    ABS(SUM(svl.value))    AS total_cost,
                    ABS(SUM(svl.quantity)) AS total_qty
                FROM   stock_valuation_layer svl
                JOIN   stock_move    sm ON sm.id = svl.stock_move_id
                JOIN   stock_picking sp ON sp.id = sm.picking_id
                WHERE  sp.pos_order_id = po.id
                  AND  sp.return_id    IS NULL
                  AND  svl.product_id  = ANY(
                      -- If a BoM exists, collect the parent + all component variant IDs;
                      -- otherwise just the product itself.
                      SELECT pp2.id
                      FROM   product_product  pp2
                      JOIN   product_template pt2 ON pt2.id = pp2.product_tmpl_id
                      WHERE  pt2.id = (
                          SELECT pp_inner.product_tmpl_id
                          FROM   product_product pp_inner
                          WHERE  pp_inner.id = rr.product_id
                      )
                      UNION
                      SELECT mbl.product_id
                      FROM   mrp_bom      mb
                      JOIN   mrp_bom_line mbl ON mbl.bom_id = mb.id
                      JOIN   product_product pp3 ON pp3.product_tmpl_id = mb.product_tmpl_id
                      WHERE  pp3.id   = rr.product_id
                        AND  mb.active = TRUE
                        AND  mbl.product_id IS NOT NULL
                  )
            ) svl ON TRUE

            -- invoice amounts from the POS account_move
            LEFT JOIN LATERAL (
                SELECT
                    SUM(CASE WHEN am.move_type = 'out_invoice' THEN aml.price_total ELSE 0 END) AS delivered
                FROM   account_move_line aml
                JOIN   account_move      am ON am.id = aml.move_id
                WHERE  am.id            = po.account_move
                  AND  aml.product_id   = rr.product_id
                  AND  am.move_type IN ('out_invoice', 'out_refund')
            ) inv ON TRUE

            WHERE rr.pos_order_id IS NOT NULL
              AND rr.id = ANY(%s)
              AND r.id  = rr.id
        """, (report_ids,))

        # ============================================================
        # FINAL PASS — derived fields (earned_amount, margin, litri)
        # These depend on the values set in the two passes above.
        # ============================================================
        self.env.cr.execute(f"""
            UPDATE {report_table}
            SET
                real_invoice_amount         = delivery_amount + returned_invoice_amount,
                real_invoice_untaxed_amount = CASE
                                                WHEN delivery_amount + returned_invoice_amount > 0
                                                THEN (delivery_amount + returned_invoice_amount) / 1.18
                                                ELSE 0.0
                                              END,
                earned_amount               = CASE
                                                WHEN (delivery_amount + returned_invoice_amount) / 1.18 > 0
                                                THEN (delivery_amount + returned_invoice_amount) / 1.18
                                                     - ((sale_delivery_quantity - returned_qty) * erteuli_cost)
                                                ELSE 0.0
                                              END,
                margin                      = CASE
                                                WHEN (delivery_amount + returned_invoice_amount) > 0
                                                     AND (
                                                         (delivery_amount + returned_invoice_amount) / 1.18
                                                         - ((sale_delivery_quantity - returned_qty) * erteuli_cost)
                                                     ) > 0
                                                THEN (
                                                         (delivery_amount + returned_invoice_amount) / 1.18
                                                         - ((sale_delivery_quantity - returned_qty) * erteuli_cost)
                                                     )
                                                     / ((delivery_amount + returned_invoice_amount) / 1.18)
                                                ELSE 0.0
                                              END,
                litri                       = COALESCE(litri, 0.0)
                                              * (COALESCE(sale_quantity, 0.0) - COALESCE(returned_qty, 0.0)),
                write_uid                   = {uid},
                write_date                  = NOW() AT TIME ZONE 'UTC'
            WHERE id = ANY(%s)
        """, (report_ids,))

        reports.invalidate_recordset([
            'returned_qty', 'refunded_qty', 'delivery_amount', 'delivery_untaxed_amount',
            'returned_invoice_amount', 'cost', 'erteuli_cost',
            'real_invoice_amount', 'real_invoice_untaxed_amount',
            'earned_amount', 'margin',
            'date_order', 'delivery_date',
            'sale_delivery_quantity', 'litri',
        ])

    def action_generate(self):
        self.ensure_one()
        if self.date_start > self.date_end:
            raise UserError(_('Start Date must be before End Date.'))

        Report = self.env['generated.sale.report']
        so_table      = self.env['sale.order']._table
        sol_table     = self.env['sale.order.line']._table
        po_table      = self.env['pos.order']._table
        pol_table     = self.env['pos.order.line']._table
        report_table  = Report._table
        pt_table      = self.env['product.template']._table
        partner_table = self.env['res.partner']._table

        # ------------------------------------------------------------------
        # 1) INSERT from sale_order_line joined to sale_order
        # ------------------------------------------------------------------
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
                supplier_id,
                litri,
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
                pp.id,
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
                pp.supplier_id,
                pp.litri,
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
            JOIN {so_table} so        ON so.id  = sol.order_id
            LEFT JOIN product_product pp        ON pp.id  = sol.product_id
            LEFT JOIN {pt_table} pt             ON pt.id  = pp.product_tmpl_id
            LEFT JOIN {partner_table} rp        ON rp.id  = so.partner_id
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

        # ------------------------------------------------------------------
        # 2) INSERT from pos_order_line joined to pos_order
        # ------------------------------------------------------------------
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
                supplier_id,
                litri,
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
                pp.id,
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
                pp.supplier_id,
                pp.litri,
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
            JOIN {po_table} po        ON po.id  = pol.order_id
            LEFT JOIN product_product pp        ON pp.id  = pol.product_id
            LEFT JOIN {pt_table} pt             ON pt.id  = pp.product_tmpl_id
            LEFT JOIN {partner_table} rp        ON rp.id  = po.partner_id
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
            'sale_order_id', 'sale_order_line_id', 'pos_order_id', 'pos_order_line_id',
            'sale_status', 'pos_status', 'partner_id', 'salesperson_id', 'product_id',
            'sale_delivery_quantity', 'sale_invoice_quantity', 'sale_packaging_quantity',
            'sale_packaging_id', 'unit_price', 'sale_amount_until_discount',
            'sale_price_total', 'sale_product_group_id',
            'article_id', 'category_id', 'supplier_id', 'litri', 'volume',
            'buyer_group', 'city_region', 'discount_percent', 'loyalty_program_id',
            'discount_difference',
        ])

        if report_ids:
            self._fill_picking_and_invoice_fields(Report.browse(report_ids))

        if self.env.user.has_group('generated_sale_report.group_sale_report_manager'):
            list_view = self.env.ref('generated_sale_report.view_generated_sale_report_list')
            pivot_view = self.env.ref('generated_sale_report.view_generated_sale_report_pivot')
        else:
            list_view = self.env.ref('generated_sale_report.view_generated_sale_report_list_user')
            pivot_view = self.env.ref('generated_sale_report.view_generated_sale_report_pivot_user')

        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Report'),
            'res_model': 'generated.sale.report',
            'view_mode': 'list,pivot',
            'views': [(list_view.id, 'list'), (pivot_view.id, 'pivot')],
            'domain': [('id', 'in', report_ids)] if report_ids else [],
        }