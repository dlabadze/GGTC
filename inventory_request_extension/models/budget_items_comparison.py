from odoo import models, fields, api, tools


class BudgetItemsComparison(models.Model):
    _name = 'budget.items.comparison'
    _description = 'Budget Items Comparison Report'
    _auto = False
    _order = 'category_id'

    category_id = fields.Many2one(
        'product.category',
        string='Category',
        readonly=True
    )
    default_budget_analytic = fields.Many2one(
        'account.analytic.account',
        string='Default Budget Analytic',
        readonly=True
    )
    request_budget_analytic = fields.Char(
        string='Request Budget Analytic',
        readonly=True
    )
    amount = fields.Float(
        string='Amount',
        readonly=True
    )

    department_id = fields.Many2one(
        'x_request_deps',
        string='Department',
        readonly=True
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    il.id,
                    pt.categ_id AS category_id,
                    pc.x_studio_many2one_field_2o6_1j1dfj1v3 AS default_budget_analytic,
                    il.budget_analytic_line_account AS request_budget_analytic,
                    il.amount AS amount,
                    ir.department_id AS department_id
                FROM inventory_line il
                LEFT JOIN product_product pp ON il.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN product_category pc ON pc.id = pt.categ_id
                LEFT JOIN account_analytic_account aaa ON aaa.id = pc.x_studio_many2one_field_2o6_1j1dfj1v3
                LEFT JOIN inventory_request ir ON il.request_id = ir.id
                WHERE 
                    (il.budget_analytic_line_account IS NULL OR il.budget_analytic_line_account = '')
                    OR (
                        il.budget_analytic_line_account IS NOT NULL
                        AND il.budget_analytic_line_account != ''
                        AND aaa.id IS NOT NULL
                        AND (
                            CASE 
                                WHEN aaa.code IS NOT NULL AND TRIM(COALESCE(aaa.code::text, '')) != '' 
                                THEN '[' || TRIM(aaa.code::text) || '] ' || TRIM(COALESCE(
                                    NULLIF(aaa.name->>'en_US', ''),
                                    NULLIF(aaa.name::text, ''),
                                    ''
                                ))
                                ELSE TRIM(COALESCE(
                                    NULLIF(aaa.name->>'en_US', ''),
                                    NULLIF(aaa.name::text, ''),
                                    ''
                                ))
                            END
                        ) != il.budget_analytic_line_account
                    )
            )
        """)

