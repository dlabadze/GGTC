from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging

_logger = logging.getLogger(__name__)


class RequestReportWizard(models.TransientModel):
    _name = 'request.report.wizard'
    _description = 'Request Report Wizard'

    # Generates the SQL view `request_report_line` used by the report UI.
    # In particular, `request.report.line.budget_amount` is calculated from
    # `budgeting_line` using a per-department quantity basis field (`budget_qty_field`),
    # and the full formula + mapping are documented in:
    # `REQUEST_REPORT_WIZARD_BUDGET_AMOUNT.md`.

    budget_request_id = fields.Many2one(
        'budgeting.request',
        string='Budget Request',
        required=True
    )
    department_id = fields.Many2one(
        'x_request_deps',
        string='Department',
        required=True
    )

    def action_generate_report(self):
        """Generate report using SQL view (runs with sudo for non-admin users)."""
        self.ensure_one()
        self = self.sudo()

        # Get department code from department_id
        dep_code = False

        # First, try to get dep_code from any x_studio_ field on department
        if self.department_id:
            for field_name in self.department_id._fields:
                if field_name.startswith('x_studio_'):
                    try:
                        field_value = getattr(self.department_id, field_name)
                        if field_value and isinstance(field_value, str) and field_value in ["ცფ", "ცფს", "კს", "ჩფ", "ყუ", "დფ", "ოდო", "მეტ"]:
                            dep_code = field_value
                            break
                    except:
                        pass
        
        # If not found, try direct dep_code field
        if not dep_code and hasattr(self.department_id, 'dep_code'):
            dep_code = self.department_id.dep_code
        
        # If still not found, try to get it from an inventory.request with this department
        if not dep_code:
            sample_request = self.env['inventory.request'].sudo().search([
                ('department_id', '=', self.department_id.id)
            ], limit=1)
            if sample_request and hasattr(sample_request, 'dep_code'):
                dep_code = sample_request.dep_code
        
        # Get year from budget_request_id.request_date
        budget_year = self.budget_request_id.request_date.year if self.budget_request_id.request_date else None
        if not budget_year:
            raise UserError(_("Budget Request must have a request date."))
        
        # Prepare date range
        year_start = fields.Datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).replace(year=budget_year)
        year_end = fields.Datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).replace(year=budget_year + 1)
        year_start_str = year_start.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        year_end_str = year_end.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        
        # Determine which budget quantity field to use based on dep_code
        budget_qty_field = 'quantity'
        if dep_code == "ცფ":
            budget_qty_field = 'x_studio_float_field_607_1j3r255vi'
        elif dep_code == "ცფს":
            budget_qty_field = 'x_studio_float_field_971_1j3r2i8ah'
        elif dep_code == "კს":
            budget_qty_field = 'x_studio_float_field_3bu_1j3r2insu'
        elif dep_code == "ჩფ":
            budget_qty_field = 'x_studio_float_field_7rg_1j3r2j0fc'
        elif dep_code == "ყუ":
            budget_qty_field = 'x_studio_float_field_1p5_1j3r2j88f'
        elif dep_code == "დფ":
            budget_qty_field = 'x_studio_float_field_349_1j3r2jgm8'
        elif dep_code == "ოდო":
            budget_qty_field = 'x_studio_float_field_366_1j3r2jrui'
        elif dep_code == "მეტ":
            budget_qty_field = 'x_studio_float_field_9r_1j3r2kjpn'
        
        try:
            self.env.cr.execute("SAVEPOINT request_report_savepoint")
            self.env.cr.execute("DROP VIEW IF EXISTS request_report_line")
            
            # Build SQL query
            sql_query = f"""
                CREATE OR REPLACE VIEW request_report_line AS (
                    WITH actual_data AS (
                        SELECT
                            pt.categ_id AS category_id,
                            SUM(COALESCE(il.amount, 0.0)) AS actual_amount,
                            SUM(COALESCE(il.quantity, 0.0)) AS actual_quantity
                        FROM inventory_line il
                        JOIN inventory_request ir ON il.request_id = ir.id
                        LEFT JOIN product_product pp ON il.product_id = pp.id
                        LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                        WHERE ir.department_id = %s
                          AND il.create_date >= %s
                          AND il.create_date < %s
                          AND ir.x_studio_selection_field_6ca_1j76p9boc = 'მარაგები'
                          AND ir.september_request_id IS NULL
                        GROUP BY pt.categ_id
                    )
                    SELECT
                        row_number() OVER () AS id,
                        ad.category_id AS category_id,
                        COALESCE(bd.budget_amt, 0.0) AS budget_amount,
                        COALESCE(bd.budget_quantity, 0.0) AS budget_quantity,
                        COALESCE(ad.actual_amount, 0.0) AS actual_amount,
                        COALESCE(ad.actual_quantity, 0.0) AS actual_quantity,
                        COALESCE(bd.budget_amt, 0.0) - COALESCE(ad.actual_amount, 0.0) AS diff_amount,
                        COALESCE(bd.budget_quantity, 0.0) - COALESCE(ad.actual_quantity, 0.0) AS diff_quantity,
                        CASE 
                            WHEN (COALESCE(bd.budget_amt, 0.0) - COALESCE(ad.actual_amount, 0.0)) < 0 
                            OR (COALESCE(bd.budget_quantity, 0.0) - COALESCE(ad.actual_quantity, 0.0)) < 0 
                            THEN 1 
                            ELSE 0 
                        END AS is_negative,
                        true AS active
                    FROM actual_data ad
                    LEFT JOIN (
                        SELECT
                            pt.categ_id AS category_id,
                            SUM(COALESCE(bl.{budget_qty_field}, bl.quantity, 0.0)) AS budget_quantity,
                            SUM(
                                COALESCE(bl.{budget_qty_field}, bl.quantity, 0.0) *
                                CASE
                                    WHEN (COALESCE(bl.x_studio_float_field_38e_1j1ftullr, 0.0) + COALESCE(bl.x_studio_float_field_8ss_1j1ftvflr, 0.0)) > 0
                                    THEN
                                        (COALESCE(bl.x_studio_float_field_4nk_1j1fvng8q, 0.0) /
                                        (COALESCE(bl.x_studio_float_field_38e_1j1ftullr, 0.0) + COALESCE(bl.x_studio_float_field_8ss_1j1ftvflr, 0.0)))
                                    ELSE 0.0
                                END
                            ) AS budget_amt
                        FROM budgeting_line bl
                        LEFT JOIN product_product pp ON bl.product_id = pp.id
                        LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                        WHERE bl.request_id = %s
                        GROUP BY pt.categ_id
                    ) bd ON ad.category_id = bd.category_id
                    WHERE ad.category_id IS NOT NULL
                )
            """
            
            self.env.cr.execute(
                sql_query,
                (
                    self.department_id.id,
                    year_start_str,
                    year_end_str,
                    self.budget_request_id.id,
                )
            )
            
            self.env.cr.execute("RELEASE SAVEPOINT request_report_savepoint")
        except Exception as exc:
            self.env.cr.execute("ROLLBACK TO SAVEPOINT request_report_savepoint")
            _logger.error("Error generating report: %s", exc)
            raise UserError(_("Error generating report: %s") % str(exc))
        
        # Return action to view the report
        action = self.env.ref('inventory_request_extension.action_request_report_line').sudo().read()[0]
        action['domain'] = []
        return action

