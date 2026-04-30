from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import date
_logger = logging.getLogger(__name__)


class BudgetingLine(models.Model):
    _inherit = 'inventory.line'

    # Use only the product `name` (no default code, etc.) in inventory lines

    purchase_agreements = fields.Many2many('purchase.requisition', string="Purchase Agreements")
    budget_line = fields.Many2one('budget.line', string='Budget Line')
    rfq_count = fields.Integer(string='RFQ Count',default=0, compute='_compute_rfq_count')

    purchase_agreements_count = fields.Integer(
        string='Transfer Count',
        compute='_compute_purchase_agreements_count'
    )
    purchase_agreement_directly = fields.Many2many(
        'purchase.requisition',
        'inventory_line_pr_direct_rel',
        'inventory_line_id',
        'purchase_requisition_id',
        string='Purchase Agreements Direct'
    )

    purchase_agreement_directly_count = fields.Integer(
        string='Purchase Agreement Count',
        compute='_compute_purchase_agreement_directly_count'
    )

    @api.depends('purchase_agreement_directly')
    def _compute_purchase_agreement_directly_count(self):
        for record in self:
            record.purchase_agreement_directly_count = len(record.purchase_agreement_directly)

    budget_analytic= fields.Many2one('budget.analytic', string='Budget Analytic')
    budget_analytic_line = fields.Many2one('budget.line', string='Budget Analytic Line')


    @api.depends('purchase_agreements')
    def _compute_purchase_agreements_count(self):
        for record in self:
            record.purchase_agreements_count = len(record.purchase_agreements)

    @api.depends('x_studio_rfq')
    def _compute_rfq_count(self):
        for record in self:
            record.rfq_count = 1 if record.x_studio_rfq else 0


    def create_purchase_agreement(self):
        PurchaseAgreement = self.env["purchase.requisition"]
        Vendor = self.env["res.partner"]
        RequisitionLine = self.env["purchase.requisition.line"]

        default_vendor = Vendor.search([('supplier_rank', '>', 0)], limit=1)

        agreement = PurchaseAgreement.create({
            'vendor_id': default_vendor.id if default_vendor else False,
        })


        for line in self:
            agreement.write({
                "line_ids": [(0, 0, {
                    "product_id": line.product_id.id,
                    "x_studio_": line.x_studio_requset_number,
                    "product_description_variants": line.name,
                    "product_qty": line.quantity,
                    "product_uom_id": line.uom_id.id,
                    "price_unit": line.unit_price,
                    "total_amount": line.amount,
                })]
            })

        for line in self:
            existing_line = RequisitionLine.search([
                ("requisition_id", "=", agreement.id),
                ("product_id", "=", line.product_id.id),
                ("product_qty", "=", line.quantity),
                ("product_uom_id", "=", line.uom_id.id),
                ("price_unit", "=", line.unit_price),
                ("total_amount", "=", line.amount),
                ("product_description_variants", "=", line.name),
                ("x_studio_", "=", line.x_studio_requset_number),
            ], limit=1)

            if not existing_line:
                new_line = RequisitionLine.create({
                    "requisition_id": agreement.id,
                    "product_id": line.product_id.id,
                })
                new_line.write({
                    "x_studio_": line.x_studio_requset_number,
                    "product_description_variants": line.name,
                    "product_uom_id": line.uom_id.id if line.uom_id else False,
                    "price_unit": line.unit_price,
                    "total_amount": line.amount,
                })
            self.write({
                "purchase_agreements": [(4, agreement.id)]
            })

        message = "Created Purchase agreement {} on lines: {}.".format(
            agreement.name, self.ids
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Purchase Agreement Created Successfully",
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_purchase_agreements(self):
        self.ensure_one()

        action = self.env.ref('purchase_requisition.action_purchase_requisition').read()[0]

        if len(self.purchase_agreements) == 1:
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.requisition',
                'res_id': self.purchase_agreements.id,
                'view_mode': 'form',
                'target': 'current',
                'context': dict(self._context, default_origin=self.name),
            }
        elif self.purchase_agreements:
            action['domain'] = [('id', 'in', self.purchase_agreements.ids)]
            action['context'] = dict(self._context, default_origin=self.name)
        else:
            action = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Purchase Agreements',
                    'message': 'No purchase agreements found for this line.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return action

    def action_view_purchase_agreements_directly(self):
        self.ensure_one()

        action = self.env.ref('purchase_requisition.action_purchase_requisition').read()[0]

        if len(self.purchase_agreement_directly) == 1:
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.requisition',
                'res_id': self.purchase_agreement_directly.id,
                'view_mode': 'form',
                'target': 'current',
                'context': dict(self._context, default_origin=self.name),
            }
        elif self.purchase_agreement_directly:
            action['domain'] = [('id', 'in', self.purchase_agreement_directly.ids)]
            action['context'] = dict(self._context, default_origin=self.name)
        else:
            action = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Direct Purchase Agreements',
                    'message': 'No direct purchase agreements found for this line.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return action

    def action_view_rfqs(self):
        self.ensure_one()

        rfqs = self.mapped('x_studio_rfq').filtered(lambda r: r)

        if not rfqs:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No RFQs Found',
                    'message': 'No RFQs have been created for this line yet.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        action = self.env.ref('purchase.purchase_rfq').read()[0]

        if len(rfqs) == 1:
            action.update({
                'res_id': rfqs.id,
                'view_mode': 'form',
                'domain': [('id', '=', rfqs.id)],
            })
        else:
            action.update({
                'domain': [('id', 'in', rfqs.ids)],
                'view_mode': 'list,form',
            })

        return action

#  Override someones Method

    def _create_purchase_agreement_direct(self, lines, vendor, purchase_method=None):
        """
        Create purchase agreement directly from inventory lines.
        This mirrors the logic from _create_single_agreement_with_all_lines but works directly with inventory lines.
        """
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
                if budget_to_use:
                    if hasattr(self.env['purchase.requisition'], 'budget_analytic_id'):
                        agreement_vals['budget_analytic_id'] = budget_to_use.id
                        _logger.info(f"Setting budget_analytic_id to {budget_to_use.id} ({budget_to_use.name})")

                if first_line.budget_analytic_line:
                    if hasattr(self.env['purchase.requisition'], 'budget_line_id'):
                        agreement_vals['budget_line_id'] = first_line.budget_analytic_line.id

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

            # Create the purchase agreement
            agreement = self.env['purchase.requisition'].create(agreement_vals)


            #Assign the created agreement to all inventory lines
            lines.write({'purchase_agreement_directly': [(4, agreement.id)]})

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

    # def action_show_onhand(self):
    #     self.ensure_one()
    #     return {
    #         'name': 'On Hand Quantities',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'product.onhand.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {'active_id': self.id},
    #     }

    # def action_view_stock_on_hand(self):
    #     self.ensure_one()
    #     return {
    #         'name': 'On Hand Quantities',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'stock.quant',
    #         'view_mode': 'list,form',
    #         'domain': [
    #             ('product_id', '=', self.product_id.id),
    #             ('location_id.usage', '=', 'internal'),
    #             ('on_hand', '=', True),
    #         ],
    #         'context': {
    #             'create': False,
    #             'edit': False,
    #         },
    #         'target': 'new',
    #     }

    def action_view_stock_on_hand(self):
        """Show, for this product, quantities per warehouse (on hand, reserved, free)."""
        self.ensure_one()
        return {
            'name': _('On Hand by Warehouse'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [
                ('product_id', '=', self.product_id.id),
                ('location_id.usage', '=', 'internal'),
                ('on_hand', '=', True),
                ('location_id.x_studio_request_location', '=', True),
            ],
            'context': {
                'create': False,
                'edit': False,
                # group by warehouse to get per‑warehouse totals
                # 'group_by': ['warehouse_id'],
            },
            'target': 'new',
        }