from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class BudgetingLine(models.Model):
    _name = 'budgeting.line'
    _description = 'Budgeting Line'
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
        'budgeting.line.stage',
        string='Stage',
        index=True,
        copy=False
    )

    # Tags field
    tag_ids = fields.Many2many(
        'budgeting.line.tag',
        string='Tags'
    )

    # Many2one relationship back to budgeting request
    request_id = fields.Many2one(
        'budgeting.request',
        string='Budgeting Request',
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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            # Set unit price from product's standard price
            self.unit_price = self.product_id.standard_price
            # Set default stage if not set
            if not self.stage_id:
                default_stage = self.env['budgeting.line.stage'].search([('active', '=', True)], limit=1,
                                                                        order='sequence')
                if default_stage:
                    self.stage_id = default_stage.id

    @api.onchange('quantity', 'unit_price')
    def _onchange_quantity_unit_price(self):
        """Trigger amount recalculation when quantity or unit price changes"""
        # The compute method will handle the calculation automatically
        pass

    @api.onchange('amount')
    def _onchange_amount(self):
        """Update budget line when amount changes"""
        self._update_budget_reservation()

    def _update_budget_reservation_combined(self, budget_analytic_id, analytic_account_id):
        """
        Update budget lines with the combined total of all budgeting lines
        for the same budget analytic and analytic account combination
        """
        _logger.info(f"Starting combined budget reservation update for budget_analytic_id={budget_analytic_id}, "
                     f"analytic_account_id={analytic_account_id}")

        # Step 1: Get all budgeting lines with the same budget combination
        all_budgeting_lines = self.env['budgeting.line'].search([
            ('budget_main', '=', budget_analytic_id),
            ('budget_name_main', '=', analytic_account_id)
        ])

        # Step 2: Calculate total amount from all matching budgeting lines
        total_amount = sum(line.amount for line in all_budgeting_lines)

        _logger.info(f"Found {len(all_budgeting_lines)} budgeting lines with combined total amount: {total_amount}")

        # Step 3: Find all budget lines for this combination
        budget_lines = self.env['budget.line'].search([
            ('budget_analytic_id', '=', budget_analytic_id),
            ('account_id', '=', analytic_account_id)
        ])

        if not budget_lines:
            _logger.warning(f"No budget.line records found with budget_analytic_id={budget_analytic_id} "
                            f"and account_id={analytic_account_id}")
            return

        _logger.info(f"Found {len(budget_lines)} budget.line records to update with total amount: {total_amount}")

        # Step 4: Update ALL matching budget lines with the total amount
        updated_count = 0
        for budget_line in budget_lines:
            try:
                _logger.info(f"Updating budget.line {budget_line.id} with total reserved amount: {total_amount}")

                budget_line.write({
                    'x_studio_reserved': total_amount
                })
                updated_count += 1

                _logger.info(f"Successfully updated budget.line {budget_line.id} "
                             f"with reserved amount: {total_amount}")
            except Exception as e:
                _logger.error(f"Error updating budget.line {budget_line.id}: {str(e)}")

        _logger.info(f"Combined budget reservation update completed. "
                     f"Updated {updated_count} out of {len(budget_lines)} budget lines. "
                     f"Set reserved amount to {total_amount} for all matching budget lines.")

    def _update_budget_reservation(self):
        """Update the reserved field in budget.line model based on analytic account"""
        if not self.budget_main or not self.budget_name_main:
            _logger.warning(f"Budget fields missing for budgeting line {self.id}: "
                            f"budget_main={self.budget_main}, budget_name_main={self.budget_name_main}")
            return

        # Use the combined approach
        self._update_budget_reservation_combined(self.budget_main.id, self.budget_name_main.id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Set default stage if not provided
            if not vals.get('stage_id'):
                default_stage = self.env['budgeting.line.stage'].search([('active', '=', True)], limit=1,
                                                                        order='sequence')
                if default_stage:
                    vals['stage_id'] = default_stage.id

        records = super().create(vals_list)

        # Update budget reservation for newly created records
        # Group by budget combination to avoid multiple updates
        budget_combinations = set()
        for record in records:
            if record.budget_main and record.budget_name_main:
                budget_combinations.add((record.budget_main.id, record.budget_name_main.id))

        # Update each unique budget combination once
        for budget_analytic_id, analytic_account_id in budget_combinations:
            self._update_budget_reservation_combined(budget_analytic_id, analytic_account_id)

        return records

    def write(self, vals):
        """Override write to update budget when amount-related fields change"""
        # Store old budget combinations before update
        old_budget_combinations = set()
        for record in self:
            if record.budget_main and record.budget_name_main:
                old_budget_combinations.add((record.budget_main.id, record.budget_name_main.id))

        result = super().write(vals)

        # Check if any amount-related fields were updated
        if any(field in vals for field in ['amount', 'quantity', 'unit_price', 'budget_main', 'budget_name_main']):
            # Get new budget combinations after update
            new_budget_combinations = set()
            for record in self:
                if record.budget_main and record.budget_name_main:
                    new_budget_combinations.add((record.budget_main.id, record.budget_name_main.id))

            # Update all affected budget combinations (both old and new)
            all_combinations = old_budget_combinations | new_budget_combinations
            for budget_analytic_id, analytic_account_id in all_combinations:
                self._update_budget_reservation_combined(budget_analytic_id, analytic_account_id)

        return result

    def unlink(self):
        """Override unlink to update budget when records are deleted"""
        # Store budget combinations before deletion
        budget_combinations = set()
        for record in self:
            if record.budget_main and record.budget_name_main:
                budget_combinations.add((record.budget_main.id, record.budget_name_main.id))

        result = super().unlink()

        # Update affected budget combinations after deletion
        for budget_analytic_id, analytic_account_id in budget_combinations:
            self._update_budget_reservation_combined(budget_analytic_id, analytic_account_id)

        return result

from odoo import models, fields, api


class BudgetingRequestStage(models.Model):
    _name = 'budgeting.request.stage'
    _description = 'Budgeting Request Stage'
    _order = 'sequence, name'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    fold = fields.Boolean(string='Folded in Kanban',
                          help="This stage is folded in the kanban view when there are no records in that stage to display.")

    # Color for progress bar
    color = fields.Integer(string='Color Index', default=0)

    # Whether this stage is done
    is_done = fields.Boolean(string='Is Done Stage',
                             help="If checked, requests in this stage are considered as done.")


class BudgetingRequestTag(models.Model):
    _name = 'budgeting.request.tag'
    _description = 'Budgeting Request Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)


class BudgetingRequest(models.Model):
    _name = 'budgeting.request'
    _description = 'Budgeting Request'
    _order = 'create_date desc'

    # Computed state field for Studio compatibility
    state = fields.Char(
        string='Status',
        compute='_compute_state',
        store=False
    )

    @api.depends('stage_id')
    def _compute_state(self):
        for record in self:
            record.state = record.stage_id.name if record.stage_id else 'draft'

    name = fields.Char(string='Request Number', required=True, copy=False, readonly=True, default='New')

    # Dynamic stage instead of static selection
    stage_id = fields.Many2one(
        'budgeting.request.stage',
        string='Stage',
        index=True,
        copy=False,
        group_expand='_read_group_stage_ids'  # This ensures empty stages appear
    )

    # Tags field
    tag_ids = fields.Many2many(
        'budgeting.request.tag',
        string='Tags'
    )

    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user,
                                   required=True)
    department_id = fields.Many2one('hr.department', string='Department')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Very High')
    ], string='Priority', default='1')

    description = fields.Text(string='Description')
    line_ids = fields.One2many('budgeting.line', 'request_id', string='Budgeting Lines')

    # Computed fields
    total_lines = fields.Integer(string='Total Lines', compute='_compute_totals', store=True)

    @api.depends('line_ids')
    def _compute_totals(self):
        for request in self:
            request.total_lines = len(request.line_ids)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        """Always return all active stages, even if they're empty"""
        # Get all active stages
        all_stages = self.env['budgeting.request.stage'].search([('active', '=', True)], order='sequence, name')
        return all_stages

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('budgeting.request') or 'New'
            # Set default stage if not provided
            if not vals.get('stage_id'):
                default_stage = self.env['budgeting.request.stage'].search([('active', '=', True)], limit=1,
                                                                           order='sequence')
                if default_stage:
                    vals['stage_id'] = default_stage.id
        return super().create(vals_list)

from odoo import models, fields, api


class BudgetingRequestStage(models.Model):
    _name = 'budgeting.request.stage'
    _description = 'Budgeting Request Stage'
    _order = 'sequence, name'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    fold = fields.Boolean(string='Folded in Kanban', default=False,
                          help="This stage is folded in the kanban view when there are no records in that stage to display.")
    active = fields.Boolean(string='Active', default=True)

    # Color for kanban view
    color = fields.Integer(string='Color Index', default=0)


class BudgetingLineStage(models.Model):
    _name = 'budgeting.line.stage'
    _description = 'Budgeting Line Stage'
    _order = 'sequence, name'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    fold = fields.Boolean(string='Folded in Kanban', default=False,
                          help="This stage is folded in the kanban view when there are no records in that stage to display.")
    active = fields.Boolean(string='Active', default=True)

    # Color for kanban view
    color = fields.Integer(string='Color Index', default=0)

from odoo import models, fields, api


class BudgetingRequestTag(models.Model):
    _name = 'budgeting.request.tag'
    _description = 'Budgeting Request Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)


class BudgetingLineTag(models.Model):
    _name = 'budgeting.line.tag'
    _description = 'Budgeting Line Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)