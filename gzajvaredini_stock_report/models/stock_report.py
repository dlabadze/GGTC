import re

from odoo import api, fields, models, tools
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta
from ast import literal_eval
import logging

_logger = logging.getLogger(__name__)

class GzaStockReport(models.Model):
    _name = 'gza.stock.report'
    _description = 'Gza Stock Report'
    _auto = False
    
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name_clean = fields.Char(string='Product', compute='_compute_product_name_clean', store=False)
    product_name = fields.Char(related='product_id.name', string='Product Name', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)
    uom_name = fields.Char(string='ზომის ერთეული', compute='_compute_uom_name', store=False, search='_search_uom_name')
    initial_qty = fields.Float(string='Initial Balance', readonly=True, digits=(16, 4), search='_search_initial_qty')
    incoming_qty = fields.Float(string='Incoming', readonly=True, digits=(16, 4), search='_search_incoming_qty')
    outgoing_qty = fields.Float(string='Outgoing', readonly=True, digits=(16, 4), search='_search_outgoing_qty')
    final_qty = fields.Float(string='Final Balance', readonly=True, digits=(16, 4), search='_search_final_qty')
    initial_amount = fields.Float(string='Initial Balance Amount', readonly=True, digits=(16, 4), compute='_compute_amounts', store=False)
    incoming_amount = fields.Float(string='Incoming Amount', readonly=True, digits=(16, 4), compute='_compute_amounts', store=False)
    outgoing_amount = fields.Float(string='Outgoing Amount', readonly=True, digits=(16, 4), compute='_compute_amounts', store=False)
    final_amount = fields.Float(string='Final Balance Amount', readonly=True, digits=(16, 4), compute='_compute_amounts', store=False)
    date_from = fields.Date(string='Date From', readonly=True, search='_search_date_from')
    date_to = fields.Date(string='Date To', readonly=True, search='_search_date_to')
    internal_ref = fields.Char(related='product_id.default_code', string='Internal Reference', readonly=True)
    category_id = fields.Many2one(related='product_id.categ_id', string='Category', readonly=True)
    include_internal_transfers = fields.Boolean(string='Include Internal Transfers', readonly=True)

    @api.depends('uom_id')
    def _compute_uom_name(self):
        for record in self:
            try:
                if record.uom_id:
                    uom = self.env['uom.uom'].browse(record.uom_id.id)
                    record.uom_name = uom.name
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

    @api.depends('product_id', 'warehouse_id', 'date_from', 'date_to', 'include_internal_transfers')
    def _compute_amounts(self):
        for record in self:
            record.initial_amount = 0.0
            record.incoming_amount = 0.0
            record.outgoing_amount = 0.0
            record.final_amount = 0.0
            if not record.product_id or not record.warehouse_id:
                continue

            date_from_end, date_to_end, date_to_end_str = record._get_amount_date_bounds()
            warehouse_locations = self.env['stock.location'].search([
                ('id', 'child_of', record.warehouse_id.view_location_id.id),
                ('usage', '=', 'internal'),
            ])
            if not warehouse_locations:
                continue

            domain = [
                ('product_id', '=', record.product_id.id),
                ('state', '=', 'done'),
                ('date', '<=', date_to_end_str),
                '|',
                ('location_id', 'in', warehouse_locations.ids),
                ('location_dest_id', 'in', warehouse_locations.ids),
            ]

            if record.include_internal_transfers:
                domain.extend([
                    '|',
                    ('picking_id.picking_type_id.code', 'in', ['incoming', 'outgoing', 'internal', 'mrp_operation', 'repair_operation']),
                    ('picking_type_id.code', 'in', ['incoming', 'outgoing', 'internal', 'mrp_operation', 'repair_operation']),
                ])
            else:
                domain.extend([
                    '|',
                    ('picking_id.picking_type_id.code', 'in', ['incoming', 'outgoing']),
                    ('picking_type_id.code', 'in', ['incoming', 'outgoing']),
                ])

            moves = self.env['stock.move'].search(domain)
            location_ids = set(warehouse_locations.ids)
            initial_amount = 0.0
            incoming_amount = 0.0
            outgoing_amount = 0.0

            for move in moves:
                move_value = abs(move.value or 0.0)
                if not move_value:
                    continue
                move_date = fields.Datetime.to_datetime(move.date)
                is_incoming = move.location_dest_id.id in location_ids
                is_outgoing = move.location_id.id in location_ids

                if move_date <= date_from_end:
                    if is_incoming:
                        initial_amount += move_value
                    if is_outgoing:
                        initial_amount -= move_value
                else:
                    if is_incoming:
                        incoming_amount += move_value
                    if is_outgoing:
                        outgoing_amount += move_value

            record.initial_amount = initial_amount
            record.incoming_amount = incoming_amount
            record.outgoing_amount = outgoing_amount
            record.final_amount = initial_amount + incoming_amount - outgoing_amount

    def _get_amount_date_bounds(self):
        self.ensure_one()
        date_from = fields.Date.to_date(self.date_from) if self.date_from else fields.Date.context_today(self)
        date_to = fields.Date.to_date(self.date_to) if self.date_to else fields.Date.context_today(self)
        date_from_end = datetime.combine(date_from, datetime.max.time())
        date_to_end = datetime.combine(date_to, datetime.max.time())
        return date_from_end, date_to_end, fields.Datetime.to_string(date_to_end)

    # Search methods for computed fields
    def _search_shenishvna(self, operator, value):
        products = self.env['product.template'].search([('x_studio_saqid3_1', operator, value)])
        if products:
            variants = self.env['product.product'].search([('product_tmpl_id', 'in', products.ids)])
            return [('product_id', 'in', variants.ids)]
        return [('id', '=', False)]

    @api.depends('product_id')
    def _compute_list_price(self):
        for rec in self:
            try:
                rec.list_price = rec.product_id.product_tmpl_id.list_price
            except Exception:
                rec.list_price = 0.0

    def _search_list_price(self, operator, value):
        # For list_price, use a direct SQL approach since the computed method isn't working
        if isinstance(value, str):
            try:
                value = float(value.replace(',', '.'))
            except (ValueError, TypeError):
                return [('id', '=', False)]
                
        # Create a more direct domain with product templates
        product_templates = self.env['product.template'].search([])
        matching_template_ids = []
        
        for template in product_templates:
            if operator == '=':
                if template.list_price == value:
                    matching_template_ids.append(template.id)
            elif operator == '>=':
                if template.list_price >= value:
                    matching_template_ids.append(template.id)
            elif operator == '>':
                if template.list_price > value:
                    matching_template_ids.append(template.id)
            elif operator == '<=':
                if template.list_price <= value:
                    matching_template_ids.append(template.id)
            elif operator == '<':
                if template.list_price < value:
                    matching_template_ids.append(template.id)
            elif operator in ('like', 'ilike'):
                str_val = str(template.list_price)
                if str(value) in str_val:
                    matching_template_ids.append(template.id)
                    
        if matching_template_ids:
            variants = self.env['product.product'].search([('product_tmpl_id', 'in', matching_template_ids)])
            if variants:
                return [('product_id', 'in', variants.ids)]
        return [('id', '=', False)]
    
    def _search_standard_price(self, operator, value):
        return [('product_id', 'in', [p.id for p in self.env['product.product'].search([]) if (operator == '=' and abs(p.standard_price - (float(value.replace(',', '.')) if isinstance(value, str) else value)) < 0.01) or (operator != '=' and eval(f"p.standard_price {operator} {float(value.replace(',', '.')) if isinstance(value, str) else value}"))])]


    def _search_x_studio_tvitgirdgg(self, operator, value): return [('product_id', 'in', [p.id for p in self.env['product.product'].search([]) if abs((p.standard_price * 1.18) - float(value if isinstance(value, (int, float)) else value.replace(',', '.'))) < 0.01])]
        
    def _search_barcode(self, operator, value):
        products = self.env['product.template'].search([('barcode', operator, value)])
        if products:
            variants = self.env['product.product'].search([('product_tmpl_id', 'in', products.ids)])
            return [('product_id', 'in', variants.ids)]
        return [('id', '=', False)]
    
    def _search_unit_id(self, operator, value):
        products = self.env['product.template'].search([('unit_id', operator, value)])
        if products:
            variants = self.env['product.product'].search([('product_tmpl_id', 'in', products.ids)])
            return [('product_id', 'in', variants.ids)]
        return [('id', '=', False)]

    def _search_unit_txt(self, operator, value):
        products = self.env['product.template'].search([('unit_txt', operator, value)])
        if products:
            variants = self.env['product.product'].search([('product_tmpl_id', 'in', products.ids)])
            return [('product_id', 'in', variants.ids)]
        return [('id', '=', False)]

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


    @api.depends('product_id')
    def _compute_unit_id(self):
        for record in self:
            try:
                product_tmpl = record.product_id.product_tmpl_id
                if product_tmpl and hasattr(product_tmpl, 'unit_id'):
                    product_template = self.env['product.template'].browse(product_tmpl.id)
                    record.unit_id = product_template.unit_id
                else:
                    record.unit_id = False
            except Exception:
                record.unit_id = False
    
    @api.depends('product_id')
    def _compute_unit_txt(self):
        for record in self:
            try:
                product_tmpl = record.product_id.product_tmpl_id
                if product_tmpl and hasattr(product_tmpl, 'unit_txt'):
                    product_template = self.env['product.template'].browse(product_tmpl.id)
                    record.unit_txt = product_template.unit_txt
                else:
                    record.unit_txt = False
            except Exception:
                record.unit_txt = False

    @api.depends('product_id')
    def _compute_barcode(self):
        for record in self:
            product_tmpl = record.product_id.product_tmpl_id
            if product_tmpl and hasattr(product_tmpl, 'barcode'):
                record.barcode = product_tmpl.barcode
            else:
                record.barcode = False
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # Create basic view with params
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH params AS (
                    SELECT
                        CURRENT_DATE - INTERVAL '30 days' AS date_from,
                        CURRENT_DATE AS date_to
                ),
                current_stock AS (
                    SELECT 
                        sq.product_id,
                        sw.id as warehouse_id,
                        SUM(sq.quantity) as qty
                    FROM stock_quant sq
                    JOIN stock_location sl ON sq.location_id = sl.id
                    JOIN stock_warehouse sw ON sl.parent_path LIKE CONCAT('%%/', sw.view_location_id, '/%%')
                    WHERE sl.usage = 'internal'
                    GROUP BY sq.product_id, sw.id
                )
                SELECT
                    row_number() OVER () as id,
                    cs.product_id,
                    cs.warehouse_id,
                    pt.uom_id as uom_id,
                    0.0 as initial_qty,
                    0.0 as incoming_qty,
                    0.0 as outgoing_qty,
                    cs.qty as final_qty,
                    0.0 as initial_amount,
                    0.0 as incoming_amount,
                    0.0 as outgoing_amount,
                    cs.qty * CASE 
                        WHEN pp.standard_price IS NULL THEN 0.0
                        WHEN pg_typeof(pp.standard_price)::text = 'jsonb' THEN
                            COALESCE(
                                (SELECT (value::text)::numeric 
                                 FROM jsonb_each_text(pp.standard_price) 
                                 LIMIT 1),
                                0.0
                            )
                        ELSE COALESCE(pp.standard_price::numeric, 0.0)
                    END as final_amount,
                    (SELECT date_from FROM params) as date_from,
                    (SELECT date_to FROM params) as date_to,
                    false as include_internal_transfers
                FROM current_stock cs
                JOIN product_product pp ON cs.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE cs.qty > 0
            )
        """ % self._table)

    def action_view_stock_moves(self):
        """
        Show ONLY the stock moves that were counted in this specific report line.
        This matches exactly what was calculated in the SQL query.
        """
        self.ensure_one()

        # Get the custom view for stock moves history
        history_view = self.env.ref('gzajvaredini_stock_report.view_stock_move_history_list')

        # Use stock.move action with custom view
        action = {
            'name': 'Stock Moves History',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'views': [(history_view.id, 'list'), (False, 'form')],
            'target': 'current',
        }

        # Base filters: product and state
        domain = [
            ('product_id', '=', self.product_id.id),
            ('state', '=', 'done'),
        ]

        # Date range filter (required - must match report generation)
        if self.date_from and self.date_to:
            domain.append(('date', '>=', fields.Datetime.to_string(
                datetime.combine(fields.Date.to_date(self.date_from), datetime.min.time())
            )))
            domain.append(('date', '<=', fields.Datetime.to_string(
                datetime.combine(fields.Date.to_date(self.date_to), datetime.max.time())
            )))

        # Warehouse filter - moves affecting this warehouse
        warehouse = self.warehouse_id
        if warehouse:
            # Get warehouse location and all its children
            warehouse_locations = self.env['stock.location'].search([
                ('id', 'child_of', warehouse.view_location_id.id),
                ('usage', '=', 'internal')
            ])

            # Move must have source OR destination in this warehouse
            domain.append('|')
            domain.append(('location_id', 'in', warehouse_locations.ids))
            domain.append(('location_dest_id', 'in', warehouse_locations.ids))

        # Operation type filter based on include_internal_transfers setting
        if self.include_internal_transfers:
            # Include all operation types
            domain.append('|')
            domain.append(('picking_id.picking_type_id.code', 'in', ['incoming', 'outgoing', 'internal', 'mrp_operation', 'repair_operation']))
            domain.append(('picking_type_id.code', 'in', ['incoming', 'outgoing', 'internal', 'mrp_operation', 'repair_operation']))
        else:
            # Only include incoming and outgoing
            domain.append('|')
            domain.append(('picking_id.picking_type_id.code', 'in', ['incoming', 'outgoing']))
            domain.append(('picking_type_id.code', 'in', ['incoming', 'outgoing']))

        action['domain'] = domain
        action['context'] = {
            'search_default_product_id': self.product_id.id,
            'search_default_done': 1,
        }

        return action


class GzaStockReportWizard(models.TransientModel):
    _name = 'gza.stock.report.wizard'
    _description = 'Stock Report Wizard'
    
    date_from = fields.Date(string='Start Date', required=True, default=lambda self: fields.Date.context_today(self) - timedelta(days=30))
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    category_ids = fields.Many2many('product.category', string='Product Categories')
    use_category_filter = fields.Boolean(string='Filter by Category')
    include_internal_transfers = fields.Boolean(string='შიდა გადაცემების გათვალისწინება', default=False)
    
    def action_generate_report(self):
        """
        Generate stock report with enhanced amount calculations.
        
        This method creates a SQL view that:
        - Calculates quantities from stock moves
        - Uses actual transaction prices (price_unit) when available from stock pickings
        - Falls back to product standard_price if no price_unit is set
        - Properly handles incoming and outgoing amounts based on actual costs
        
        The amounts now reflect real transaction values rather than just current product cost.
        """
        self.ensure_one()
        
        try:
            # Drop existing view with savepoint
            self.env.cr.execute("SAVEPOINT stock_report_savepoint")
            self.env.cr.execute("DROP VIEW IF EXISTS gza_stock_report")
            
            # Convert dates to strings for SQL
            date_from_str = self.date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_to_str = self.date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
            
            # Build query based on internal transfers option
            if self.include_internal_transfers:
                # Include all operation types: incoming, outgoing, internal, mrp_operation, repair_operation
                sql_query = """
                CREATE OR REPLACE VIEW gza_stock_report AS (
                    WITH current_stock AS (
                        SELECT 
                            sq.product_id,
                            sw.id as warehouse_id,
                            SUM(sq.quantity) as current_qty
                        FROM stock_quant sq
                        JOIN stock_location sl ON sq.location_id = sl.id
                        JOIN stock_warehouse sw ON sl.parent_path LIKE CONCAT('%%/', sw.view_location_id, '/%%')
                        WHERE sl.usage = 'internal'
                        GROUP BY sq.product_id, sw.id
                    ),
                    incoming AS (
                        SELECT 
                            sm.product_id,
                            sw.id as warehouse_id,
                            SUM(sm.product_qty) as qty,
                            SUM(
                                CASE 
                                    WHEN sm.price_unit > 0 THEN sm.product_qty * sm.price_unit
                                    ELSE sm.product_qty * COALESCE(
                                        CASE 
                                            WHEN pg_typeof(pp.standard_price)::text = 'jsonb' THEN
                                                (SELECT (value::text)::numeric 
                                                 FROM jsonb_each_text(pp.standard_price) 
                                                 LIMIT 1)
                                            ELSE pp.standard_price::numeric
                                        END, 0.0)
                                END
                            ) as amount
                        FROM stock_move sm
                        JOIN product_product pp ON sm.product_id = pp.id
                        JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                        JOIN stock_warehouse sw ON sl_dest.parent_path LIKE CONCAT('%%/', sw.view_location_id, '/%%')
                        LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                        LEFT JOIN stock_picking_type spt ON COALESCE(sp.picking_type_id, sm.picking_type_id) = spt.id
                        WHERE sm.state = 'done'
                        AND sl_dest.usage = 'internal'
                        AND spt.code IN ('incoming', 'outgoing', 'internal', 'mrp_operation', 'repair_operation')
                        AND sm.date::date >= '%s'
                        AND sm.date::date <= '%s'
                        GROUP BY sm.product_id, sw.id
                    ),
                    outgoing AS (
                        SELECT 
                            sm.product_id,
                            sw.id as warehouse_id,
                            SUM(sm.product_qty) as qty,
                            SUM(
                                CASE 
                                    WHEN sm.price_unit > 0 THEN sm.product_qty * sm.price_unit
                                    ELSE sm.product_qty * COALESCE(
                                        CASE 
                                            WHEN pg_typeof(pp.standard_price)::text = 'jsonb' THEN
                                                (SELECT (value::text)::numeric 
                                                 FROM jsonb_each_text(pp.standard_price) 
                                                 LIMIT 1)
                                            ELSE pp.standard_price::numeric
                                        END, 0.0)
                                END
                            ) as amount
                        FROM stock_move sm
                        JOIN product_product pp ON sm.product_id = pp.id
                        JOIN stock_location sl_source ON sm.location_id = sl_source.id
                        JOIN stock_warehouse sw ON sl_source.parent_path LIKE CONCAT('%%/', sw.view_location_id, '/%%')
                        LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                        LEFT JOIN stock_picking_type spt ON COALESCE(sp.picking_type_id, sm.picking_type_id) = spt.id
                        WHERE sm.state = 'done'
                        AND sl_source.usage = 'internal'
                        AND spt.code IN ('incoming', 'outgoing', 'internal', 'mrp_operation', 'repair_operation')
                        AND sm.date::date >= '%s'
                        AND sm.date::date <= '%s'
                        GROUP BY sm.product_id, sw.id
                    ),"""
                sql_params = (date_from_str, date_to_str, date_from_str, date_to_str)
            else:
                # Only include incoming and outgoing operation types (exclude internal transfers)
                sql_query = """
                CREATE OR REPLACE VIEW gza_stock_report AS (
                    WITH current_stock AS (
                        SELECT 
                            sq.product_id,
                            sw.id as warehouse_id,
                            SUM(sq.quantity) as current_qty
                        FROM stock_quant sq
                        JOIN stock_location sl ON sq.location_id = sl.id
                        JOIN stock_warehouse sw ON sl.parent_path LIKE CONCAT('%%/', sw.view_location_id, '/%%')
                        WHERE sl.usage = 'internal'
                        GROUP BY sq.product_id, sw.id
                    ),
                    incoming AS (
                        SELECT 
                            sm.product_id,
                            sw.id as warehouse_id,
                            SUM(sm.product_qty) as qty,
                            SUM(
                                CASE 
                                    WHEN sm.price_unit > 0 THEN sm.product_qty * sm.price_unit
                                    ELSE sm.product_qty * COALESCE(
                                        CASE 
                                            WHEN pg_typeof(pp.standard_price)::text = 'jsonb' THEN
                                                (SELECT (value::text)::numeric 
                                                 FROM jsonb_each_text(pp.standard_price) 
                                                 LIMIT 1)
                                            ELSE pp.standard_price::numeric
                                        END, 0.0)
                                END
                            ) as amount
                        FROM stock_move sm
                        JOIN product_product pp ON sm.product_id = pp.id
                        JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                        JOIN stock_warehouse sw ON sl_dest.parent_path LIKE CONCAT('%%/', sw.view_location_id, '/%%')
                        LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                        LEFT JOIN stock_picking_type spt ON COALESCE(sp.picking_type_id, sm.picking_type_id) = spt.id
                        WHERE sm.state = 'done'
                        AND sl_dest.usage = 'internal'
                        AND spt.code IN ('incoming', 'outgoing')
                        AND sm.date::date >= '%s'
                        AND sm.date::date <= '%s'
                        GROUP BY sm.product_id, sw.id
                    ),
                    outgoing AS (
                        SELECT 
                            sm.product_id,
                            sw.id as warehouse_id,
                            SUM(sm.product_qty) as qty,
                            SUM(
                                CASE 
                                    WHEN sm.price_unit > 0 THEN sm.product_qty * sm.price_unit
                                    ELSE sm.product_qty * COALESCE(
                                        CASE 
                                            WHEN pg_typeof(pp.standard_price)::text = 'jsonb' THEN
                                                (SELECT (value::text)::numeric 
                                                 FROM jsonb_each_text(pp.standard_price) 
                                                 LIMIT 1)
                                            ELSE pp.standard_price::numeric
                                        END, 0.0)
                                END
                            ) as amount
                        FROM stock_move sm
                        JOIN product_product pp ON sm.product_id = pp.id
                        JOIN stock_location sl_source ON sm.location_id = sl_source.id
                        JOIN stock_warehouse sw ON sl_source.parent_path LIKE CONCAT('%%/', sw.view_location_id, '/%%')
                        LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                        LEFT JOIN stock_picking_type spt ON COALESCE(sp.picking_type_id, sm.picking_type_id) = spt.id
                        WHERE sm.state = 'done'
                        AND sl_source.usage = 'internal'
                        AND spt.code IN ('incoming', 'outgoing')
                        AND sm.date::date >= '%s'
                        AND sm.date::date <= '%s'
                        GROUP BY sm.product_id, sw.id
                    ),"""
                sql_params = (date_from_str, date_to_str, date_from_str, date_to_str)
            
            # Complete the query with common parts
            complete_query = sql_query + """
                    product_prices AS (
                        SELECT 
                            pp.id as product_id,
                            CASE 
                                WHEN pp.standard_price IS NULL THEN 0.0
                                WHEN pg_typeof(pp.standard_price)::text = 'jsonb' THEN
                                    COALESCE(
                                        (SELECT (value::text)::numeric 
                                         FROM jsonb_each_text(pp.standard_price) 
                                         LIMIT 1),
                                        0.0
                                    )
                                ELSE COALESCE(pp.standard_price::numeric, 0.0)
                            END as standard_price
                        FROM product_product pp
                    )
                    SELECT
                        row_number() OVER () as id,
                        cs.product_id,
                        cs.warehouse_id,
                        pt.uom_id as uom_id,
                        cs.current_qty - COALESCE(i.qty, 0) + COALESCE(o.qty, 0) as initial_qty,
                        COALESCE(i.qty, 0) as incoming_qty,
                        COALESCE(o.qty, 0) as outgoing_qty,
                        cs.current_qty as final_qty,
                        (cs.current_qty - COALESCE(i.qty, 0) + COALESCE(o.qty, 0)) * COALESCE(pr.standard_price, 0.0) as initial_amount,
                        COALESCE(i.amount, 0.0) as incoming_amount,
                        COALESCE(o.amount, 0.0) as outgoing_amount,
                        cs.current_qty * COALESCE(pr.standard_price, 0.0) as final_amount,
                        '%s'::date as date_from,
                        '%s'::date as date_to,
                        %s as include_internal_transfers
                    FROM current_stock cs
                    JOIN product_product pp ON cs.product_id = pp.id
                    JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    LEFT JOIN product_prices pr ON cs.product_id = pr.product_id
                    LEFT JOIN incoming i ON cs.product_id = i.product_id AND cs.warehouse_id = i.warehouse_id
                    LEFT JOIN outgoing o ON cs.product_id = o.product_id AND cs.warehouse_id = o.warehouse_id
                    WHERE 
                        cs.current_qty > 0 
                        OR COALESCE(i.qty, 0) > 0 
                        OR COALESCE(o.qty, 0) > 0
                )
            """
            
            # Format and execute the query
            include_internal_str = 'true' if self.include_internal_transfers else 'false'
            self.env.cr.execute(complete_query % (sql_params + (date_from_str, date_to_str, include_internal_str)))

            
            
            self.env.cr.execute("RELEASE SAVEPOINT stock_report_savepoint")
        except Exception as e:
            self.env.cr.execute("ROLLBACK TO SAVEPOINT stock_report_savepoint")
            if "SerializationFailure" in str(e):
                import time
                time.sleep(5)
                return self.action_generate_report()
            raise
        
        # Prepare domain for warehouse filter
        domain = []
        if self.warehouse_ids:
            domain.append(('warehouse_id', 'in', self.warehouse_ids.ids))
        if self.use_category_filter and self.category_ids:
            domain.append(('product_id.categ_id', 'child_of', self.category_ids.ids))
        
        # Return the action to open the report
        action = self.env.ref('gzajvaredini_stock_report.action_gza_stock_report').read()[0]
        view_with_category = self.env.ref('gzajvaredini_stock_report.view_gza_stock_report_list')
        view_without_category = self.env.ref('gzajvaredini_stock_report.view_gza_stock_report_list_no_category')
        selected_view = view_with_category if self.use_category_filter else view_without_category
        action['views'] = [(selected_view.id, 'list')]
        action['view_id'] = selected_view.id
        action['domain'] = domain
        return action

# -*- coding: utf-8 -*-
# Save this as cleanup_products.py in your Odoo.sh custom_addons directory

# -*- coding: utf-8 -*-
# Save this as cleanup_products.py in your Odoo.sh custom_addons directory

# -*- coding: utf-8 -*-
# Save this as wizard/product_cleanup.py in your custom module
