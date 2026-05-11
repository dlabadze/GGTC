from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import date

_logger = logging.getLogger(__name__)


class AgreementVendorSelectionWizard(models.TransientModel):
    """Separate wizard for creating purchase agreements directly from inventory lines"""
    _name = 'agreement.vendor.selection.wizard'
    _description = 'Purchase Agreement Vendor Selection Wizard'

    vendor_id = fields.Many2one(
        'res.partner',
        string='Select Vendor',
    )

    inventory_line_ids = fields.Many2many(
        'inventory.line',
        string='Inventory Lines'
    )

    line_count = fields.Integer(
        string='Number of Lines',
        compute='_compute_line_count'
    )

    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        digits='Product Price'
    )

    @api.depends('inventory_line_ids')
    def _compute_line_count(self):
        for wizard in self:
            wizard.line_count = len(wizard.inventory_line_ids)

    @api.depends('inventory_line_ids')
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = sum(wizard.inventory_line_ids.mapped('amount'))

    def action_create_purchase_agreement(self):
        """Create Purchase Agreement with the selected vendor"""
        if not self.vendor_id:
            raise UserError(_('Please select a vendor.'))

        if not self.inventory_line_ids:
            raise UserError(_('No inventory lines found.'))

        _logger.info(f"CHECK FLAG FOR ME 2")

        # Get purchase method from inventory lines
        purchase_methods = set()
        for line in self.inventory_line_ids:
            if line.x_studio_purchase_plan_line and line.x_studio_purchase_plan_line.purchase_method_id:
                purchase_methods.add(line.x_studio_purchase_plan_line.purchase_method_id.id)

        purchase_method = None
        if purchase_methods:
            method_id = list(purchase_methods)[0]
            purchase_method = self.env['purchase.method'].browse(method_id)

        # Create Purchase Agreement directly
        agreement = self.inventory_line_ids._create_purchase_agreement_direct(
            self.inventory_line_ids,
            self.vendor_id,
            purchase_method
        )

        # Update tender status on selected inventory lines
        self.inventory_line_ids.write({'x_studio_tender_status': 'Contract Status'})
        _logger.info(
            f"Updated tender status to 'ხელშეკრულება დადებულია' for {len(self.inventory_line_ids)} inventory lines (direct agreement creation)")

        return self.inventory_line_ids._return_agreement_action(agreement)

class VendorSelectionWizard(models.TransientModel):
    _name = 'vendor.selection.wizard'
    _description = 'Vendor Selection Wizard'

    vendor_id = fields.Many2one(
        'res.partner',
        string='Select Vendor'
    )

    inventory_line_ids = fields.Many2many(
        'inventory.line',
        string='Inventory Lines'
    )

    def action_create_rfq_with_selected_vendor(self):
        """Create RFQ with the selected vendor"""
        if not self.vendor_id:
            raise UserError(_('Please select a vendor.'))

        if not self.inventory_line_ids:
            raise UserError(_('No inventory lines found.'))

        # Get purchase method from inventory lines
        purchase_methods = set()
        for line in self.inventory_line_ids:
            if line.x_studio_purchase_plan_line and line.x_studio_purchase_plan_line.purchase_method_id:
                purchase_methods.add(line.x_studio_purchase_plan_line.purchase_method_id.id)

        purchase_method = None
        if purchase_methods:
            method_id = list(purchase_methods)[0]
            purchase_method = self.env['purchase.method'].browse(method_id)

        # Create RFQ using the existing method from inventory.line
        rfq = self.inventory_line_ids._create_single_rfq(
            self.inventory_line_ids,
            self.vendor_id,
            purchase_method
        )

        # NEW: Check and update parent request status if all purchase lines have RFQs
        self.inventory_line_ids._check_and_update_parent_request_status()

        return self.inventory_line_ids._return_rfq_action(rfq)


class InventoryLine(models.Model):
    _name = 'inventory.line'
    _description = 'Inventory Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Description', required=True)

    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)

    x_studio_purchase_plan = fields.Many2one('purchase.plan', string='Purchase Plan')
    x_studio_purchase_plan_line = fields.Many2one('purchase.plan.line', string='Purchase Plan Line')

    budget_analytic = fields.Many2one('budget.analytic', string='budget analytic')
    budget_analytic_line = fields.Many2one('budget.line', string='budget analytic line')\

    budget_analytic_line_account = fields.Char(
        string='Budget Account',
        compute='_compute_budget_analytic_line_account',
        store=True
    )

    @api.depends('budget_analytic_line', 'budget_analytic_line.account_id')
    def _compute_budget_analytic_line_account(self):
        for record in self:
            if record.budget_analytic_line and record.budget_analytic_line.account_id:
                account = record.budget_analytic_line.account_id
                if account.code:
                    record.budget_analytic_line_account = f"[{account.code}] {account.name}"
                else:
                    record.budget_analytic_line_account = account.name
            else:
                record.budget_analytic_line_account = False

    # Field to store request number from parent request
    x_studio_ = fields.Char(string='Request Number', related='request_id.x_studio_request_number', store=True,
                            readonly=True)

    request_date = fields.Date(
        string='Request Date',
        related='request_id.request_date',
        store=True,
        readonly=True,
        help='Request date copied from parent inventory request'
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )

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

    # Fields for tracking contracted quantities and amounts
    contracted_quantity = fields.Float(
        string='Contracted Quantity',
        default=0.0,
        readonly=True,
        help='Total quantity already contracted in purchase agreements'
    )

    contracted_amount = fields.Float(
        string='Contracted Amount',
        default=0.0,
        readonly=True,
        digits='Product Price',
        help='Total amount already contracted in purchase agreements'
    )

    remaining_quantity = fields.Float(
        string='Remaining Quantity',
        compute='_compute_remaining_values',
        store=True,
        help='Quantity not yet contracted'
    )

    remaining_amount = fields.Float(
        string='Remaining Amount',
        compute='_compute_remaining_values',
        store=True,
        digits='Product Price',
        help='Amount not yet contracted'
    )

    expected_date = fields.Date(string='Expected Date')
    notes = fields.Text(string='Notes')

    stage_id = fields.Many2one(
        'inventory.line.stage',
        string='Stage',
        index=True,
        copy=False
    )

    tag_ids = fields.Many2many(
        'inventory.line.tag',
        string='Tags'
    )

    request_id = fields.Many2one(
        'inventory.request',
        string='Inventory Request',
        ondelete='cascade'
    )

    request_stage_id = fields.Many2one(
        related='request_id.stage_id',
        string='Request Stage',
        readonly=True
    )

    budget_main = fields.Many2one('budget.analytic', string='Budget Analytic')
    budget_name_main = fields.Many2one('account.analytic.account', string='Analytic Account')

    @api.onchange('budget_analytic')
    def _onchange_budget_analytic_set_main(self):
        for record in self:
            if record.budget_analytic:
                record.budget_main = record.budget_analytic
            else:
                record.budget_main = False

    @api.onchange('budget_analytic_line')
    def _onchange_budget_analytic_line_set_account(self):
        for record in self:
            if record.budget_analytic_line and record.budget_analytic_line.account_id:
                record.budget_name_main = record.budget_analytic_line.account_id
            else:
                record.budget_name_main = False

    @api.onchange('budget_analytic_line')
    def _onchange_budget_analytic_line_check_resource(self):
        for record in self:
            if record.budget_analytic_line and record.budget_analytic_line.request_resource <= 0:
                raise UserError(_(
                    'Cannot select budget line "%s" because its Request Resource is %.2f. '
                    'The Request Resource must be greater than 0.',
                    record.budget_analytic_line.display_name,
                    record.budget_analytic_line.request_resource,
                ))

    @api.constrains('budget_analytic_line')
    def _check_budget_analytic_line_request_resource(self):
        for record in self:
            if record.budget_analytic_line and record.budget_analytic_line.request_resource <= 0:
                raise UserError(_(
                    'Cannot save inventory line with budget line "%s" because its Request Resource is %.2f. '
                    'The Request Resource must be greater than 0.',
                    record.budget_analytic_line.display_name,
                    record.budget_analytic_line.request_resource,
                ))

    def _check_and_update_parent_request_status(self):
        """
        Check if all inventory lines with x_studio_purchase=True have RFQs created,
        and update parent request status to 'ხელშეკრულება გაფორმებულია' if so.
        """
        for line in self:
            if not line.request_id:
                continue

            parent_request = line.request_id

            # Find all inventory lines of the parent request where x_studio_purchase is True
            purchase_lines = parent_request.line_ids.filtered(lambda l: l.x_studio_purchase == True)

            if not purchase_lines:
                _logger.info(f"No purchase lines found for request {parent_request.id}")
                continue

            # Check if all purchase lines have RFQs created
            all_have_rfqs = True
            for purchase_line in purchase_lines:
                # Check if this line has any associated RFQ/Purchase Order
                rfqs = self.env['purchase.order'].search([
                    ('inventory_line_ids', 'in', purchase_line.id)
                ])

                if not rfqs:
                    all_have_rfqs = False
                    _logger.info(f"Line {purchase_line.id} does not have an RFQ yet")
                    break

            # If all purchase lines have RFQs, update the parent request status
            if all_have_rfqs:
                try:
                    parent_request.write({
                            'status_request': 'yes'
                    })
                    _logger.info(
                        f"Updated parent request {parent_request.id} status to 'ხელშეკრულება გაფორმებულია' "
                        f"as all {len(purchase_lines)} purchase lines have RFQs created"
                    )
                except Exception as e:
                    _logger.error(f"Error updating parent request status: {str(e)}")
            else:
                _logger.info(
                    f"Not all purchase lines have RFQs yet for request {parent_request.id}. "
                    f"Total purchase lines: {len(purchase_lines)}"
                )

    @api.onchange('x_studio_purchase_plan')
    def _onchange_purchase_plan(self):
        """Filter purchase plan lines based on selected purchase plan"""
        if self.x_studio_purchase_plan:
            plan_line_fields = self.env['purchase.plan.line'].fields_get()
            linking_field = None

            for field_name, field_info in plan_line_fields.items():
                if field_info.get('relation') == 'purchase.plan':
                    linking_field = field_name
                    break

            if linking_field:
                return {
                    'domain': {
                        'x_studio_purchase_plan_line': [
                            (linking_field, '=', self.x_studio_purchase_plan.id)
                        ]
                    },
                    'value': {
                        'x_studio_purchase_plan_line': False
                    }
                }
        else:
            return {
                'domain': {
                    'x_studio_purchase_plan_line': [('id', '=', False)]
                },
                'value': {
                    'x_studio_purchase_plan_line': False
                }
            }

    @api.onchange('quantity', 'unit_price')
    def _onchange_quantity_unit_price(self):
        """Update purchase plan line when quantity or unit price changes (UI only)"""
        if self._context.get('disable_purchase_plan_update'):
            return

        current_amount = self.quantity * self.unit_price
        self._update_purchase_plan_reservation_with_amount(current_amount)

    def _update_purchase_plan_reservation_with_amount(self, new_amount):
        """Update purchase plan reservation with a specific amount value"""
        if not self.x_studio_purchase_plan or not self.x_studio_purchase_plan_line:
            _logger.warning(f"Purchase plan fields missing for inventory line {self.id}")
            return

        _logger.info(f"Updating purchase plan reservation with amount: {new_amount} for line {self.id}")

        other_lines = self.env['inventory.line'].search([
            ('x_studio_purchase_plan', '=', self.x_studio_purchase_plan.id),
            ('x_studio_purchase_plan_line', '=', self.x_studio_purchase_plan_line.id),
            ('id', '!=', self.id)
        ])

        total_amount = sum(line.amount for line in other_lines) + new_amount
        purchase_plan_line = self.env['purchase.plan.line'].browse(self.x_studio_purchase_plan_line.id)

        if not purchase_plan_line.exists():
            return

        try:
            purchase_plan_line.with_context(disable_purchase_plan_update=True).write({
                'x_studio_reserved': total_amount
            })

            remaining_resource = (purchase_plan_line.pu_ac_am or 0.0) - total_amount
            purchase_plan_line.with_context(disable_purchase_plan_update=True).write({
                'x_studio_remaining_resource': remaining_resource
            })
        except Exception as e:
            _logger.error(f"Error updating purchase.plan.line {purchase_plan_line.id}: {str(e)}")


    def _update_purchase_plan_reservation_combined(self, purchase_plan_id, purchase_plan_line_id):
        """Update purchase plan lines with combined total"""
        all_inventory_lines = self.env['inventory.line'].search([
            ('x_studio_purchase_plan', '=', purchase_plan_id),
            ('x_studio_purchase_plan_line', '=', purchase_plan_line_id)
        ])

        total_amount = sum(line.amount for line in all_inventory_lines)
        purchase_plan_line = self.env['purchase.plan.line'].browse(purchase_plan_line_id)

        if not purchase_plan_line.exists():
            return

        try:
            purchase_plan_line.with_context(disable_purchase_plan_update=True).write({
                'x_studio_reserved': total_amount
            })

            remaining_resource = (purchase_plan_line.pu_ac_am or 0.0) - total_amount
            purchase_plan_line.with_context(disable_purchase_plan_update=True).write({
                'x_studio_remaining_resource': remaining_resource
            })
        except Exception as e:
            _logger.error(f"Error updating purchase.plan.line: {str(e)}")

    def _get_line_reservation_amount(self, amount=None):
        """
        Returns the effective amount for x_studio_reserved calculation on budget.line.
        If x_studio_purchase is True and budget_analytic_line_account does not contain
        '2/10' or '2/12/3', divides the amount by 1.18 (VAT exclusion).
        """
        use_amount = amount if amount is not None else self.amount
        account = self.budget_analytic_line_account or ''
        if self.x_studio_purchase and '2/10' not in account and '2/12/3' not in account:
            return use_amount / 1.18
        return use_amount

    def _update_budget_line_reservation_with_amount(self, new_amount):
        """Update budget line reservation with a specific amount value"""
        if not self.budget_analytic or not self.budget_analytic_line:
            _logger.warning(f"Budget fields missing for inventory line {self.id}")
            return

        # Check if september_request_id is filled - if filled, skip update
        if self.request_id and hasattr(self.request_id, 'september_request_ids') and self.request_id.september_request_ids:
            _logger.warning(f"september_request_ids is filled for inventory line {self.id}, skipping x_studio_reserved update")
            return

        _logger.info(f"Updating budget line reservation with amount: {new_amount} for line {self.id}")

        other_lines = self.env['inventory.line'].search([
            ('budget_analytic', '=', self.budget_analytic.id),
            ('budget_analytic_line', '=', self.budget_analytic_line.id),
            ('id', '!=', self.id)
        ])

        total_amount = sum(line._get_line_reservation_amount() for line in other_lines) + self._get_line_reservation_amount(new_amount)
        budget_line = self.env['budget.line'].browse(self.budget_analytic_line.id)

        if not budget_line.exists():
            return

        try:
            request_resource = budget_line.budget_amount - total_amount
            budget_line.write({
                'x_studio_reserved': total_amount,
                'request_resource': request_resource
            })
            _logger.info(
                f"Successfully updated budget.line {budget_line.id} with reserved amount: {total_amount}, request_source: {request_resource}")
        except Exception as e:
            _logger.error(f"Error updating budget.line {budget_line.id}: {str(e)}")

    def _update_budget_line_reservation_combined(self, budget_analytic_id, budget_line_id):
        """Update budget line with combined total"""
        all_inventory_lines = self.env['inventory.line'].search([
            ('budget_analytic', '=', budget_analytic_id),
            ('budget_analytic_line', '=', budget_line_id)
        ])

        # Filter only lines WITHOUT september_request_id filled
        valid_lines = all_inventory_lines.filtered(
            lambda line: not line.request_id or
            not hasattr(line.request_id, 'september_request_ids') or
            not line.request_id.september_request_ids
        )

        # Calculate total amount (will be 0 if no valid lines)
        # Lines with x_studio_purchase=True and account not containing '2/10' or '2/12/3' are divided by 1.18 (VAT exclusion)
        total_amount = sum(line._get_line_reservation_amount() for line in valid_lines) if valid_lines else 0.0

        if not valid_lines:
            _logger.info(f"No inventory lines without september_request_ids found for budget line {budget_line_id}, setting x_studio_reserved to 0")

        budget_line = self.env['budget.line'].browse(budget_line_id)

        if not budget_line.exists():
            return

        try:
            request_resource = budget_line.budget_amount - total_amount
            budget_line.write({
                'x_studio_reserved': total_amount,
                'request_resource': request_resource
            })
            _logger.info(
                f"Successfully updated budget.line {budget_line_id} with reserved amount: {total_amount}, request_resource: {request_resource}")
        except Exception as e:
            _logger.error(f"Error updating budget.line {budget_line_id}: {str(e)}")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('stage_id'):
                default_stage = self.env['inventory.line.stage'].search([('active', '=', True)], limit=1,
                                                                        order='sequence')
                if default_stage:
                    vals['stage_id'] = default_stage.id

        records = super().create(vals_list)

        # Auto-fill budget_main from budget_analytic
        for record in records:
            if record.budget_analytic and not record.budget_main:
                record.budget_main = record.budget_analytic

        # Auto-fill budget_name_main from budget_analytic_line.account_id
        for record in records:
            if record.budget_analytic_line and record.budget_analytic_line.account_id and not record.budget_name_main:
                record.budget_name_main = record.budget_analytic_line.account_id

        for record in records:
            if record.product_id and not (record.budget_main and record.budget_name_main):
                record._auto_populate_budget_fields()

        # Update purchase plan reservations
        purchase_plan_combinations = set()
        for record in records:
            if record.x_studio_purchase_plan and record.x_studio_purchase_plan_line:
                purchase_plan_combinations.add(
                    (record.x_studio_purchase_plan.id, record.x_studio_purchase_plan_line.id))

        for purchase_plan_id, purchase_plan_line_id in purchase_plan_combinations:
            records._update_purchase_plan_reservation_combined(purchase_plan_id, purchase_plan_line_id)

        # Update budget line reservations
        budget_line_combinations = set()
        for record in records:
            if record.budget_analytic and record.budget_analytic_line:
                budget_line_combinations.add((record.budget_analytic.id, record.budget_analytic_line.id))

        for budget_analytic_id, budget_line_id in budget_line_combinations:
            records._update_budget_line_reservation_combined(budget_analytic_id, budget_line_id)

        return records

    def write(self, vals):
        # Store old combinations before update
        old_purchase_plan_combinations = set()
        old_budget_line_combinations = set()

        for record in self:
            if record.x_studio_purchase_plan and record.x_studio_purchase_plan_line:
                old_purchase_plan_combinations.add(
                    (record.x_studio_purchase_plan.id, record.x_studio_purchase_plan_line.id))
            if record.budget_analytic and record.budget_analytic_line:
                old_budget_line_combinations.add((record.budget_analytic.id, record.budget_analytic_line.id))

        result = super().write(vals)

        # Auto-fill budget_main when budget_analytic changes
        if 'budget_analytic' in vals:
            for record in self:
                if record.budget_analytic:
                    record.budget_main = record.budget_analytic
                else:
                    record.budget_main = False

        # Auto-fill budget_name_main when budget_analytic_line changes
        if 'budget_analytic_line' in vals:
            for record in self:
                if record.budget_analytic_line and record.budget_analytic_line.account_id:
                    record.budget_name_main = record.budget_analytic_line.account_id
                else:
                    record.budget_name_main = False

        if 'product_id' in vals:
            for record in self:
                if record.product_id and not (record.budget_main and record.budget_name_main):
                    record._auto_populate_budget_fields()

        # Check if any relevant fields were updated
        purchase_plan_fields = ['amount', 'quantity', 'unit_price', 'x_studio_purchase_plan',
                                'x_studio_purchase_plan_line']
        budget_fields = ['amount', 'quantity', 'unit_price', 'budget_analytic', 'budget_analytic_line']

        if any(field in vals for field in purchase_plan_fields):
            # Update purchase plan reservations
            new_purchase_plan_combinations = set()
            for record in self:
                if record.x_studio_purchase_plan and record.x_studio_purchase_plan_line:
                    new_purchase_plan_combinations.add(
                        (record.x_studio_purchase_plan.id, record.x_studio_purchase_plan_line.id))

            all_purchase_combinations = old_purchase_plan_combinations | new_purchase_plan_combinations
            for purchase_plan_id, purchase_plan_line_id in all_purchase_combinations:
                self._update_purchase_plan_reservation_combined(purchase_plan_id, purchase_plan_line_id)

        if any(field in vals for field in budget_fields):
            # Update budget line reservations
            new_budget_line_combinations = set()
            for record in self:
                if record.budget_analytic and record.budget_analytic_line:
                    new_budget_line_combinations.add((record.budget_analytic.id, record.budget_analytic_line.id))

            all_budget_combinations = old_budget_line_combinations | new_budget_line_combinations
            for budget_analytic_id, budget_line_id in all_budget_combinations:
                self._update_budget_line_reservation_combined(budget_analytic_id, budget_line_id)

        return result

    def unlink(self):
        # Store combinations before deletion
        purchase_plan_combinations = set()
        budget_line_combinations = set()

        for record in self:
            if record.x_studio_purchase_plan and record.x_studio_purchase_plan_line:
                purchase_plan_combinations.add(
                    (record.x_studio_purchase_plan.id, record.x_studio_purchase_plan_line.id))
            if record.budget_analytic and record.budget_analytic_line:
                budget_line_combinations.add((record.budget_analytic.id, record.budget_analytic_line.id))

        result = super().unlink()

        # Update affected combinations after deletion
        for purchase_plan_id, purchase_plan_line_id in purchase_plan_combinations:
            self._update_purchase_plan_reservation_combined(purchase_plan_id, purchase_plan_line_id)

        for budget_analytic_id, budget_line_id in budget_line_combinations:
            self._update_budget_line_reservation_combined(budget_analytic_id, budget_line_id)

        return result

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.unit_price

    @api.depends('quantity', 'amount', 'contracted_quantity', 'contracted_amount')
    def _compute_remaining_values(self):
        """Compute remaining quantities and amounts"""
        for line in self:
            line.remaining_quantity = max(0, line.quantity - line.contracted_quantity)
            line.remaining_amount = max(0, line.amount - line.contracted_amount)

    def _update_contracted_values(self):
        """Update contracted quantities and amounts from purchase agreements"""
        # Flush to ensure all data is written to database
        self.env.cr.flush()

        for line in self:
            # Find all purchase requisition lines linked to this inventory line
            requisition_lines = self.env['purchase.requisition.line'].search([
                ('inventory_line_ids', 'in', line.id)
            ])

            _logger.info(f"Found {len(requisition_lines)} requisition lines linked to inventory line {line.id}")

            # Filter out cancelled/unfulfilled requisitions
            valid_requisition_lines = requisition_lines.filtered(
                lambda l: l.requisition_id and l.requisition_id.contract_status not in ['გაუქმებული', 'შეუსრულებელი']
            )

            _logger.info(f"Of those, {len(valid_requisition_lines)} are valid (not cancelled/unfulfilled)")

            # Calculate total contracted quantity and amount
            total_qty = sum(valid_requisition_lines.mapped('product_qty'))
            total_amount = sum(rl.product_qty * rl.price_unit for rl in valid_requisition_lines)

            _logger.info(f"Updating inventory line {line.id}: contracted_qty={total_qty}, contracted_amount={total_amount}")

            # Update the fields directly (not computed fields)
            line.write({
                'contracted_quantity': total_qty,
                'contracted_amount': total_amount,
            })

    def action_create_rfq_from_lines(self):
        if not self:
            raise UserError(_('Please select at least one inventory line to create RFQ.'))

        lines_without_product = self.filtered(lambda line: not line.product_id)
        if lines_without_product:
            raise UserError(_('All selected lines must have a product assigned.'))

        # Check that all required fields are filled
        missing_fields_lines = []
        for line in self:
            missing_fields = []
            if not line.x_studio_purchase_plan:
                missing_fields.append('Purchase Plan')
            if not line.x_studio_purchase_plan_line:
                missing_fields.append('Purchase Plan Line')
            if not line.budget_analytic:
                missing_fields.append('Budget Analytic')
            if not line.budget_analytic_line:
                missing_fields.append('Budget Analytic Line')

            if missing_fields:
                missing_fields_lines.append(f"{line.name}: {', '.join(missing_fields)}")

        if missing_fields_lines:
            error_message = _('The following lines have missing required fields:\n\n%s') % '\n'.join(missing_fields_lines)
            raise UserError(error_message)

        allowed_statuses = ['დასრულებულია უარყოფითი შედეგებით', 'არ შედგა', 'შეწყვეტილია']

        lines_with_other_status = self.filtered(
            lambda line: line.x_studio_tender_status and line.x_studio_tender_status not in allowed_statuses
        )

        if lines_with_other_status:
            other_status_names = ', '.join(set(lines_with_other_status.mapped('x_studio_tender_status')))
            raise UserError(
                _('Cannot create RFQ. Only lines with tender status "%s", "%s", or "%s" are allowed. Found other statuses: %s') %
                (allowed_statuses[0], allowed_statuses[1], allowed_statuses[2], other_status_names)
            )

        # Check purchase reasons (keeping existing validation logic)
        purchase_reasons = set()
        purchase_methods = set()
        lines_with_purchase_reason = []
        lines_without_purchase_reason = []

        for line in self:
            if line.x_studio_purchase_plan_line and line.x_studio_purchase_plan_line.purchase_reason_id:
                purchase_reasons.add(line.x_studio_purchase_plan_line.purchase_reason_id.id)
                lines_with_purchase_reason.append(line)
                if line.x_studio_purchase_plan_line.purchase_method_id:
                    purchase_methods.add(line.x_studio_purchase_plan_line.purchase_method_id.id)
            else:
                lines_without_purchase_reason.append(line)

        # Check for mixed state (some filled, some empty)
        if lines_with_purchase_reason and lines_without_purchase_reason:
            raise UserError(
                _('Cannot create RFQ. Purchase reasons must be either all empty or all filled with the same value. '
                  'Found %d lines with purchase reason and %d lines without.') %
                (len(lines_with_purchase_reason), len(lines_without_purchase_reason))
            )

        # If all lines have purchase reasons, they must be the same
        if len(purchase_reasons) > 1:
            reason_names = []
            for reason_id in purchase_reasons:
                reason = self.env['purchase.reason'].browse(reason_id)
                reason_names.append(reason.name or f"Reason {reason_id}")
            raise UserError(
                _('Cannot create RFQ. All selected lines must have the same purchase reason. '
                  'Found different reasons: %s') % ', '.join(reason_names)
            )

        # Instead of automatically selecting vendor, open the wizard
        return self._open_vendor_selection_wizard()

    def _open_vendor_selection_wizard(self):
        """Open vendor selection wizard"""
        wizard = self.env['vendor.selection.wizard'].create({
            'inventory_line_ids': [(6, 0, self.ids)]
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Vendor for RFQ'),
            'res_model': 'vendor.selection.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',  # Opens as a popup
            'context': {'default_inventory_line_ids': [(6, 0, self.ids)]}
        }

    def _create_single_rfq(self, lines, vendor, purchase_method=None):
        try:
            rfq_vals = {
                'state': 'draft',
                'partner_id': vendor.id,
                'order_line': [],
                'inventory_line_ids': [(6, 0, lines.ids)],
            }

            if vendor.property_purchase_currency_id:
                rfq_vals['currency_id'] = vendor.property_purchase_currency_id.id

            if purchase_method:
                rfq_vals['x_studio_purchase_method'] = purchase_method.id

            request_names = lines.mapped('request_id.name')
            if request_names:
                rfq_vals['origin'] = ', '.join(filter(None, request_names))

            for line in lines:
                po_line_vals = {
                    'product_id': line.product_id.id,
                    'name': line.name or line.product_id.name,
                    'product_qty': line.quantity,
                    'product_uom': line.uom_id.id if line.uom_id else line.product_id.uom_po_id.id,
                    'price_unit': line.unit_price or line.product_id.standard_price,
                    'date_planned': line.expected_date or fields.Date.today(),
                }

                # Transfer relation fields
                if line.x_studio_purchase_plan:
                    po_line_vals['purchase_plan_id'] = line.x_studio_purchase_plan.id
                if line.x_studio_purchase_plan_line:
                    po_line_vals['purchase_plan_line_id'] = line.x_studio_purchase_plan_line.id
                if line.budget_analytic:
                    po_line_vals['budget_analytic_id'] = line.budget_analytic.id
                if line.budget_analytic_line:
                    po_line_vals['budget_line_id'] = line.budget_analytic_line.id

                # Transfer x_studio_ field (request number)
                if line.x_studio_requset_number:
                    po_line_vals['x_studio_'] = line.x_studio_requset_number

                rfq_vals['order_line'].append((0, 0, po_line_vals))

            rfq = self.env['purchase.order'].create(rfq_vals)
            lines.write({'x_studio_rfq': rfq.id})

            _logger.info(f"Created RFQ {rfq.name} from {len(lines)} inventory lines with vendor {vendor.name}")
            return rfq

        except Exception as e:
            _logger.error(f"Error creating RFQ: {str(e)}")
            raise UserError(_('Error creating RFQ: %s') % str(e))

    def _return_rfq_action(self, rfq):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request for Quotation'),
            'res_model': 'purchase.order',
            'res_id': rfq.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _find_active_budget_for_category_analytic(self, category_analytic_account):
        """Find active budget and matching budget line"""
        try:
            current_date = date.today()
            active_budgets = self.env['budget.analytic'].search([
                ('date_from', '<=', current_date),
            ], order='date_from desc')

            possible_field_names = ['account_id', 'analytic_account_id', 'analytic_id']

            for budget in active_budgets:
                for field_name in possible_field_names:
                    try:
                        budget_lines = self.env['budget.line'].search([
                            ('budget_analytic_id', '=', budget.id),
                            (field_name, '=', category_analytic_account.id)
                        ])

                        if budget_lines:
                            return budget, budget_lines[0]
                    except Exception:
                        continue

            return None, None

        except Exception as e:
            _logger.error(f"Error finding active budget: {str(e)}")
            return None, None

    def _auto_populate_budget_fields(self):
        """Auto-populate budget fields based on product category"""
        if not self.product_id:
            return

        try:
            product_category = self.product_id.categ_id
            if not product_category:
                return

            category_analytic_account = product_category.x_studio_many2one_field_2o6_1j1dfj1v3
            if not category_analytic_account:
                return

            budget_analytic, budget_line = self._find_active_budget_for_category_analytic(category_analytic_account)

            if budget_analytic and budget_line:
                self.budget_main = budget_analytic.id
                self.budget_name_main = category_analytic_account.id

        except Exception as e:
            _logger.error(f"Error in auto-populating budget fields: {str(e)}")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.unit_price = self.product_id.standard_price
            self._auto_populate_budget_fields()

            if not self.stage_id:
                default_stage = self.env['inventory.line.stage'].search([('active', '=', True)], limit=1,
                                                                        order='sequence')
                if default_stage:
                    self.stage_id = default_stage.id

    def action_create_purchase_agreement_direct(self):
        """
        Create a purchase agreement directly from inventory lines.
        Opens a dedicated wizard to select vendor.
        """
        if not self:
            raise UserError(_('Please select at least one inventory line.'))

        # Check that all required fields are filled
        missing_fields_lines = []
        for line in self:
            missing_fields = []
            if not line.product_id:
                missing_fields.append('Product')
            if line.quantity <= 0:
                missing_fields.append('Valid Quantity')
            if not line.x_studio_purchase_plan:
                missing_fields.append('Purchase Plan')
            if not line.x_studio_purchase_plan_line:
                missing_fields.append('Purchase Plan Line')
            if not line.budget_analytic:
                missing_fields.append('Budget Analytic')
            if not line.budget_analytic_line:
                missing_fields.append('Budget Analytic Line')

            if missing_fields:
                missing_fields_lines.append(f"{line.name}: {', '.join(missing_fields)}")

        if missing_fields_lines:
            error_message = _('The following lines have missing required fields:\n\n%s') % '\n'.join(missing_fields_lines)
            raise UserError(error_message)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Vendor for Purchase Agreement'),
            'res_model': 'agreement.vendor.selection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_inventory_line_ids': [(6, 0, self.ids)],
            },
        }

    def _create_purchase_agreement_direct(self, lines, vendor, purchase_method=None):
        """
        Create purchase agreement directly from inventory lines.
        This mirrors the logic from _create_single_agreement_with_all_lines but works directly with inventory lines.
        """
        _logger.info(f"CHECK FLAG FOR ME")
        if not vendor:
            raise UserError(_('Please select a vendor.'))

        if not lines:
            raise UserError(_('No inventory lines provided.'))

        try:
            # Prepare base agreement values
            agreement_vals = {
                'user_id': self.env.user.id,
                'currency_id': vendor.property_purchase_currency_id.id if vendor.property_purchase_currency_id else self.env.company.currency_id.id,
                'description': f"Purchase Agreement from Inventory Lines",
                'line_ids': [],
            }

            # AUTO-FILL: registration_year from current date or first line's request date
            first_line = lines[0] if lines else None

            # DEBUG: Log budget fields to find the issue
            if first_line:
                _logger.info(f"=== BUDGET DEBUG FOR PURCHASE AGREEMENT ===")
                _logger.info(f"First inventory line ID: {first_line.id}, Name: {first_line.name}")
                _logger.info(f"budget_analytic: {first_line.budget_analytic.name if first_line.budget_analytic else 'EMPTY'} (ID: {first_line.budget_analytic.id if first_line.budget_analytic else 'None'})")
                _logger.info(f"budget_main: {first_line.budget_main.name if first_line.budget_main else 'EMPTY'} (ID: {first_line.budget_main.id if first_line.budget_main else 'None'})")
                _logger.info(f"budget_analytic_line: {first_line.budget_analytic_line.name if first_line.budget_analytic_line else 'EMPTY'} (ID: {first_line.budget_analytic_line.id if first_line.budget_analytic_line else 'None'})")
                _logger.info(f"=========================================")

            if first_line and first_line.request_date:
                if hasattr(self.env['purchase.requisition'], 'registration_year'):
                    agreement_vals['registration_year'] = str(first_line.request_date.year)
                    _logger.info(f"Setting registration_year to: {first_line.request_date.year}")
            else:
                if hasattr(self.env['purchase.requisition'], 'registration_year'):
                    agreement_vals['registration_year'] = str(date.today().year)
                    _logger.info(f"Setting registration_year to current year: {date.today().year}")

            # AUTO-FILL: Collect unique values from inventory lines for multiple fields
            purchase_methods = []  # for purchase_method field
            purchase_basis_values = []  # for purchase_basis field (request numbers)
            cpv_codes = []  # for cpv_code field
            budget_articles = []  # for budget_article field

            for line in lines:
                # Collect purchase_method from purchase_plan_line -> purchase_method_id
                if line.x_studio_purchase_plan_line and hasattr(line.x_studio_purchase_plan_line, 'purchase_method_id'):
                    if line.x_studio_purchase_plan_line.purchase_method_id:
                        method_name = line.x_studio_purchase_plan_line.purchase_method_id.name or ''
                        if method_name and method_name not in purchase_methods:
                            purchase_methods.append(method_name)

                # Collect x_studio_ (request number) for purchase_basis
                if line.x_studio_:
                    if line.x_studio_ not in purchase_basis_values:
                        purchase_basis_values.append(line.x_studio_)

                # Collect cpv_code from purchase_plan_line name
                if line.x_studio_purchase_plan_line:
                    cpv_name = line.x_studio_purchase_plan_line.name or ''
                    if cpv_name:
                        # Split by '-' and take the first element, strip whitespace
                        cpv_code = cpv_name.split('-')[0].strip()
                        if cpv_code and cpv_code not in cpv_codes:
                            cpv_codes.append(cpv_code)

                # Collect budget_article codes only from budget_analytic_line
                if line.budget_analytic_line:
                    try:
                        budget_line = line.budget_analytic_line
                        # Try common field names for analytic account in budget.line
                        for field_name in ['account_id', 'analytic_account_id', 'analytic_id']:
                            if hasattr(budget_line, field_name):
                                analytic_acc = getattr(budget_line, field_name)
                                if analytic_acc and hasattr(analytic_acc, 'code'):
                                    code = getattr(analytic_acc, 'code', '') or ''

                                    if code and code not in budget_articles:
                                        budget_articles.append(code)
                                        _logger.info(f"Added budget article code: {code}")
                                    break  # Found the field, stop trying other names
                    except Exception as e:
                        _logger.debug(f"Could not extract budget article from line: {str(e)}")

            # Set purchase_method (comma-separated)
            if purchase_methods and hasattr(self.env['purchase.requisition'], 'purchase_method'):
                agreement_vals['purchase_method'] = ', '.join(purchase_methods)
                _logger.info(f"Setting purchase_method to: {agreement_vals['purchase_method']}")

            # Set purchase_basis (comma-separated request numbers)
            if purchase_basis_values and hasattr(self.env['purchase.requisition'], 'purchase_basis'):
                agreement_vals['purchase_basis'] = ', '.join(purchase_basis_values)
                _logger.info(f"Setting purchase_basis to: {agreement_vals['purchase_basis']}")

            # Set cpv_code (comma-separated)
            if cpv_codes and hasattr(self.env['purchase.requisition'], 'cpv_code'):
                agreement_vals['cpv_code'] = ', '.join(cpv_codes)
                _logger.info(f"Setting cpv_code to: {agreement_vals['cpv_code']}")

            # Set budget_article (comma-separated)
            if budget_articles and hasattr(self.env['purchase.requisition'], 'budget_article'):
                agreement_vals['budget_article'] = ', '.join(budget_articles)
                _logger.info(f"Setting budget_article to: {agreement_vals['budget_article']}")

            # Add origin from request names
            request_names = lines.mapped('request_id.name')
            if request_names and hasattr(self.env['purchase.requisition'], 'origin'):
                agreement_vals['origin'] = ', '.join(filter(None, request_names))
                _logger.info(f"Setting origin to: {agreement_vals['origin']}")

            # Add vendor
            if vendor:
                if hasattr(self.env['purchase.requisition'], 'vendor_id'):
                    agreement_vals['vendor_id'] = vendor.id
                    # Auto-fill supplier_id_code from vendor's VAT
                    if hasattr(self.env['purchase.requisition'], 'supplier_id_code') and vendor.vat:
                        agreement_vals['supplier_id_code'] = vendor.vat
                        _logger.info(f"Setting supplier_id_code to {vendor.vat} from vendor {vendor.name}")
                elif hasattr(self.env['purchase.requisition'], 'partner_id'):
                    agreement_vals['partner_id'] = vendor.id
                    # Auto-fill supplier_id_code from partner's VAT
                    if hasattr(self.env['purchase.requisition'], 'supplier_id_code') and vendor.vat:
                        agreement_vals['supplier_id_code'] = vendor.vat
                        _logger.info(f"Setting supplier_id_code to {vendor.vat} from partner {vendor.name}")

            # Transfer budget/plan fields from first line to header
            if first_line:
                if first_line.x_studio_purchase_plan:
                    if hasattr(self.env['purchase.requisition'], 'purchase_plan_id'):
                        agreement_vals['purchase_plan_id'] = first_line.x_studio_purchase_plan.id

                if first_line.x_studio_purchase_plan_line:
                    if hasattr(self.env['purchase.requisition'], 'purchase_plan_line_id'):
                        agreement_vals['purchase_plan_line_id'] = first_line.x_studio_purchase_plan_line.id

                # Try budget_analytic first, then budget_main as fallback
                budget_to_use = first_line.budget_analytic or first_line.budget_main
                _logger.info(f"Budget to use: {budget_to_use.name if budget_to_use else 'NONE FOUND'}")
                _logger.info(f"Does purchase.requisition have budget_analytic_id? {hasattr(self.env['purchase.requisition'], 'budget_analytic_id')}")

                if budget_to_use:
                    if hasattr(self.env['purchase.requisition'], 'budget_analytic_id'):
                        agreement_vals['budget_analytic_id'] = budget_to_use.id
                        _logger.info(f"✓✓✓ SET budget_analytic_id to {budget_to_use.id} ({budget_to_use.name})")
                    else:
                        _logger.error(f"XXX purchase.requisition does NOT have budget_analytic_id field!")
                else:
                    _logger.warning(f"XXX No budget found on inventory line!")

                if first_line.budget_analytic_line:
                    if hasattr(self.env['purchase.requisition'], 'budget_line_id'):
                        agreement_vals['budget_line_id'] = first_line.budget_analytic_line.id
                        _logger.info(f"✓✓✓ SET budget_line_id to {first_line.budget_analytic_line.id}")

            # Create agreement lines from inventory lines
            for line in lines:
                if not line.product_id:
                    continue

                # Force recalculation of contracted values before checking
                line._update_contracted_values()

                # Check if there's remaining quantity to contract
                remaining = line.quantity - line.contracted_quantity

                # If no remaining quantity, skip this line
                if remaining <= 0:
                    _logger.warning(f"Skipping inventory line {line.id} ({line.name}) - fully contracted (quantity: {line.quantity}, contracted: {line.contracted_quantity})")
                    continue

                # Get analytic distribution
                analytic_distribution = {}
                if line.budget_name_main:
                    analytic_distribution = {str(line.budget_name_main.id): 100}

                # Use REMAINING quantity for this new agreement
                qty_to_contract = remaining
                price = line.unit_price or line.product_id.standard_price

                _logger.info(f"Creating agreement line for {line.name}: qty={qty_to_contract} (inventory total={line.quantity}, already contracted={line.contracted_quantity}, remaining={remaining})")

                agreement_line_vals = {
                    'product_id': line.product_id.id,
                    'product_qty': qty_to_contract,
                    'product_uom_id': line.uom_id.id if line.uom_id else line.product_id.uom_id.id,
                    'price_unit': price,
                    'inventory_line_ids': [(6, 0, [line.id])],  # Link to inventory line
                }

                # Calculate total_amount for the agreement line based on remaining quantity
                if hasattr(self.env['purchase.requisition.line'], 'total_amount'):
                    agreement_line_vals['total_amount'] = qty_to_contract * price

                # Set product description
                if hasattr(self.env['purchase.requisition.line'], 'product_description_variants'):
                    agreement_line_vals['product_description_variants'] = line.name or line.product_id.name
                elif hasattr(self.env['purchase.requisition.line'], 'name'):
                    agreement_line_vals['name'] = line.name or line.product_id.name

                # Transfer analytic distribution
                if analytic_distribution and hasattr(self.env['purchase.requisition.line'], 'analytic_distribution'):
                    agreement_line_vals['analytic_distribution'] = analytic_distribution

                # Transfer purchase plan and budget fields to agreement line
                if line.x_studio_purchase_plan:
                    if hasattr(self.env['purchase.requisition.line'], 'purchase_plan_id'):
                        agreement_line_vals['purchase_plan_id'] = line.x_studio_purchase_plan.id

                if line.x_studio_purchase_plan_line:
                    if hasattr(self.env['purchase.requisition.line'], 'purchase_plan_line_id'):
                        agreement_line_vals['purchase_plan_line_id'] = line.x_studio_purchase_plan_line.id

                # Use budget_analytic or budget_main
                line_budget = line.budget_analytic or line.budget_main
                if line_budget:
                    if hasattr(self.env['purchase.requisition.line'], 'budget_analytic_id'):
                        agreement_line_vals['budget_analytic_id'] = line_budget.id

                if line.budget_analytic_line:
                    if hasattr(self.env['purchase.requisition.line'], 'budget_line_id'):
                        agreement_line_vals['budget_line_id'] = line.budget_analytic_line.id

                # Transfer x_studio_ (request number) to agreement line
                if line.x_studio_:
                    if hasattr(self.env['purchase.requisition.line'], 'x_studio_'):
                        agreement_line_vals['x_studio_'] = line.x_studio_
                        _logger.info(f"Setting x_studio_ on agreement line to: {line.x_studio_}")

                agreement_vals['line_ids'].append((0, 0, agreement_line_vals))

            if not agreement_vals['line_ids']:
                raise UserError(_('No valid lines found to create agreement.'))

            # DEBUG: Show what values we're about to create
            _logger.info(f"=== CREATING PURCHASE AGREEMENT ===")
            _logger.info(f"budget_analytic_id in agreement_vals: {agreement_vals.get('budget_analytic_id', 'NOT SET')}")
            _logger.info(f"budget_line_id in agreement_vals: {agreement_vals.get('budget_line_id', 'NOT SET')}")
            _logger.info(f"All keys in agreement_vals: {list(agreement_vals.keys())}")
            _logger.info(f"===================================")

            # Create the purchase agreement
            agreement = self.env['purchase.requisition'].create(agreement_vals)

            _logger.info(f"=== CREATED AGREEMENT {agreement.name} ===")
            _logger.info(f"Agreement budget_analytic_id: {agreement.budget_analytic_id.name if hasattr(agreement, 'budget_analytic_id') and agreement.budget_analytic_id else 'NOT SET'}")
            _logger.info(f"=======================================")


            # AUTO-FILL: Calculate requested_amount from inventory lines
            if hasattr(agreement, 'requested_amount'):
                total_requested_amount = sum(lines.mapped('amount'))
                agreement.write({'requested_amount': total_requested_amount})
                _logger.info(f"Set requested_amount to {total_requested_amount} based on {len(lines)} inventory lines")

            # The contract_amount will be automatically calculated from the lines
            # but we can explicitly trigger it to ensure it's set immediately
            if hasattr(agreement, 'contract_amount'):
                agreement._compute_contract_amount()

            # CRITICAL: Flush all changes to database before updating contracted values
            self.env.cr.flush()
            self.env.cr.commit()

            # Update contracted values on inventory lines immediately
            _logger.info(f"Updating contracted values for {len(lines)} inventory lines after creating agreement {agreement.name}")
            for line in lines:
                line._update_contracted_values()
                _logger.info(f"Line {line.name}: quantity={line.quantity}, contracted={line.contracted_quantity}, remaining={line.quantity - line.contracted_quantity}")

            # Flush again to ensure updates are saved
            self.env.cr.flush()

            _logger.info(f"Created purchase agreement {agreement.name} directly from {len(lines)} inventory lines")
            _logger.info(
                f"Vendor: {vendor.name}, Contract Amount: {agreement.contract_amount if hasattr(agreement, 'contract_amount') else 'N/A'}, Requested Amount: {agreement.requested_amount if hasattr(agreement, 'requested_amount') else 'N/A'}")

            return agreement

        except Exception as e:
            _logger.error(f"Error creating purchase agreement: {str(e)}")
            raise UserError(_('Error creating purchase agreement: %s') % str(e))


    def _return_agreement_action(self, agreement):
        """Return action to view the created purchase agreement"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Agreement'),
            'res_model': 'purchase.requisition',
            'res_id': agreement.id,
            'view_mode': 'form',
            'target': 'current',
        }




class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    inventory_line_ids = fields.Many2many(
        'inventory.line',
        'purchase_order_inventory_line_rel',
        'purchase_order_id',
        'inventory_line_id',
        string='Inventory Lines',
        help='Inventory lines used to create this RFQ'
    )

    @api.onchange('x_studio_tender_status')
    def _onchange_tender_status(self):
        """Update tender status on inventory lines when RFQ tender status changes"""
        if self.x_studio_tender_status and self.inventory_line_ids:
            for line in self.inventory_line_ids:
                line.x_studio_tender_status = self.x_studio_tender_status
            _logger.info(
                f"Updated tender status to '{self.x_studio_tender_status}' for {len(self.inventory_line_ids)} inventory lines")

    def write(self, vals):
        """Update inventory lines tender status when RFQ tender status is changed"""
        result = super().write(vals)

        if 'x_studio_tender_status' in vals:
            for order in self:
                if order.inventory_line_ids and order.x_studio_tender_status:
                    order.inventory_line_ids.write({'x_studio_tender_status': order.x_studio_tender_status})
                    _logger.info(
                        f"Updated tender status to '{order.x_studio_tender_status}' for {len(order.inventory_line_ids)} inventory lines via write")

        return result

    def action_create_purchase_agreements(self):
        """Create Purchase Agreement from RFQ with auto-filled fields"""
        if not self.order_line:
            raise UserError(_('This RFQ has no lines to create agreement from.'))

        if self.state not in ['draft', 'sent']:
            raise UserError(_('Purchase agreement can only be created from draft or sent RFQs.'))

        if 'purchase.requisition' not in self.env:
            raise UserError(_('Purchase Agreements module is not installed.'))

        existing_agreement = self.env['purchase.requisition'].search([
            ('description', 'ilike', f'RFQ: {self.name}')
        ], limit=1)

        if existing_agreement:
            raise UserError(_('Purchase agreement already exists for this RFQ: %s') % existing_agreement.name)

        # Create the agreement ONCE
        agreement = self._create_single_agreement_with_all_lines()

        # Update the RFQ status
        self.write({'x_studio_tender_status': 'Contract Status'})

        # Update inventory lines tender status
        self._update_inventory_lines_tender_status_after_agreement()

        return self._return_agreement_action(agreement)

    def _update_inventory_lines_tender_status_after_agreement(self):
        """Update tender status in inventory lines after agreement creation"""
        try:
            if not self.x_studio_tender_status:
                return

            inventory_lines = self.env['inventory.line'].search([
                ('x_studio_rfq', '=', self.id)
            ])

            if inventory_lines:
                inventory_lines.write({'x_studio_tender_status': self.x_studio_tender_status})
                _logger.info(f"Updated tender status for {len(inventory_lines)} inventory lines")

        except Exception as e:
            _logger.error(f"Error updating inventory lines tender status: {str(e)}")

    def _create_single_agreement_with_all_lines(self):
        """Create purchase agreement with all fields auto-filled from RFQ"""
        try:
            agreement_vals = {
                'user_id': self.env.user.id,
                'currency_id': self.currency_id.id or self.env.company.currency_id.id,
                'description': f"Purchase Agreement for RFQ: {self.name}",
                'line_ids': [],
            }

            # AUTO-FILL: registration_year from date_approve
            if self.date_approve and hasattr(self.env['purchase.requisition'], 'registration_year'):
                agreement_vals['registration_year'] = str(self.date_approve.year)
                _logger.info(f"Setting registration_year to: {self.date_approve.year}")

            # AUTO-FILL: Collect unique values from order lines for multiple fields
            purchase_methods = []  # for purchase_method field
            purchase_basis_values = []  # for purchase_basis field
            cpv_codes = []  # for cpv_code field
            budget_articles = []  # for budget_article field

            for po_line in self.order_line:
                # Collect purchase_method from purchase_plan_line_id -> purchase_method_id
                if hasattr(po_line, 'purchase_plan_line_id') and po_line.purchase_plan_line_id:
                    plan_line = po_line.purchase_plan_line_id
                    if hasattr(plan_line, 'purchase_method_id') and plan_line.purchase_method_id:
                        method_name = plan_line.purchase_method_id.name or ''
                        if method_name and method_name not in purchase_methods:
                            purchase_methods.append(method_name)

                # Collect x_studio_ (request number) for purchase_basis
                if hasattr(po_line, 'x_studio_') and po_line.x_studio_:
                    if po_line.x_studio_ not in purchase_basis_values:
                        purchase_basis_values.append(po_line.x_studio_)

                # Collect cpv_code from purchase_plan_line_id name
                if hasattr(po_line, 'purchase_plan_line_id') and po_line.purchase_plan_line_id:
                    cpv_name = po_line.purchase_plan_line_id.name or ''
                    if cpv_name:
                        # Split by '-' and take the first element, strip whitespace
                        cpv_code = cpv_name.split('-')[0].strip()
                        if cpv_code and cpv_code not in cpv_codes:
                            cpv_codes.append(cpv_code)

                # FIXED: Collect budget_article codes only from budget_line_id
                if hasattr(po_line, 'budget_line_id') and po_line.budget_line_id:
                    try:
                        budget_line = po_line.budget_line_id
                        # Try common field names for analytic account in budget.line
                        for field_name in ['account_id', 'analytic_account_id', 'analytic_id']:
                            if hasattr(budget_line, field_name):
                                analytic_acc = getattr(budget_line, field_name)
                                if analytic_acc and hasattr(analytic_acc, 'code'):
                                    code = getattr(analytic_acc, 'code', '') or ''

                                    if code and code not in budget_articles:
                                        budget_articles.append(code)
                                        _logger.info(f"Added budget article code: {code}")
                                    break  # Found the field, stop trying other names
                    except Exception as e:
                        _logger.debug(f"Could not extract budget article from line: {str(e)}")

            # Set purchase_method (comma-separated)
            if purchase_methods and hasattr(self.env['purchase.requisition'], 'purchase_method'):
                agreement_vals['purchase_method'] = ', '.join(purchase_methods)
                _logger.info(f"Setting purchase_method to: {agreement_vals['purchase_method']}")

            # Set purchase_basis (comma-separated request numbers)
            if purchase_basis_values and hasattr(self.env['purchase.requisition'], 'purchase_basis'):
                agreement_vals['purchase_basis'] = ', '.join(purchase_basis_values)
                _logger.info(f"Setting purchase_basis to: {agreement_vals['purchase_basis']}")

            # Set cpv_code (comma-separated)
            if cpv_codes and hasattr(self.env['purchase.requisition'], 'cpv_code'):
                agreement_vals['cpv_code'] = ', '.join(cpv_codes)
                _logger.info(f"Setting cpv_code to: {agreement_vals['cpv_code']}")

            # Set budget_article (comma-separated)
            if budget_articles and hasattr(self.env['purchase.requisition'], 'budget_article'):
                agreement_vals['budget_article'] = ', '.join(budget_articles)
                _logger.info(f"Setting budget_article to: {agreement_vals['budget_article']}")

            # Add origin if exists
            if hasattr(self.env['purchase.requisition'], 'origin'):
                agreement_vals['origin'] = self.name

            # Add vendor if exists
            if self.partner_id:
                if hasattr(self.env['purchase.requisition'], 'vendor_id'):
                    agreement_vals['vendor_id'] = self.partner_id.id
                elif hasattr(self.env['purchase.requisition'], 'partner_id'):
                    agreement_vals['partner_id'] = self.partner_id.id

            # Transfer budget/plan fields from first line to header
            first_line = self.order_line[0] if self.order_line else None
            if first_line:
                if hasattr(first_line, 'purchase_plan_id') and first_line.purchase_plan_id:
                    if hasattr(self.env['purchase.requisition'], 'purchase_plan_id'):
                        agreement_vals['purchase_plan_id'] = first_line.purchase_plan_id.id

                if hasattr(first_line, 'purchase_plan_line_id') and first_line.purchase_plan_line_id:
                    if hasattr(self.env['purchase.requisition'], 'purchase_plan_line_id'):
                        agreement_vals['purchase_plan_line_id'] = first_line.purchase_plan_line_id.id

                if hasattr(first_line, 'budget_analytic_id') and first_line.budget_analytic_id:
                    if hasattr(self.env['purchase.requisition'], 'budget_analytic_id'):
                        agreement_vals['budget_analytic_id'] = first_line.budget_analytic_id.id

                if hasattr(first_line, 'budget_line_id') and first_line.budget_line_id:
                    if hasattr(self.env['purchase.requisition'], 'budget_line_id'):
                        agreement_vals['budget_line_id'] = first_line.budget_line_id.id

            # Create agreement lines
            for po_line in self.order_line:
                if not po_line.product_id:
                    continue

                agreement_line_vals = {
                    'product_id': po_line.product_id.id,
                    'product_qty': po_line.product_qty,
                    'product_uom_id': po_line.product_uom.id,
                    'price_unit': po_line.price_unit,
                }

                # Calculate total_amount for the agreement line
                if hasattr(self.env['purchase.requisition.line'], 'total_amount'):
                    agreement_line_vals['total_amount'] = po_line.product_qty * po_line.price_unit

                # Transfer fields to agreement line
                if hasattr(po_line, 'purchase_plan_id') and po_line.purchase_plan_id:
                    if hasattr(self.env['purchase.requisition.line'], 'purchase_plan_id'):
                        agreement_line_vals['purchase_plan_id'] = po_line.purchase_plan_id.id

                if hasattr(po_line, 'purchase_plan_line_id') and po_line.purchase_plan_line_id:
                    if hasattr(self.env['purchase.requisition.line'], 'purchase_plan_line_id'):
                        agreement_line_vals['purchase_plan_line_id'] = po_line.purchase_plan_line_id.id

                if hasattr(po_line, 'budget_analytic_id') and po_line.budget_analytic_id:
                    if hasattr(self.env['purchase.requisition.line'], 'budget_analytic_id'):
                        agreement_line_vals['budget_analytic_id'] = po_line.budget_analytic_id.id

                if hasattr(po_line, 'budget_line_id') and po_line.budget_line_id:
                    if hasattr(self.env['purchase.requisition.line'], 'budget_line_id'):
                        agreement_line_vals['budget_line_id'] = po_line.budget_line_id.id

                if hasattr(self.env['purchase.requisition.line'], 'product_description_variants'):
                    agreement_line_vals['product_description_variants'] = po_line.name
                elif hasattr(self.env['purchase.requisition.line'], 'name'):
                    agreement_line_vals['name'] = po_line.name

                if hasattr(po_line, 'analytic_distribution') and po_line.analytic_distribution:
                    if hasattr(self.env['purchase.requisition.line'], 'analytic_distribution'):
                        agreement_line_vals['analytic_distribution'] = po_line.analytic_distribution

                # Transfer x_studio_ (request number) to agreement line
                if hasattr(po_line, 'x_studio_') and po_line.x_studio_:
                    if hasattr(self.env['purchase.requisition.line'], 'x_studio_'):
                        agreement_line_vals['x_studio_'] = po_line.x_studio_
                        _logger.info(f"Setting x_studio_ on agreement line to: {po_line.x_studio_}")

                agreement_vals['line_ids'].append((0, 0, agreement_line_vals))

            if not agreement_vals['line_ids']:
                raise UserError(_('No valid lines found to create agreement.'))

            # Add vendor if exists
            if self.partner_id:
                if hasattr(self.env['purchase.requisition'], 'vendor_id'):
                    agreement_vals['vendor_id'] = self.partner_id.id
                    # Auto-fill supplier_id_code from vendor's VAT
                    if hasattr(self.env['purchase.requisition'], 'supplier_id_code') and self.partner_id.vat:
                        agreement_vals['supplier_id_code'] = self.partner_id.vat
                        _logger.info(
                            f"Setting supplier_id_code to {self.partner_id.vat} from vendor {self.partner_id.name}")
                elif hasattr(self.env['purchase.requisition'], 'partner_id'):
                    agreement_vals['partner_id'] = self.partner_id.id
                    # Auto-fill supplier_id_code from partner's VAT
                    if hasattr(self.env['purchase.requisition'], 'supplier_id_code') and self.partner_id.vat:
                        agreement_vals['supplier_id_code'] = self.partner_id.vat
                        _logger.info(
                            f"Setting supplier_id_code to {self.partner_id.vat} from partner {self.partner_id.name}")

            # Create the agreement
            agreement = self.env['purchase.requisition'].create(agreement_vals)

            self.write({'requisition_id': agreement.id})

            # AUTO-FILL: Calculate requested_amount from inventory lines
            if hasattr(agreement, 'requested_amount') and self.inventory_line_ids:
                total_requested_amount = sum(self.inventory_line_ids.mapped('amount'))
                agreement.write({'requested_amount': total_requested_amount})
                _logger.info(
                    f"Set requested_amount to {total_requested_amount} based on {len(self.inventory_line_ids)} inventory lines")

            # The contract_amount will be automatically calculated from the lines
            # but we can explicitly trigger it to ensure it's set immediately
            if hasattr(agreement, 'contract_amount'):
                agreement._compute_contract_amount()

            _logger.info(f"Created purchase agreement {agreement.name} from RFQ {self.name}")
            _logger.info(
                f"Contract Amount: {agreement.contract_amount}, Requested Amount: {agreement.requested_amount}")

            return agreement

        except Exception as e:
            _logger.error(f"Error creating purchase agreement: {str(e)}")
            raise UserError(_('Error creating purchase agreement: %s') % str(e))

    def _return_agreement_action(self, agreement):
        """Return action to view the created purchase agreement"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Agreement'),
            'res_model': 'purchase.requisition',
            'res_id': agreement.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'create': False},
        }


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    purchase_plan_id = fields.Many2one('purchase.plan', string='Purchase Plan')
    purchase_plan_line_id = fields.Many2one('purchase.plan.line', string='Purchase Plan Line')
    budget_analytic_id = fields.Many2one('budget.analytic', string='Budget Analytic')
    budget_line_id = fields.Many2one('budget.line', string='Budget Line')
    budget_analytic_line = fields.Many2one('budget.line', string='Budget Analytic Line')

    # Field to store request number from inventory line
    x_studio_ = fields.Char(string='Request Number')


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def action_confirm(self):
        """Override action_confirm to create a new quotation after confirmation"""
        # Call the original action_confirm method
        res = super(PurchaseRequisition, self).action_confirm()

        # Update related inventory requests to "დადასტურებული" (id=18)
        confirmed_stage = self.env['inventory.request.stage'].browse(18)
        if confirmed_stage.exists():
            requests = self.mapped('line_ids.inventory_line_ids.request_id')
            if requests:
                requests.write({'stage_id': confirmed_stage.id})
                _logger.info(
                    "Updated request stage to 'დადასტურებული' (id=18) for %s inventory requests on agreement confirmation",
                    len(requests),
                )

        # Call action_create_new_quotation after confirmation
        self.action_create_new_quotation()

        return res

    def action_create_new_quotation(self):
        """Create a new RFQ/Purchase Order from the agreement with same fields"""
        if not self.line_ids:
            raise UserError(_('This agreement has no lines to create quotation from.'))

        # Check if vendor is set on the agreement
        if not self.vendor_id:
            raise UserError(_('Cannot create quotation: No vendor set on this agreement.'))

        # Try to get the original RFQ that created this agreement
        original_rfq = self.env['purchase.order'].search([
            ('requisition_id', '=', self.id)
        ], limit=1)

        # Prepare new RFQ values
        new_rfq_vals = {
            'state': 'draft',
            'partner_id': self.vendor_id.id,  # Get vendor from agreement itself
            'requisition_id': self.id,  # Link back to this agreement
            'order_line': [],
        }

        # If original RFQ exists, copy optional fields from it
        if original_rfq:
            if original_rfq.currency_id:
                new_rfq_vals['currency_id'] = original_rfq.currency_id.id

            # Copy purchase method if exists
            if hasattr(original_rfq, 'x_studio_purchase_method') and original_rfq.x_studio_purchase_method:
                new_rfq_vals['x_studio_purchase_method'] = original_rfq.x_studio_purchase_method.id

            # Copy origin
            if original_rfq.origin:
                new_rfq_vals['origin'] = f"Agreement: {self.name} (From: {original_rfq.origin})"
            else:
                new_rfq_vals['origin'] = f"Agreement: {self.name}"

            # Copy inventory_line_ids if they exist
            if hasattr(original_rfq, 'inventory_line_ids') and original_rfq.inventory_line_ids:
                new_rfq_vals['inventory_line_ids'] = [(6, 0, original_rfq.inventory_line_ids.ids)]
        else:
            # No original RFQ found, just set origin
            new_rfq_vals['origin'] = f"Agreement: {self.name}"

        # Create order lines from agreement lines
        for agreement_line in self.line_ids:
            po_line_vals = {
                'product_id': agreement_line.product_id.id,
                'name': agreement_line.product_description_variants if hasattr(agreement_line,
                                                                               'product_description_variants') else agreement_line.product_id.name,
                'product_qty': agreement_line.product_qty,
                'product_uom': agreement_line.product_uom_id.id,
                'price_unit': agreement_line.price_unit,
                'date_planned': fields.Date.today(),
            }

            # Transfer plan and budget fields
            if hasattr(agreement_line, 'purchase_plan_id') and agreement_line.purchase_plan_id:
                po_line_vals['purchase_plan_id'] = agreement_line.purchase_plan_id.id

            if hasattr(agreement_line, 'purchase_plan_line_id') and agreement_line.purchase_plan_line_id:
                po_line_vals['purchase_plan_line_id'] = agreement_line.purchase_plan_line_id.id

            if hasattr(agreement_line, 'budget_analytic_id') and agreement_line.budget_analytic_id:
                po_line_vals['budget_analytic_id'] = agreement_line.budget_analytic_id.id

            if hasattr(agreement_line, 'budget_line_id') and agreement_line.budget_line_id:
                po_line_vals['budget_line_id'] = agreement_line.budget_line_id.id

            # Transfer request number
            if hasattr(agreement_line, 'x_studio_') and agreement_line.x_studio_:
                po_line_vals['x_studio_'] = agreement_line.x_studio_

            if hasattr(agreement_line, 'analytic_distribution') and agreement_line.analytic_distribution:
                po_line_vals['analytic_distribution'] = agreement_line.analytic_distribution

            new_rfq_vals['order_line'].append((0, 0, po_line_vals))

        # Create the new RFQ
        new_rfq = self.env['purchase.order'].create(new_rfq_vals)

        _logger.info(f"Created new quotation {new_rfq.name} from agreement {self.name}")

        return {
            'type': 'ir.actions.act_window',
            'name': _('New Quotation'),
            'res_model': 'purchase.order',
            'res_id': new_rfq.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.onchange('contract_registration_date')
    def _onchange_contract_registration_date(self):
        """Auto-fill registration_year when contract_registration_date is selected"""
        if self.contract_registration_date:
            self.registration_year = str(self.contract_registration_date.year)

    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        """Auto-fill supplier_id_code from vendor's VAT"""
        if self.vendor_id and self.vendor_id.vat:
            self.supplier_id_code = self.vendor_id.vat
            _logger.info(f"Set supplier_id_code to {self.vendor_id.vat} from vendor {self.vendor_id.name}")

    def _compute_contract_amount(self):
        """Calculate contract_amount as sum of all line total_amounts"""
        for requisition in self:
            total = sum(requisition.line_ids.mapped('total_amount'))
            requisition.write({'contract_amount': total})
            _logger.info(f"Updated contract_amount to {total} for requisition {requisition.name or requisition.id}")


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    # Link to inventory lines that created this requisition line
    inventory_line_ids = fields.Many2many(
        'inventory.line',
        'purchase_requisition_line_inventory_line_rel',
        'requisition_line_id',
        'inventory_line_id',
        string='Inventory Lines',
        help='Inventory lines used to create this agreement line'
    )

    @api.depends('product_qty', 'price_unit')
    def _compute_total_amount(self):
        """Calculate total amount as product_qty * price_unit"""
        for line in self:
            line.total_amount = line.product_qty * line.price_unit
            # Update parent contract_amount whenever line total_amount changes
            if line.requisition_id:
                line.requisition_id._compute_contract_amount()

    @api.onchange('product_qty', 'price_unit')
    def _onchange_product_qty_price_unit(self):
        """Update total_amount when quantity or price changes in UI"""
        for line in self:
            line.total_amount = line.product_qty * line.price_unit

    @api.model_create_multi
    def create(self, vals_list):
        """Update contract_amount when lines are created"""
        lines = super().create(vals_list)

        # Update contract_amount for each affected requisition
        requisitions = lines.mapped('requisition_id')
        for requisition in requisitions:
            requisition._compute_contract_amount()

        # Trigger recalculation of contracted values on inventory lines
        for line in lines:
            if line.inventory_line_ids:
                line.inventory_line_ids._update_contracted_values()

        return lines

    def write(self, vals):
        """Update contract_amount when lines are modified"""
        result = super().write(vals)

        # Update contract_amount if relevant fields changed
        if any(field in vals for field in ['product_qty', 'price_unit', 'total_amount']):
            requisitions = self.mapped('requisition_id')
            for requisition in requisitions:
                requisition._compute_contract_amount()

        # Trigger recalculation of contracted values on inventory lines
        if any(field in vals for field in ['product_qty', 'price_unit', 'inventory_line_ids']):
            for line in self:
                if line.inventory_line_ids:
                    line.inventory_line_ids._update_contracted_values()

        return result

    def unlink(self):
        """Update contract_amount when lines are deleted"""
        requisitions = self.mapped('requisition_id')
        # Store inventory lines before deletion
        inventory_lines = self.mapped('inventory_line_ids')

        result = super().unlink()

        for requisition in requisitions:
            if requisition.exists():
                requisition._compute_contract_amount()

        # Trigger recalculation of contracted values on inventory lines
        if inventory_lines:
            inventory_lines._update_contracted_values()

        return result


class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    @api.onchange('x_studio_request_number')
    def _onchange_request_number(self):
        """Update request number on all lines when changed"""
        if self.x_studio_request_number:
            for line in self.line_ids:
                line.x_studio_requset_number = self.x_studio_request_number