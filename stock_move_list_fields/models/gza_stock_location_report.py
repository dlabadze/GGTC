from odoo import models, fields, api, tools
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

class GzaStockLocationReport(models.Model):
    _inherit = 'gza.stock.location.report'

    request_manual_num = fields.Char( string='Request Number Manual', readonly=True)
    x_studio_request_number = fields.Char(string='Request Number', readonly=True)
    request_date = fields.Date(string='Request Date', readonly=True)

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
                    NULL::varchar AS request_manual_num,
                    NULL::varchar AS x_studio_request_number,
                    NULL::date AS request_date,
                    0.0 AS initial_qty,
                    0.0 AS incoming_qty,
                    0.0 AS outgoing_qty,
                    cs.qty AS final_qty,
                    0.0 AS initial_amount,
                    0.0 AS incoming_amount,
                    0.0 AS outgoing_amount,
                    0.0 AS final_amount,
                    (SELECT date_from FROM params) AS date_from,
                    (SELECT date_to FROM params) AS date_to,
                    TRUE AS include_internal_transfers
                FROM current_stock cs
                JOIN product_product pp ON cs.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE cs.qty <> 0
            )
        """)

class GzaStockLocationReportWizard(models.TransientModel):
    _inherit = 'gza.stock.location.report.wizard'



    def action_generate_report(self):
        res = super(GzaStockLocationReportWizard, self).action_generate_report()

        date_from_str = self.date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_to_str = self.date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
        tools.drop_view_if_exists(self.env.cr, 'gza_stock_location_report')

        self.env.cr.execute(
            """
            CREATE VIEW gza_stock_location_report AS (
                WITH current_stock AS (
                    SELECT sq.product_id, sq.location_id, SUM(sq.quantity) AS current_qty
                    FROM stock_quant sq
                    JOIN stock_location sl ON sq.location_id = sl.id
                    WHERE sl.usage = 'internal'
                    GROUP BY sq.product_id, sq.location_id
                ),
                latest_info AS (
                    SELECT DISTINCT ON (product_id, location_dest_id)
                        product_id, 
                        location_dest_id AS location_id, 
                        request_manual_num,
                        x_studio_request_number, 
                        request_date
                    FROM stock_move_line
                    WHERE state = 'done' 
                      AND x_studio_request_number IS NOT NULL
                      AND x_studio_request_number != ''
                    ORDER BY product_id, location_dest_id, date DESC
                ),
                incoming AS (
                    SELECT sml.product_id, sml.location_dest_id AS location_id, SUM(sml.quantity) AS qty
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sml.move_id = sm.id
                    JOIN stock_location sl_dest ON sml.location_dest_id = sl_dest.id
                    WHERE sm.state = 'done' 
                      AND sl_dest.usage = 'internal'
                      AND sml.date::date > %s AND sml.date::date <= %s
                    GROUP BY sml.product_id, sml.location_dest_id
                ),
                incoming_amount AS (
                    SELECT sml.product_id, sml.location_dest_id AS location_id, SUM(ABS(COALESCE(sml.value, 0))) AS amount
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sml.move_id = sm.id
                    JOIN stock_location sl_dest ON sml.location_dest_id = sl_dest.id
                    WHERE sm.state = 'done'
                      AND sl_dest.usage = 'internal'
                      AND sml.date::date > %s AND sml.date::date <= %s
                    GROUP BY sml.product_id, sml.location_dest_id
                ),
                outgoing AS (
                    SELECT sml.product_id, sml.location_id AS location_id, SUM(sml.quantity) AS qty
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sml.move_id = sm.id
                    JOIN stock_location sl_source ON sml.location_id = sl_source.id
                    WHERE sm.state = 'done' 
                      AND sl_source.usage = 'internal'
                      AND sml.date::date > %s AND sml.date::date <= %s
                    GROUP BY sml.product_id, sml.location_id
                ),
                outgoing_amount AS (
                    SELECT sml.product_id, sml.location_id AS location_id, SUM(ABS(COALESCE(sml.value, 0))) AS amount
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sml.move_id = sm.id
                    JOIN stock_location sl_source ON sml.location_id = sl_source.id
                    WHERE sm.state = 'done'
                      AND sl_source.usage = 'internal'
                      AND sml.date::date > %s AND sml.date::date <= %s
                    GROUP BY sml.product_id, sml.location_id
                ),
                incoming_up_to_from AS (
                    SELECT sml.product_id, sml.location_dest_id AS location_id, SUM(sml.quantity) AS qty
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sml.move_id = sm.id
                    JOIN stock_location sl_dest ON sml.location_dest_id = sl_dest.id
                    WHERE sm.state = 'done'
                      AND sl_dest.usage = 'internal'
                      AND sml.date::date <= %s
                    GROUP BY sml.product_id, sml.location_dest_id
                ),
                incoming_amount_up_to_from AS (
                    SELECT sml.product_id, sml.location_dest_id AS location_id, SUM(ABS(COALESCE(sml.value, 0))) AS amount
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sml.move_id = sm.id
                    JOIN stock_location sl_dest ON sml.location_dest_id = sl_dest.id
                    WHERE sm.state = 'done'
                      AND sl_dest.usage = 'internal'
                      AND sml.date::date <= %s
                    GROUP BY sml.product_id, sml.location_dest_id
                ),
                outgoing_up_to_from AS (
                    SELECT sml.product_id, sml.location_id AS location_id, SUM(sml.quantity) AS qty
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sml.move_id = sm.id
                    JOIN stock_location sl_source ON sml.location_id = sl_source.id
                    WHERE sm.state = 'done'
                      AND sl_source.usage = 'internal'
                      AND sml.date::date <= %s
                    GROUP BY sml.product_id, sml.location_id
                ),
                outgoing_amount_up_to_from AS (
                    SELECT sml.product_id, sml.location_id AS location_id, SUM(ABS(COALESCE(sml.value, 0))) AS amount
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sml.move_id = sm.id
                    JOIN stock_location sl_source ON sml.location_id = sl_source.id
                    WHERE sm.state = 'done'
                      AND sl_source.usage = 'internal'
                      AND sml.date::date <= %s
                    GROUP BY sml.product_id, sml.location_id
                ),
                all_locations AS (
                    SELECT product_id, location_id FROM current_stock
                    UNION SELECT product_id, location_id FROM incoming
                    UNION SELECT product_id, location_id FROM outgoing
                    UNION SELECT product_id, location_id FROM incoming_up_to_from
                    UNION SELECT product_id, location_id FROM outgoing_up_to_from
                    UNION SELECT product_id, location_id FROM incoming_amount
                    UNION SELECT product_id, location_id FROM outgoing_amount
                    UNION SELECT product_id, location_id FROM incoming_amount_up_to_from
                    UNION SELECT product_id, location_id FROM outgoing_amount_up_to_from
                )
                SELECT
                    row_number() OVER () AS id,
                    al.product_id,
                    al.location_id,
                    pt.uom_id AS uom_id,
                    -- ORIGINAL ORDER KEPT HERE:
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
                    %s::boolean AS include_internal_transfers,
                    -- NEW COLUMNS ADDED AT THE VERY END:
                    li.request_manual_num,
                    li.x_studio_request_number,
                    li.request_date
                FROM all_locations al
                JOIN product_product pp ON al.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN latest_info li ON al.product_id = li.product_id AND al.location_id = li.location_id
                LEFT JOIN incoming i ON al.product_id = i.product_id AND al.location_id = i.location_id
                LEFT JOIN outgoing o ON al.product_id = o.product_id AND al.location_id = o.location_id
                LEFT JOIN incoming_amount i_amount ON al.product_id = i_amount.product_id AND al.location_id = i_amount.location_id
                LEFT JOIN outgoing_amount o_amount ON al.product_id = o_amount.product_id AND al.location_id = o_amount.location_id
                LEFT JOIN incoming_up_to_from i_up_to_from ON al.product_id = i_up_to_from.product_id AND al.location_id = i_up_to_from.location_id
                LEFT JOIN outgoing_up_to_from o_up_to_from ON al.product_id = o_up_to_from.product_id AND al.location_id = o_up_to_from.location_id
                LEFT JOIN incoming_amount_up_to_from i_amount_up_to_from ON al.product_id = i_amount_up_to_from.product_id AND al.location_id = i_amount_up_to_from.location_id
                LEFT JOIN outgoing_amount_up_to_from o_amount_up_to_from ON al.product_id = o_amount_up_to_from.product_id AND al.location_id = o_amount_up_to_from.location_id
                WHERE (COALESCE(i_up_to_from.qty, 0) - COALESCE(o_up_to_from.qty, 0)) <> 0
                   OR COALESCE(i.qty, 0) <> 0
                   OR COALESCE(o.qty, 0) <> 0
            )
            """,
            (
                date_from_str, date_to_str,
                date_from_str, date_to_str,
                date_from_str, date_to_str,
                date_from_str, date_to_str,
                date_from_str,
                date_from_str,
                date_from_str,
                date_from_str,
                date_from_str, date_to_str,
                self.include_internal_transfers,
            ),
        )
        return res