from odoo import models, fields, api, tools


class RequestReportLine(models.Model):
    _name = 'request.report.line'
    _description = 'Request Report Line'
    _auto = False
    _order = 'category_id'

    category_id = fields.Many2one(
        'product.category',
        string='Category',
        readonly=True
    )
    budget_amount = fields.Float(
        string='Budget Amount',
        digits=(16, 2),
        readonly=True
    )
    budget_quantity = fields.Float(
        string='Budget Quantity',
        digits=(16, 2),
        readonly=True
    )
    actual_amount = fields.Float(
        string='Actual Amount',
        digits=(16, 2),
        readonly=True
    )
    actual_quantity = fields.Float(
        string='Actual Quantity',
        digits=(16, 2),
        readonly=True
    )
    diff_amount = fields.Float(
        string='Difference Amount',
        digits=(16, 2),
        readonly=True
    )
    diff_quantity = fields.Float(
        string='Difference Quantity',
        digits=(16, 2),
        readonly=True
    )
    is_negative = fields.Boolean(
        string='Is Negative',
        readonly=True,
        help='True if diff_amount or diff_quantity is negative'
    )
    active = fields.Boolean(string='Active', default=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # Create empty view initially - will be populated by wizard
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    NULL::integer AS category_id,
                    0.0 AS budget_amount,
                    0.0 AS budget_quantity,
                    0.0 AS actual_amount,
                    0.0 AS actual_quantity,
                    0.0 AS diff_amount,
                    0.0 AS diff_quantity,
                    false AS is_negative,
                    true AS active
                WHERE FALSE
            )
        """)

