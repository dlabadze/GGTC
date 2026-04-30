from odoo import models, fields, api
import logging
from datetime import date

_logger = logging.getLogger(__name__)


class SeptemberLine(models.Model):
    _name = 'september.line'
    _description = 'September Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Description', required=True)

    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)

    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )

    # New fields for pricing
    unit_price = fields.Float(
        string='Unit Price',
        default=0.0,
        digits='Product Price'
    )

    amount = fields.Float(
        string='Amount',
        compute='_compute_amount',
        store=True,
        digits='Product Price'
    )

    expected_date = fields.Date(string='Expected Date')
    notes = fields.Text(string='Notes')

    # Dynamic stage instead of static selection
    stage_id = fields.Many2one(
        'september.line.stage',
        string='Stage',
        index=True,
        copy=False
    )

    # Tags field
    tag_ids = fields.Many2many(
        'september.line.tag',
        string='Tags'
    )

    # Many2one relationship back to september request
    request_id = fields.Many2one(
        'september.request',
        string='September Request',
        ondelete='cascade'
    )

    # Related fields from request
    request_stage_id = fields.Many2one(
        related='request_id.stage_id',
        string='Request Stage',
        readonly=True
    )

    # Budget fields (renamed from x_studio fields)
    budget_main = fields.Many2one('budget.analytic', string='Budget Analytic')
    budget_name_main = fields.Many2one('account.analytic.account', string='Analytic Account')

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        """Compute the amount based on quantity and unit price"""
        for line in self:
            line.amount = line.quantity * line.unit_price

    def _find_active_budget_for_category_analytic(self, category_analytic_account):
        """
        Find active budget.analytic record and matching budget.line for given analytic account
        Returns tuple: (budget_analytic_record, budget_line_record) or (None, None)
        """
        try:
            current_date = date.today()

            # Find active budget.analytic records where current date >= date_from
            active_budgets = self.env['budget.analytic'].search([
                ('date_from', '<=', current_date),
            ], order='date_from desc')

            _logger.info(f"Found {len(active_budgets)} active budgets for current date {current_date}")

            # Look for matching budget.line in each active budget
            # Try common field names for analytic account in budget.line
            possible_field_names = [
                'account_id',  # Most common field name for analytic account
                'analytic_account_id',
                'analytic_id'
            ]

            for budget in active_budgets:
                for field_name in possible_field_names:
                    try:
                        budget_lines = self.env['budget.line'].search([
                            ('budget_analytic_id', '=', budget.id),
                            (field_name, '=', category_analytic_account.id)
                        ])

                        if budget_lines:
                            _logger.info(f"Found matching budget line in budget {budget.id} "
                                         f"for analytic account {category_analytic_account.id} "
                                         f"using field '{field_name}'")
                            return budget, budget_lines[0]  # Return first matching line
                    except Exception as field_error:
                        _logger.debug(f"Field '{field_name}' not found in budget.line: {str(field_error)}")
                        continue

            _logger.warning(f"No matching budget.line found for analytic account {category_analytic_account.id}")
            return None, None

        except Exception as e:
            _logger.error(f"Error finding active budget for category analytic: {str(e)}")
            return None, None

    def _auto_populate_budget_fields(self):
        """
        Automatically populate budget_main and budget_name_main based on product category
        """
        if not self.product_id:
            return

        try:
            # Step 1: Get product category
            product_category = self.product_id.categ_id
            if not product_category:
                _logger.warning(f"Product {self.product_id.name} has no category")
                return

            # Step 2: Get category's budget line (analytic account)
            category_analytic_account = product_category.x_studio_many2one_field_2o6_1j1dfj1v3
            if not category_analytic_account:
                _logger.warning(f"Product category {product_category.name} has no analytic account configured")
                return

            _logger.info(f"Product {self.product_id.name} -> Category {product_category.name} -> "
                         f"Analytic Account {category_analytic_account.name}")

            # Step 3: Find active budget and matching budget line
            budget_analytic, budget_line = self._find_active_budget_for_category_analytic(category_analytic_account)

            if budget_analytic and budget_line:
                # Step 4: Update budget fields
                self.budget_main = budget_analytic.id
                self.budget_name_main = category_analytic_account.id

                _logger.info(f"Auto-populated budget fields for september line {self.id}: "
                             f"budget_main={budget_analytic.name}, "
                             f"budget_name_main={category_analytic_account.name}")
            else:
                _logger.warning(f"Could not find active budget for product {self.product_id.name}")

        except Exception as e:
            _logger.error(f"Error in auto-populating budget fields: {str(e)}")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            # Set unit price from product's standard price
            self.unit_price = self.product_id.standard_price

            # Auto-populate budget fields based on product category
            self._auto_populate_budget_fields()

            # Set default stage if not set
            if not self.stage_id:
                default_stage = self.env['september.line.stage'].search([('active', '=', True)], limit=1,
                                                                        order='sequence')
                if default_stage:
                    self.stage_id = default_stage.id

    @api.onchange('quantity', 'unit_price')
    def _onchange_quantity_unit_price(self):
        """Trigger amount recalculation when quantity or unit price changes"""
        # The compute method will handle the calculation automatically
        pass

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Set default stage if not provided
            if not vals.get('stage_id'):
                default_stage = self.env['september.line.stage'].search([('active', '=', True)], limit=1,
                                                                        order='sequence')
                if default_stage:
                    vals['stage_id'] = default_stage.id

        records = super().create(vals_list)

        # Auto-populate budget fields for newly created records
        for record in records:
            if record.product_id and not (record.budget_main and record.budget_name_main):
                record._auto_populate_budget_fields()

        return records

    def write(self, vals):
        """Override write method"""
        result = super().write(vals)

        # Auto-populate budget fields if product_id changed and budget fields are empty
        if 'product_id' in vals:
            for record in self:
                if record.product_id and not (record.budget_main and record.budget_name_main):
                    record._auto_populate_budget_fields()

        return result