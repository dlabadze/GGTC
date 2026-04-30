from datetime import datetime
from ast import literal_eval
import logging
import re

from odoo import api, fields, models, tools
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)


def _get_utc_day_bounds(env, date_from, date_to):
    """Return day bounds without timezone offset shifting."""
    del env  # kept for backward-compatible signature
    from_dt = datetime.combine(date_from, datetime.min.time())
    to_dt = datetime.combine(date_to, datetime.max.time())
    return fields.Datetime.to_string(from_dt), fields.Datetime.to_string(to_dt)


class GzaStockLocationReport(models.Model):
    _name = 'gza.stock.location.report'
    _description = 'Gza Stock Location Report'
    _auto = False

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(related='product_id.name', string='Product Name', readonly=True)
    product_name_clean = fields.Char(string='Product', compute='_compute_product_name_clean', store=False)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)
    uom_name = fields.Char(string='Unit of Measure Name', compute='_compute_uom_name', store=False, search='_search_uom_name')
    initial_qty = fields.Float(string='Initial Balance', readonly=True, digits=(16, 4), search='_search_initial_qty')
    incoming_qty = fields.Float(string='Incoming', readonly=True, digits=(16, 4), search='_search_incoming_qty')
    outgoing_qty = fields.Float(string='Outgoing', readonly=True, digits=(16, 4), search='_search_outgoing_qty')
    final_qty = fields.Float(string='Final Balance', readonly=True, digits=(16, 4), search='_search_final_qty')
    initial_amount = fields.Float(string='საწყისი თანხა', readonly=True, digits=(16, 2), store=True)
    incoming_amount = fields.Float(string='შემოსავალი თანხა', readonly=True, digits=(16, 2), store=True)
    outgoing_amount = fields.Float(string='გასავალი თანხა', readonly=True, digits=(16, 2), store=True)
    final_amount = fields.Float(string='საბოლოო ნაშთი თანხა', readonly=True, digits=(16, 2), store=True)
    date_from = fields.Date(string='Date From', readonly=True, search='_search_date_from')
    date_to = fields.Date(string='Date To', readonly=True, search='_search_date_to')
    include_internal_transfers = fields.Boolean(string='Include Internal Transfers', readonly=True)
    internal_ref = fields.Char(related='product_id.default_code', string='Internal Reference', readonly=True)
    category_id = fields.Many2one(related='product_id.categ_id', string='Category', readonly=True)
    stock_valuation_account_id = fields.Many2one(
        related='product_id.categ_id.property_stock_valuation_account_id',
        comodel_name='account.account',
        string='Stock Valuation Account',
        readonly=True,
    )
    unique_location_id = fields.Char(related='location_id.x_unique_location_id', string='Unique Location ID', readonly=True)
    unit_price = fields.Float(string='Cost', readonly=True, digits=(16, 4), compute='_compute_unit_price', store=False)

    @api.depends('product_id')
    def _compute_unit_price(self):
        for record in self:
            if record.product_id:
                record.unit_price = record.product_id.standard_price
            else:
                record.unit_price = 0.0

    @api.depends('uom_id')
    def _compute_uom_name(self):
        for record in self:
            try:
                if record.uom_id:
                    record.uom_name = record.uom_id.name
                else:
                    record.uom_name = False
            except Exception:
                record.uom_name = False

    @api.depends('product_id')
    def _compute_product_name_clean(self):
        bracket_pattern = re.compile(r'^\[[^\]]*\]\s*')
        for record in self:
            name = record.product_id.display_name if record.product_id else ''
            record.product_name_clean = bracket_pattern.sub('', name or '').strip()

    def _search_uom_name(self, operator, value):
        uoms = self.env['uom.uom'].search([('name', operator, value)])
        if uoms:
            return [('uom_id', 'in', uoms.ids)]
        return [('id', '=', False)]

    def _search_initial_qty(self, operator, value):
        return [('initial_qty', operator, value)]

    def _search_incoming_qty(self, operator, value):
        return [('incoming_qty', operator, value)]

    def _search_outgoing_qty(self, operator, value):
        return [('outgoing_qty', operator, value)]

    def _search_final_qty(self, operator, value):
        return [('final_qty', operator, value)]

    def _search_date_from(self, operator, value):
        return [('date_from', operator, value)]

    def _search_date_to(self, operator, value):
        return [('date_to', operator, value)]

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH params AS (
                    SELECT
                        CURRENT_DATE - INTERVAL '30 days' AS date_from,
                        CURRENT_DATE AS date_to
                ),
                current_stock AS (
                    SELECT
                        sq.product_id,
                        sq.location_id,
                        SUM(sq.quantity) AS qty
                    FROM stock_quant sq
                    JOIN stock_location sl ON sq.location_id = sl.id
                    WHERE sl.usage = 'internal'
                    GROUP BY sq.product_id, sq.location_id
                )
                SELECT
                    row_number() OVER () AS id,
                    cs.product_id,
                    cs.location_id,
                    pt.uom_id AS uom_id,
                    0.0 AS initial_qty,
                    0.0 AS incoming_qty,
                    0.0 AS outgoing_qty,
                    cs.qty AS final_qty,
                    0.0 AS initial_amount,
                    0.0 AS incoming_amount,
                    0.0 AS outgoing_amount,
                    0.0 AS final_amount,
                    (SELECT date_from FROM params) AS date_from,
                    (SELECT date_to FROM params) AS date_to
                FROM current_stock cs
                JOIN product_product pp ON cs.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE cs.qty <> 0
            )
        """)

    def action_view_stock_moves(self):
        """Open the stock.move.line records that are used for this report line.

        Same filters as the report: product, done move, move line date in
        [date_from, date_to], and line touches this location (source or dest).
        These are the lines that feed incoming/outgoing for this (product, location).
        """
        self.ensure_one()

        history_view = self.env.ref('stock_report_location.view_stock_move_line_history_list')

        action = {
            'name': 'Stock Move Lines (History)',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'view_mode': 'list,form',
            'views': [(history_view.id, 'list'), (False, 'form')],
            'target': 'current',
        }

        # Same logic as report: stock.move.line with product, done, date in range, location
        domain = [
            ('product_id', '=', self.product_id.id),
            ('move_id.state', '=', 'done'),
        ]

        if self.date_from or self.date_to:
            date_from = fields.Date.to_date(self.date_from) if self.date_from else fields.Date.from_string('1900-01-01')
            date_to = fields.Date.to_date(self.date_to) if self.date_to else fields.Date.context_today(self)
            date_from_str, date_to_str = _get_utc_day_bounds(self.env, date_from, date_to)
            domain.extend([
                ('date', '>=', date_from_str),
                ('date', '<=', date_to_str),
            ])

        # Line touches this location (source or destination) – same as report incoming/outgoing
        domain.extend([
            '|',
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', self.location_id.id),
        ])

        action['domain'] = domain
        action['context'] = {'search_default_done': 1}
        return action


class GzaStockLocationReportWizard(models.TransientModel):
    _name = 'gza.stock.location.report.wizard'
    _description = 'Stock Location Report Wizard'

    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: self._get_last_date_from(),
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        default=lambda self: self._get_last_date_to(),
    )
    location_ids = fields.Many2many(
        'stock.location',
        string='Locations',
        domain=[('usage', '=', 'internal')],
        default=lambda self: self._get_last_location_ids(),
    )
    category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
    )
    use_category_filter = fields.Boolean(string='Filter by Category')
    include_internal_transfers = fields.Boolean(string='შიდა გადაცემების გათვალისწინება', default=True)
    show_amount_columns = fields.Boolean(string='თანხის გრაფები')

    def _get_last_date_to(self):
        last_date_to = self.env['ir.config_parameter'].sudo().get_param(
            'gza.stock.location.report.wizard.last_date_to'
        )
        if last_date_to:
            return fields.Date.from_string(last_date_to)
        return fields.Date.context_today(self)

    def _get_last_date_from(self):
        last_date_from = self.env['ir.config_parameter'].sudo().get_param(
            'gza.stock.location.report.wizard.last_date_from'
        )
        if last_date_from:
            return fields.Date.from_string(last_date_from)
        return fields.Date.context_today(self)

    def _get_last_location_ids(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'gza.stock.location.report.wizard.last_location_ids'
        )
        if param:
            try:
                ids = [int(x) for x in param.split(',') if x.strip().isdigit()]
                if ids:
                    return [(6, 0, ids)]
            except (ValueError, TypeError):
                pass
        return [(5, 0, 0)]

    def action_generate_report(self):
        self.ensure_one()


        self.env['ir.config_parameter'].sudo().set_param(
            'gza.stock.location.report.wizard.last_date_to',
            fields.Date.to_string(self.date_to)
        )

        self.env['ir.config_parameter'].sudo().set_param(
            'gza.stock.location.report.wizard.last_date_from',
            fields.Date.to_string(self.date_from)
        )

        self.env['ir.config_parameter'].sudo().set_param(
            'gza.stock.location.report.wizard.last_location_ids',
            ','.join(str(i) for i in self.location_ids.ids)
        )

        try:
            self.env.cr.execute("SAVEPOINT stock_location_report_savepoint")
            self.env.cr.execute("DROP VIEW IF EXISTS gza_stock_location_report")

            date_from_str = self.date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_to_str = self.date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_from_start_str, date_to_end_str = _get_utc_day_bounds(self.env, self.date_from, self.date_to)

            # Force refresh stored stock.move.line.value so report generation
            # always uses values recalculated by _compute_line_value().
            self._recompute_move_line_values_for_report(date_to_end_str)

            # Log all stock.move.line for product code 3312 between report dates
            product_3312 = self.env['product.product'].search([('default_code', '=', '3312')], limit=1)
            if product_3312:
                move_lines = self.env['stock.move.line'].search([
                    ('product_id', '=', product_3312.id),
                    ('move_id.state', '=', 'done'),
                    ('date', '>=', date_from_start_str),
                    ('date', '<=', date_to_end_str),
                ], order='date, id')
                _logger.info(
                    "Stock Report: stock.move.line records for product 3312 between %s and %s (count=%s)",
                    date_from_str, date_to_str, len(move_lines)
                )
                for ml in move_lines:
                    source = ml.location_dest_id.display_name if ml.location_dest_id else ""
                    _logger.info("  dest=%s id=%s quantity=%s", source, ml.id, ml.quantity)
            else:
                _logger.info("Stock Report: no product with code 3312 found, skipping move line log")

            # Use same filtering as log: product, move_id.state='done', date between from/to, plus location.
            # No picking_type filter so all done moves in date range are considered.
            self.env.cr.execute(
                """
                CREATE OR REPLACE VIEW gza_stock_location_report AS (
                    WITH current_stock AS (
                        SELECT
                            sq.product_id,
                            sq.location_id,
                            SUM(sq.quantity) AS current_qty
                        FROM stock_quant sq
                        JOIN stock_location sl ON sq.location_id = sl.id
                        WHERE sl.usage = 'internal'
                        GROUP BY sq.product_id, sq.location_id
                    ),
                    incoming AS (
                        SELECT
                            sml.product_id,
                            sml.location_dest_id AS location_id,
                            SUM(sml.quantity) AS qty
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_dest ON sml.location_dest_id = sl_dest.id
                        WHERE sm.state = 'done'
                        AND sl_dest.usage = 'internal'
                        AND sml.date >= %s
                        AND sml.date <= %s
                        GROUP BY sml.product_id, sml.location_dest_id
                    ),
                    incoming_amount AS (
                        SELECT
                            sml.product_id,
                            sml.location_dest_id AS location_id,
                            SUM(ABS(COALESCE(sml.value, 0))) AS amount
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_dest ON sml.location_dest_id = sl_dest.id
                        WHERE sm.state = 'done'
                        AND sl_dest.usage = 'internal'
                        AND sml.date >= %s
                        AND sml.date <= %s
                        GROUP BY sml.product_id, sml.location_dest_id
                    ),
                    outgoing AS (
                        SELECT
                            sml.product_id,
                            sml.location_id AS location_id,
                            SUM(sml.quantity) AS qty
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_source ON sml.location_id = sl_source.id
                        WHERE sm.state = 'done'
                        AND sl_source.usage = 'internal'
                        AND sml.date >= %s
                        AND sml.date <= %s
                        GROUP BY sml.product_id, sml.location_id
                    ),
                    outgoing_amount AS (
                        SELECT
                            sml.product_id,
                            sml.location_id AS location_id,
                            SUM(ABS(COALESCE(sml.value, 0))) AS amount
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_source ON sml.location_id = sl_source.id
                        WHERE sm.state = 'done'
                        AND sl_source.usage = 'internal'
                        AND sml.date >= %s
                        AND sml.date <= %s
                        GROUP BY sml.product_id, sml.location_id
                    ),
                    incoming_after_from AS (
                        SELECT sml.product_id, sml.location_dest_id AS location_id, SUM(sml.quantity) AS qty
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_dest ON sml.location_dest_id = sl_dest.id
                        WHERE sm.state = 'done' AND sl_dest.usage = 'internal'
                        AND sml.date >= %s
                        GROUP BY sml.product_id, sml.location_dest_id
                    ),
                    outgoing_after_from AS (
                        SELECT sml.product_id, sml.location_id AS location_id, SUM(sml.quantity) AS qty
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_source ON sml.location_id = sl_source.id
                        WHERE sm.state = 'done' AND sl_source.usage = 'internal'
                        AND sml.date >= %s
                        GROUP BY sml.product_id, sml.location_id
                    ),
                    incoming_after_to AS (
                        SELECT sml.product_id, sml.location_dest_id AS location_id, SUM(sml.quantity) AS qty
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_dest ON sml.location_dest_id = sl_dest.id
                        WHERE sm.state = 'done' AND sl_dest.usage = 'internal'
                        AND sml.date > %s
                        GROUP BY sml.product_id, sml.location_dest_id
                    ),
                    outgoing_after_to AS (
                        SELECT sml.product_id, sml.location_id AS location_id, SUM(sml.quantity) AS qty
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_source ON sml.location_id = sl_source.id
                        WHERE sm.state = 'done' AND sl_source.usage = 'internal'
                        AND sml.date > %s
                        GROUP BY sml.product_id, sml.location_id
                    ),
                    incoming_up_to_from AS (
                        SELECT sml.product_id, sml.location_dest_id AS location_id, SUM(sml.quantity) AS qty
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_dest ON sml.location_dest_id = sl_dest.id
                        WHERE sm.state = 'done' AND sl_dest.usage = 'internal'
                        AND sml.date < %s
                        GROUP BY sml.product_id, sml.location_dest_id
                    ),
                    incoming_amount_up_to_from AS (
                        SELECT sml.product_id, sml.location_dest_id AS location_id, SUM(ABS(COALESCE(sml.value, 0))) AS amount
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_dest ON sml.location_dest_id = sl_dest.id
                        WHERE sm.state = 'done' AND sl_dest.usage = 'internal'
                        AND sml.date < %s
                        GROUP BY sml.product_id, sml.location_dest_id
                    ),
                    outgoing_up_to_from AS (
                        SELECT sml.product_id, sml.location_id AS location_id, SUM(sml.quantity) AS qty
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_source ON sml.location_id = sl_source.id
                        WHERE sm.state = 'done' AND sl_source.usage = 'internal'
                        AND sml.date < %s
                        GROUP BY sml.product_id, sml.location_id
                    ),
                    outgoing_amount_up_to_from AS (
                        SELECT sml.product_id, sml.location_id AS location_id, SUM(ABS(COALESCE(sml.value, 0))) AS amount
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sml.move_id = sm.id
                        JOIN stock_location sl_source ON sml.location_id = sl_source.id
                        WHERE sm.state = 'done' AND sl_source.usage = 'internal'
                        AND sml.date < %s
                        GROUP BY sml.product_id, sml.location_id
                    ),
                    all_locations AS (
                        SELECT product_id, location_id FROM current_stock
                        UNION
                        SELECT product_id, location_id FROM incoming
                        UNION
                        SELECT product_id, location_id FROM outgoing
                        UNION
                        SELECT product_id, location_id FROM incoming_after_from
                        UNION
                        SELECT product_id, location_id FROM outgoing_after_from
                        UNION
                        SELECT product_id, location_id FROM incoming_after_to
                        UNION
                        SELECT product_id, location_id FROM outgoing_after_to
                        UNION
                        SELECT product_id, location_id FROM incoming_up_to_from
                        UNION
                        SELECT product_id, location_id FROM outgoing_up_to_from
                        UNION
                        SELECT product_id, location_id FROM incoming_amount
                        UNION
                        SELECT product_id, location_id FROM outgoing_amount
                        UNION
                        SELECT product_id, location_id FROM incoming_amount_up_to_from
                        UNION
                        SELECT product_id, location_id FROM outgoing_amount_up_to_from
                    )
                    SELECT
                        row_number() OVER () AS id,
                        al.product_id,
                        al.location_id,
                        pt.uom_id AS uom_id,
                        (COALESCE(i_up_to_from.qty, 0) - COALESCE(o_up_to_from.qty, 0)) AS initial_qty,
                        COALESCE(i.qty, 0) AS incoming_qty,
                        COALESCE(o.qty, 0) AS outgoing_qty,
                        ((COALESCE(i_up_to_from.qty, 0) - COALESCE(o_up_to_from.qty, 0)) + COALESCE(i.qty, 0) - COALESCE(o.qty, 0)) AS final_qty,
                        (COALESCE(i_amount_up_to_from.amount, 0) - COALESCE(o_amount_up_to_from.amount, 0)) AS initial_amount,
                        COALESCE(i_amount.amount, 0) AS incoming_amount,
                        COALESCE(o_amount.amount, 0) AS outgoing_amount,
                        ((COALESCE(i_amount_up_to_from.amount, 0) - COALESCE(o_amount_up_to_from.amount, 0)) + COALESCE(i_amount.amount, 0) - COALESCE(o_amount.amount, 0)) AS final_amount,
                        %s::date AS date_from,
                        %s::date AS date_to,
                        %s::boolean AS include_internal_transfers
                    FROM all_locations al
                    JOIN product_product pp ON al.product_id = pp.id
                    JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    LEFT JOIN current_stock cs ON al.product_id = cs.product_id AND al.location_id = cs.location_id
                    LEFT JOIN incoming i ON al.product_id = i.product_id AND al.location_id = i.location_id
                    LEFT JOIN outgoing o ON al.product_id = o.product_id AND al.location_id = o.location_id
                    LEFT JOIN incoming_after_from i_after_from ON al.product_id = i_after_from.product_id AND al.location_id = i_after_from.location_id
                    LEFT JOIN outgoing_after_from o_after_from ON al.product_id = o_after_from.product_id AND al.location_id = o_after_from.location_id
                    LEFT JOIN incoming_after_to i_after ON al.product_id = i_after.product_id AND al.location_id = i_after.location_id
                    LEFT JOIN outgoing_after_to o_after ON al.product_id = o_after.product_id AND al.location_id = o_after.location_id
                    LEFT JOIN incoming_up_to_from i_up_to_from ON al.product_id = i_up_to_from.product_id AND al.location_id = i_up_to_from.location_id
                    LEFT JOIN outgoing_up_to_from o_up_to_from ON al.product_id = o_up_to_from.product_id AND al.location_id = o_up_to_from.location_id
                    LEFT JOIN incoming_amount i_amount ON al.product_id = i_amount.product_id AND al.location_id = i_amount.location_id
                    LEFT JOIN outgoing_amount o_amount ON al.product_id = o_amount.product_id AND al.location_id = o_amount.location_id
                    LEFT JOIN incoming_amount_up_to_from i_amount_up_to_from ON al.product_id = i_amount_up_to_from.product_id AND al.location_id = i_amount_up_to_from.location_id
                    LEFT JOIN outgoing_amount_up_to_from o_amount_up_to_from ON al.product_id = o_amount_up_to_from.product_id AND al.location_id = o_amount_up_to_from.location_id
                    WHERE (COALESCE(i_up_to_from.qty, 0) - COALESCE(o_up_to_from.qty, 0)) <> 0
                    OR COALESCE(i.qty, 0) <> 0
                    OR COALESCE(o.qty, 0) <> 0
                )
                """,
                (
                    date_from_start_str,
                    date_to_end_str,
                    date_from_start_str,
                    date_to_end_str,
                    date_from_start_str,
                    date_to_end_str,
                    date_from_start_str,
                    date_to_end_str,
                    date_from_start_str,
                    date_from_start_str,
                    date_to_end_str,
                    date_to_end_str,
                    date_from_start_str,
                    date_from_start_str,
                    date_from_start_str,
                    date_from_start_str,
                    date_from_str,
                    date_to_str,
                    self.include_internal_transfers,
                ),
            )

            self.env.cr.execute("RELEASE SAVEPOINT stock_location_report_savepoint")
        except Exception as exc:
            self.env.cr.execute("ROLLBACK TO SAVEPOINT stock_location_report_savepoint")
            if "SerializationFailure" in str(exc):
                import time
                time.sleep(5)
                return self.action_generate_report()
            raise

        domain = []
        if self.location_ids:
            domain.append(('location_id', 'in', self.location_ids.ids))
        if self.use_category_filter and self.category_ids:
            domain.append(('product_id.categ_id', 'child_of', self.category_ids.ids))

        action = self.env.ref('stock_report_location.action_gza_stock_location_report').read()[0]
        view_with_category = (
            self.env.ref('stock_report_location.view_gza_stock_location_report_list_amount')
            if self.show_amount_columns else
            self.env.ref('stock_report_location.view_gza_stock_location_report_list')
        )
        view_without_category = (
            self.env.ref('stock_report_location.view_gza_stock_location_report_list_no_category_amount')
            if self.show_amount_columns else
            self.env.ref('stock_report_location.view_gza_stock_location_report_list_no_category')
        )
        selected_view = view_with_category if self.use_category_filter else view_without_category
        action['views'] = [(selected_view.id, 'list')]
        action['view_id'] = selected_view.id
        action['domain'] = domain
        return action

    def _recompute_move_line_values_for_report(self, date_to_end_str):
        move_line_model = self.env['stock.move.line'].sudo()
        domain = [
            ('move_id.state', '=', 'done'),
            ('date', '<=', date_to_end_str),
        ]
        all_lines = move_line_model.search(domain)
        _logger.info("Stock Report: recomputing stock.move.line.value for %s lines", len(all_lines))

        for line in all_lines:
            line.write({'value': line._compute_line_value()})
